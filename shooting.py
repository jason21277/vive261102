"""
SKY RAIDER - 종스크롤 슈팅 게임 (pygame)

조작법
  방향키 / WASD : 이동
  Z / J         : 공중 사격 (공중 적 공격)
  X / K         : 지상 폭탄 (조준점 위치의 지상 적 공격)
  P             : 일시정지
  ENTER / SPACE : 시작 / 재시작
  ESC           : 종료

외부 이미지/사운드 파일 없이 그래픽과 효과음을 모두 코드로 만듭니다.
P 아이템을 먹으면 총알이 2 -> 4 -> 8 -> 16발로 강화됩니다. (죽으면 한 단계 하락)
"""
import math
import random
import sys
from array import array

import pygame

# ---------------------------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 480, 720
FPS = 60
TILE = 24
COLS = WIDTH // TILE
SCROLL_SPEED = 1.0
BOMB_RANGE = 150          # 기체에서 조준점까지 거리
BOMB_RADIUS = 180         # 폭탄 폭발 반경 (기존 18의 10배)
BOMB_CRATER_SCALE = 10    # 폭탄 흔적(구덩이) 크기 배율 (지상 적 잔해는 1배)
BOSS_TIME = FPS * 70      # 스테이지 시작 후 보스 등장까지 시간
EXTRA_LIFE_EVERY = 20000

# 무기 단계별 (총알 수, 부채꼴 반각(rad), 좌우 폭(px))
SHOT_LEVELS = [(2, 0.0, 6), (4, 0.10, 12), (8, 0.30, 16), (16, 0.75, 20)]
SHOT_COLORS = [(255, 245, 150), (150, 255, 200), (140, 200, 255), (255, 150, 255)]
ITEM_DROP_CHANCE = {"dart": 0.06, "weaver": 0.06, "spinner": 0.5, "hunter": 0.15}

TERRAIN_COLORS = {
    "water": (40, 90, 170),
    "bridge": (125, 100, 75),
    "road": (90, 90, 95),
    "sand": (200, 185, 130),
    "grass": (70, 140, 60),
    "forest": (40, 105, 45),
}

# 종류: (체력, 점수, 충돌 반경)
AIR_SPECS = {
    "dart": (1, 100, 11),
    "weaver": (1, 150, 12),
    "spinner": (4, 400, 15),
    "hunter": (2, 250, 12),
}
GROUND_SPECS = {
    "turret": (1, 300, 13),
    "tank": (1, 500, 13),
    "radar": (1, 1000, 14),
    "bunker": (3, 800, 18),
}

EXPLOSION_COLORS = [(255, 240, 180), (255, 190, 70), (255, 120, 40), (210, 60, 20)]


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def hash2(a, b):
    """정수 좌표 -> 0~1 사이의 고정된 난수"""
    n = (a * 374761393 + b * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n ^ (n >> 16)) / 0xFFFFFFFF


def shade(color, h, amount=18):
    k = int((h - 0.5) * amount)
    return tuple(clamp(v + k, 0, 255) for v in color)


def dist2(ax, ay, bx, by):
    return (ax - bx) ** 2 + (ay - by) ** 2


def make_crater(scale):
    """반투명 구덩이 이미지. 기본 반경 13px에 scale배"""
    r = 13 * scale
    surf = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
    c = (r + 1, r + 1)
    pygame.draw.circle(surf, (45, 35, 25, 110), c, r)
    pygame.draw.circle(surf, (55, 45, 35, 170), c, int(r * 0.8))
    pygame.draw.circle(surf, (35, 28, 22, 220), c, int(r * 0.6))
    pygame.draw.circle(surf, (90, 75, 55, 160), c, int(r * 0.8), max(1, scale))
    for _ in range(6 * scale):
        a = random.uniform(0, math.tau)
        d = random.uniform(0.3, 0.95) * r
        pygame.draw.circle(surf, (25, 20, 15, 200),
                           (int(c[0] + math.cos(a) * d), int(c[1] + math.sin(a) * d)),
                           random.randint(1, 2 + scale // 2))
    return surf


# ---------------------------------------------------------------------------
# 효과음 (코드로 합성, numpy 불필요)
# ---------------------------------------------------------------------------
class SoundBank:
    """오디오 장치가 없으면 소리 없이 조용히 동작한다."""

    def __init__(self):
        self.sounds = {}
        self.channels = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            self.rate, _, self.nch = pygame.mixer.get_init()
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(2)
            # 연사음/피격음은 전용 채널에서 이전 소리를 덮어쓰며 재생
            self.channels = {"shot": pygame.mixer.Channel(0), "hit": pygame.mixer.Channel(1)}
            self._build()
        except pygame.error:
            self.sounds = {}

    def tone(self, dur, f0, f1, wave="square", vol=0.3, curve=1.0, noise=0.0):
        n = int(self.rate * dur)
        attack = max(1, int(self.rate * 0.004))
        out = []
        phase = 0.0
        hold = 0.0
        for i in range(n):
            k = i / n
            phase += (f0 + (f1 - f0) * k) / self.rate
            if phase >= 1.0:
                phase -= int(phase)
                hold = random.uniform(-1, 1)
            if wave == "square":
                s = 1.0 if phase < 0.5 else -1.0
            elif wave == "saw":
                s = 2 * phase - 1
            elif wave == "tri":
                s = 4 * abs(phase - 0.5) - 1
            elif wave == "noise":
                s = hold
            else:
                s = math.sin(math.tau * phase)
            if noise:
                s = s * (1 - noise) + random.uniform(-1, 1) * noise
            out.append(s * min(1.0, i / attack) * (1 - k) ** curve * vol)
        return out

    def make(self, segments):
        buf = array("h")
        for seg in segments:
            for s in seg:
                buf.extend((int(clamp(s, -1, 1) * 32767),) * self.nch)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def notes(self, freqs, dur, vol=0.2, wave="square"):
        return [self.tone(dur, f, f, wave, vol, curve=0.4) for f in freqs]

    def _build(self):
        t, m = self.tone, self.make
        self.sounds = {
            "shot": m([t(0.06, 1500, 700, "square", 0.10)]),
            "bomb": m([t(0.28, 1000, 250, "tri", 0.25)]),
            "hit": m([t(0.04, 400, 250, "square", 0.08)]),
            "boom": m([t(0.35, 3000, 200, "noise", 0.35)]),
            "ground_boom": m([t(0.5, 1600, 80, "noise", 0.40)]),
            "big_boom": m([t(1.3, 1200, 60, "noise", 0.55, curve=1.6)]),
            "death": m([t(1.0, 700, 50, "saw", 0.35, noise=0.5)]),
            "powerup": m(self.notes((523, 659, 784, 1047, 1319), 0.07)),
            "extra": m(self.notes((784, 988, 1175, 1568, 1175, 1568), 0.08)),
            "warning": m(self.notes((880, 587) * 3, 0.18, 0.22)),
            "clear": m(self.notes((523, 659, 784, 1047), 0.12) + [t(0.4, 1047, 1047, "square", 0.2)]),
            "start": m(self.notes((392, 523, 659, 784), 0.08)),
        }

    def play(self, name):
        snd = self.sounds.get(name)
        if snd is None:
            return
        ch = self.channels.get(name)
        if ch:
            ch.play(snd)
        else:
            snd.play()


# ---------------------------------------------------------------------------
# 스크롤되는 지형
# ---------------------------------------------------------------------------
class Terrain:
    def __init__(self):
        self.scroll = 0.0
        self.seed = random.random() * 100
        self.cache = {}
        self.t = 0

    def tile(self, c, r):
        key = (c, r)
        t = self.cache.get(key)
        if t is None:
            t = self._gen(c, r)
            self.cache[key] = t
        return t

    def _gen(self, c, r):
        s = self.seed
        river_x = COLS / 2 + 6 * math.sin(r * 0.035 + s) + 2.5 * math.sin(r * 0.11 + s * 2)
        river_w = 1.6 + 0.9 * math.sin(r * 0.021 + s)
        d = abs(c + 0.5 - river_x)
        h = hash2(c, r)
        road = (r % 90) in (0, 1)
        if d < river_w:
            kind = "bridge" if road else "water"
        elif road:
            kind = "road"
        elif d < river_w + 1.0:
            kind = "sand"
        else:
            v = (math.sin(c * 0.45 + r * 0.08 + s)
                 + math.sin(c * 0.21 - r * 0.05 + s * 3)
                 + (h - 0.5) * 0.6)
            kind = "forest" if v > 0.8 else "grass"
        return kind, h

    def row_at(self, y):
        return int((HEIGHT - y + self.scroll) // TILE)

    def is_water(self, x, y):
        c = int(clamp(x, 0, WIDTH - 1) // TILE)
        return self.tile(c, self.row_at(y))[0] == "water"

    def update(self, speed):
        self.scroll += speed
        self.t += 1
        if self.t % 120 == 0:
            first = int(self.scroll // TILE) - 2
            self.cache = {k: v for k, v in self.cache.items() if k[1] >= first}

    def draw(self, surf):
        first = int(self.scroll // TILE)
        for r in range(first, first + HEIGHT // TILE + 2):
            y = int(HEIGHT - (r + 1) * TILE + self.scroll)
            for c in range(COLS):
                kind, h = self.tile(c, r)
                x = c * TILE
                surf.fill(shade(TERRAIN_COLORS[kind], h), (x, y, TILE, TILE))
                if kind == "forest":
                    pygame.draw.circle(surf, shade((25, 75, 30), h), (x + 12, y + 12), 10)
                    pygame.draw.circle(surf, (60, 130, 55), (x + 9, y + 9), 3)
                elif kind == "water" and h > 0.7:
                    off = int((self.t * 0.4 + h * 40) % 10)
                    pygame.draw.line(surf, (95, 150, 220), (x + 3 + off, y + 6 + int(h * 10)),
                                     (x + 10 + off, y + 6 + int(h * 10)), 2)
                elif kind == "road" and r % 90 == 0 and c % 2 == 0:
                    surf.fill((230, 215, 130), (x + 4, y - 1, 14, 2))
                elif kind == "bridge":
                    for i in range(0, TILE, 6):
                        pygame.draw.line(surf, (95, 75, 55), (x + i, y), (x + i, y + TILE))
                elif kind == "grass" and h > 0.9:
                    pygame.draw.circle(surf, (95, 165, 75), (x + 8 + int(h * 8), y + 10), 3)


# ---------------------------------------------------------------------------
# 이펙트
# ---------------------------------------------------------------------------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "ground")

    def __init__(self, x, y, vx, vy, life, color, size, ground=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size, self.ground = color, size, ground

    def update(self, scroll):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.93
        self.vy *= 0.93
        if self.ground:
            self.y += scroll
        self.life -= 1

    def draw(self, surf):
        r = max(1, int(self.size * self.life / self.max_life))
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), r)


class Popup:
    def __init__(self, x, y, text, color=(255, 255, 255)):
        self.x, self.y, self.text, self.color = x, y, text, color
        self.life = 50


# ---------------------------------------------------------------------------
# 플레이어
# ---------------------------------------------------------------------------
def ship_points(x, y):
    return [(x, y - 16), (x + 5, y - 6), (x + 16, y + 6), (x + 16, y + 10), (x + 5, y + 8),
            (x + 3, y + 13), (x - 3, y + 13), (x - 5, y + 8), (x - 16, y + 10),
            (x - 16, y + 6), (x - 5, y - 6)]


class Player:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 100
        self.speed = 4.2
        self.fire_cd = 0
        self.lives = 3
        self.power = 0            # SHOT_LEVELS 인덱스 (0: 2발 ~ 3: 16발)
        self.invuln = 120
        self.alive = True
        self.respawn = 0

    def draw(self, surf, t):
        if self.invuln > 0 and (t // 4) % 2 == 0:
            return
        x, y = int(self.x), int(self.y)
        flame = 18 + random.randint(0, 6)
        pygame.draw.polygon(surf, (255, 150, 40), [(x - 3, y + 12), (x + 3, y + 12), (x, y + flame)])
        pygame.draw.polygon(surf, (255, 240, 160), [(x - 1, y + 12), (x + 1, y + 12), (x, y + flame - 5)])
        pygame.draw.polygon(surf, (205, 212, 225), ship_points(x, y))
        pygame.draw.polygon(surf, (90, 100, 125), ship_points(x, y), 1)
        pygame.draw.line(surf, (230, 70, 60), (x - 14, y + 7), (x - 7, y + 4), 2)
        pygame.draw.line(surf, (230, 70, 60), (x + 14, y + 7), (x + 7, y + 4), 2)
        pygame.draw.ellipse(surf, (60, 170, 255), (x - 3, y - 9, 6, 10))


class Shot:
    def __init__(self, x, y, angle=0.0, color=(255, 245, 150)):
        self.x, self.y = x, y
        self.vx = math.sin(angle) * 11
        self.vy = -math.cos(angle) * 11
        self.color = color
        self.dead = False

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -20 or self.x < -20 or self.x > WIDTH + 20:
            self.dead = True

    def draw(self, surf):
        hx, hy = self.vx * 0.55, self.vy * 0.55
        pygame.draw.line(surf, self.color, (self.x - hx, self.y - hy), (self.x + hx, self.y + hy), 3)


class Item:
    """P 아이템: 먹으면 무기 단계 상승"""

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.base_x = clamp(x, 30, WIDTH - 30)
        self.t = 0
        self.dead = False

    def update(self):
        self.t += 1
        self.y += 1.3
        self.x = self.base_x + math.sin(self.t * 0.06) * 20
        if self.y > HEIGHT + 20:
            self.dead = True

    def draw(self, surf, font):
        x, y = int(self.x), int(self.y)
        glow = 15 + int(math.sin(self.t * 0.2) * 2)
        pygame.draw.circle(surf, (255, 255, 255), (x, y), glow, 2)
        col = (60, 120, 255) if (self.t // 8) % 2 else (255, 80, 80)
        pygame.draw.circle(surf, col, (x, y), 11)
        img = font.render("P", True, (255, 255, 255))
        surf.blit(img, img.get_rect(center=(x, y + 1)))


class Bomb:
    """기체에서 조준점(지상)으로 떨어지는 폭탄. 조준점은 지면과 함께 스크롤된다."""

    def __init__(self, sx, sy, tx, ty):
        self.sx, self.sy, self.tx, self.ty = sx, sy, tx, ty
        self.t = 0
        self.dur = 26
        self.done = False

    @property
    def pos(self):
        k = self.t / self.dur
        return self.sx + (self.tx - self.sx) * k, self.sy + (self.ty - self.sy) * k

    def update(self, scroll):
        self.t += 1
        self.ty += scroll
        if self.t >= self.dur:
            self.done = True

    def draw(self, surf):
        x, y = self.pos
        size = 6 - 3 * self.t / self.dur
        pygame.draw.circle(surf, (50, 50, 60), (int(x), int(y)), int(size) + 1)
        pygame.draw.circle(surf, (170, 170, 185), (int(x) - 1, int(y) - 1), max(1, int(size) - 2))


class EnemyBullet:
    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.dead = False

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.dead = True

    def draw(self, surf, t):
        c = (255, 90, 160) if (t // 4) % 2 else (255, 150, 60)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), 5)
        pygame.draw.circle(surf, (255, 255, 255), (int(self.x), int(self.y)), 2)


# ---------------------------------------------------------------------------
# 공중 적
# ---------------------------------------------------------------------------
class AirEnemy:
    def __init__(self, kind, x, y, phase=0.0):
        self.kind = kind
        self.hp, self.score, self.r = AIR_SPECS[kind]
        self.x, self.y = x, y
        self.base_x = x
        self.phase = phase
        self.vx = self.vy = 0.0
        self.t = 0
        self.flash = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        if self.flash:
            self.flash -= 1
        p = game.player
        d = game.difficulty

        if self.kind == "dart":
            if self.t == 1:
                ang = math.atan2(p.y - self.y, p.x - self.x)
                spd = 3.6 + d * 0.3
                self.vx = math.cos(ang) * spd * 0.5
                self.vy = max(2.8, math.sin(ang) * spd)
            self.x += self.vx
            self.y += self.vy
        elif self.kind == "weaver":
            self.y += 2.2 + d * 0.15
            self.x = self.base_x + math.sin(self.t * 0.05 + self.phase) * 70
        elif self.kind == "spinner":
            if self.t < 60:
                self.y += 2.5
            elif self.t < 260:
                self.x += math.sin(self.t * 0.03) * 1.3
                interval = max(25, 55 - int(d * 5))
                if self.t % interval == 0:
                    game.fire_aimed(self.x, self.y, 3.0, 0.22, 5 if d >= 2 else 3)
            else:
                self.y -= 2.5
                if self.y < -40:
                    self.dead = True
        elif self.kind == "hunter":
            if self.t < 110:
                self.y += 2.0
                self.x += clamp(p.x - self.x, -2.5, 2.5)
                if self.t == 50:
                    game.fire_aimed(self.x, self.y, 3.5 + d * 0.2)
            else:
                self.y += 5

        if self.kind in ("dart", "weaver") and 0 < self.y < HEIGHT * 0.55:
            if random.random() < 0.005 + d * 0.002:
                game.fire_aimed(self.x, self.y, 3.2 + d * 0.2)

        if self.y > HEIGHT + 40 or self.x < -80 or self.x > WIDTH + 80:
            self.dead = True

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        white = self.flash > 0
        if self.kind == "dart":
            col = (255, 255, 255) if white else (220, 60, 60)
            pts = [(x, y + 13), (x + 11, y - 9), (x, y - 4), (x - 11, y - 9)]
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, (120, 20, 20), pts, 1)
            pygame.draw.circle(surf, (255, 220, 120), (x, y), 3)
        elif self.kind == "weaver":
            col = (255, 255, 255) if white else (160, 90, 220)
            pygame.draw.polygon(surf, col, [(x - 14, y - 4), (x, y - 10), (x + 14, y - 4), (x, y + 12)])
            pygame.draw.circle(surf, (240, 200, 255), (x, y), 4)
        elif self.kind == "spinner":
            col = (255, 255, 255) if white else (240, 150, 40)
            a = self.t * 0.15
            for i in range(3):
                ang = a + i * 2 * math.pi / 3
                ex, ey = x + math.cos(ang) * 16, y + math.sin(ang) * 16
                pygame.draw.line(surf, (200, 200, 210), (x, y), (ex, ey), 4)
                pygame.draw.circle(surf, (150, 150, 165), (int(ex), int(ey)), 4)
            pygame.draw.circle(surf, col, (x, y), 9)
            pygame.draw.circle(surf, (120, 40, 10), (x, y), 9, 2)
        elif self.kind == "hunter":
            col = (255, 255, 255) if white else (70, 200, 120)
            pts = [(x, y + 14), (x + 12, y - 2), (x + 6, y - 10), (x, y - 4), (x - 6, y - 10), (x - 12, y - 2)]
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, (20, 90, 50), pts, 1)


# ---------------------------------------------------------------------------
# 지상 적
# ---------------------------------------------------------------------------
class GroundEnemy:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.hp, self.score, self.r = GROUND_SPECS[kind]
        self.x, self.y = x, y
        self.vx = random.choice((-0.6, 0.6)) if kind == "tank" else 0.0
        self.fire_timer = random.randint(60, 150)
        self.angle = math.pi / 2
        self.t = 0
        self.flash = 0
        self.dead = False

    def update(self, game):
        self.t += 1
        self.y += game.scroll_speed
        if self.flash:
            self.flash -= 1
        p = game.player
        self.angle = math.atan2(p.y - self.y, p.x - self.x)

        if self.kind == "tank":
            nx = self.x + self.vx
            if nx < 20 or nx > WIDTH - 20 or game.terrain.is_water(nx + self.vx * 20, self.y):
                self.vx = -self.vx
            else:
                self.x = nx

        if self.kind != "radar" and 30 < self.y < HEIGHT - 160 and p.alive:
            self.fire_timer -= 1
            if self.fire_timer <= 0:
                d = game.difficulty
                self.fire_timer = max(45, int(130 - d * 12)) + random.randint(0, 40)
                if self.kind == "bunker":
                    game.fire_aimed(self.x, self.y, 2.6, 0.25, 3)
                else:
                    game.fire_aimed(self.x, self.y, 2.8 + d * 0.15)

        if self.y > HEIGHT + 40:
            self.dead = True

    def draw(self, surf):
        x, y = int(self.x), int(self.y)
        white = self.flash > 0
        bx = x + int(math.cos(self.angle) * 13)
        by = y + int(math.sin(self.angle) * 13)
        if self.kind == "turret":
            surf.fill((70, 70, 80), (x - 12, y - 12, 24, 24))
            surf.fill((255, 255, 255) if white else (120, 120, 132), (x - 10, y - 10, 20, 20))
            pygame.draw.line(surf, (40, 40, 45), (x, y), (bx, by), 4)
            pygame.draw.circle(surf, (160, 160, 175), (x, y), 7)
        elif self.kind == "tank":
            surf.fill((50, 45, 35), (x - 13, y - 10, 26, 5))
            surf.fill((50, 45, 35), (x - 13, y + 5, 26, 5))
            surf.fill((255, 255, 255) if white else (140, 120, 70), (x - 11, y - 7, 22, 14))
            pygame.draw.line(surf, (60, 55, 40), (x, y), (bx, by), 4)
            pygame.draw.circle(surf, (170, 150, 95), (x, y), 6)
        elif self.kind == "radar":
            pygame.draw.circle(surf, (90, 90, 100), (x, y), 13)
            pygame.draw.circle(surf, (255, 255, 255) if white else (185, 185, 195), (x, y), 10)
            a = self.t * 0.08
            ex, ey = x + math.cos(a) * 12, y + math.sin(a) * 5
            pygame.draw.line(surf, (60, 60, 70), (x - (ex - x), y - (ey - y)), (ex, ey), 4)
            if (self.t // 20) % 2:
                pygame.draw.circle(surf, (255, 60, 60), (x, y), 3)
        elif self.kind == "bunker":
            pts = [(x + math.cos(i * math.pi / 4 + math.pi / 8) * 18,
                    y + math.sin(i * math.pi / 4 + math.pi / 8) * 18) for i in range(8)]
            pygame.draw.polygon(surf, (60, 65, 50), pts)
            inner = [((px - x) * 0.75 + x, (py - y) * 0.75 + y) for px, py in pts]
            base = (100, 105, 85) if self.hp >= 3 else (130, 100, 70) if self.hp == 2 else (150, 80, 60)
            pygame.draw.polygon(surf, (255, 255, 255) if white else base, inner)
            pygame.draw.circle(surf, (30, 30, 30), (x, y), 5 if self.fire_timer < 20 else 3)


# ---------------------------------------------------------------------------
# 보스
# ---------------------------------------------------------------------------
HULL = [(-110, 0), (-70, -35), (70, -35), (110, 0), (70, 40), (30, 60), (-30, 60), (-70, 40)]


class Boss:
    def __init__(self, stage):
        self.stage = stage
        self.x = WIDTH / 2
        self.y = -140.0
        self.t = 0
        self.state = "enter"
        pod_hp = 14 + stage * 4
        self.pods = [{"dx": dx, "dy": dy, "hp": pod_hp, "flash": 0, "timer": 40 + i * 18}
                     for i, (dx, dy) in enumerate(((-88, 6), (88, 6), (-46, 46), (46, 46)))]
        self.pod_max = pod_hp
        self.core_max = 70 + stage * 25
        self.core_hp = self.core_max
        self.core_flash = 0
        self.score = 5000 + 5000 * stage
        self.dead = False

    @property
    def shielded(self):
        return any(p["hp"] > 0 for p in self.pods)

    def update(self, game):
        self.t += 1
        if self.core_flash:
            self.core_flash -= 1
        for pod in self.pods:
            if pod["flash"]:
                pod["flash"] -= 1

        if self.state == "enter":
            self.y += 1.5
            if self.y >= 150:
                self.state = "fight"
                self.t = 0
        elif self.state == "fight":
            self.x = WIDTH / 2 + math.sin(self.t * 0.012) * 110
            self.y = 150 + math.sin(self.t * 0.023) * 18
            for pod in self.pods:
                if pod["hp"] <= 0:
                    continue
                pod["timer"] -= 1
                if pod["timer"] <= 0:
                    pod["timer"] = max(50, 95 - self.stage * 8)
                    game.fire_aimed(self.x + pod["dx"], self.y + pod["dy"], 3.0 + 0.2 * self.stage,
                                    0.18, 3 if self.stage > 1 else 1)
            if self.shielded:
                if self.t % 160 == 0:
                    game.fire_ring(self.x, self.y + 10, 2.2, 14, self.t * 0.05)
            else:
                rate = max(8, 14 - self.stage)
                if self.t % rate == 0:
                    game.fire_ring(self.x, self.y, 2.6, 3, self.t * 0.13)
                if self.t % 90 == 0:
                    game.fire_aimed(self.x, self.y, 4.0, 0.12, 5)
        elif self.state == "dying":
            if self.t % 6 == 0:
                game.explode(self.x + random.uniform(-100, 100), self.y + random.uniform(-30, 55), 1.2)
            if self.t > 150:
                game.explode(self.x, self.y, 3.5)
                self.dead = True

    def hit(self, game, bx, by):
        """플레이어 탄이 보스에 맞았으면 True"""
        if self.state != "fight":
            return False
        for pod in self.pods:
            if pod["hp"] <= 0:
                continue
            px, py = self.x + pod["dx"], self.y + pod["dy"]
            if dist2(px, py, bx, by) < 18 ** 2:
                pod["hp"] -= 1
                pod["flash"] = 4
                if pod["hp"] <= 0:
                    game.explode(px, py, 1.5)
                    game.add_score(1500, px, py)
                    game.items.append(Item(px, py))
                return True
        if dist2(self.x, self.y + 10, bx, by) < 30 ** 2:
            if self.shielded:
                game.spark(bx, by, (120, 220, 255))
            else:
                self.core_hp -= 1
                self.core_flash = 4
                game.sfx.play("hit")
                if self.core_hp <= 0:
                    self.state = "dying"
                    self.t = 0
                    game.ebullets.clear()
                    game.add_score(self.score, self.x, self.y)
            return True
        if abs(bx - self.x) < 100 and -35 < by - self.y < 50:
            game.spark(bx, by, (255, 230, 150))
            return True
        return False

    def collides(self, px, py):
        return self.state == "fight" and dist2(self.x, self.y + 10, px, py) < 50 ** 2

    def draw(self, surf, t):
        x, y = int(self.x), int(self.y)
        shake = random.randint(-3, 3) if self.state == "dying" else 0
        x += shake
        hull = [(x + px, y + py) for px, py in HULL]
        pygame.draw.polygon(surf, (55, 60, 75), hull)
        inner = [(x + px * 0.75, y + py * 0.75) for px, py in HULL]
        pygame.draw.polygon(surf, (95, 100, 120), inner)
        pygame.draw.polygon(surf, (30, 32, 40), hull, 2)
        for i in (-1, 1):
            pygame.draw.line(surf, (140, 145, 165), (x + i * 30, y - 30), (x + i * 80, y + 2), 2)
            surf.fill((255, 120, 40) if (t // 5) % 2 else (255, 200, 80), (x + i * 50 - 6, y + 48, 12, 6))

        for pod in self.pods:
            px, py = x + pod["dx"], y + pod["dy"]
            if pod["hp"] > 0:
                col = (255, 255, 255) if pod["flash"] else (150, 160, 185)
                pygame.draw.circle(surf, (40, 45, 55), (px, py), 16)
                pygame.draw.circle(surf, col, (px, py), 12)
                pygame.draw.line(surf, (40, 40, 50), (px, py), (px, py + 18), 5)
            else:
                pygame.draw.circle(surf, (35, 30, 30), (px, py), 13)
                pygame.draw.circle(surf, (90, 50, 30), (px, py), 6)

        pulse = int(abs(math.sin(t * 0.08)) * 80)
        core_col = (255, 255, 255) if self.core_flash else (175 + pulse, 40, 40)
        pygame.draw.circle(surf, (30, 20, 25), (x, y + 10), 24)
        pygame.draw.circle(surf, core_col, (x, y + 10), 18)
        pygame.draw.circle(surf, (255, 200, 120), (x, y + 10), 7)
        if self.shielded and self.state == "fight":
            pygame.draw.circle(surf, (110, 210, 255), (x, y + 10), 28 + (t // 3) % 3, 2)

    def draw_bar(self, surf):
        if self.state != "fight":
            return
        w = WIDTH - 80
        surf.fill((40, 0, 0), (40, 42, w, 8))
        if self.shielded:
            ratio = sum(max(0, p["hp"]) for p in self.pods) / (self.pod_max * 4)
            surf.fill((90, 200, 255), (40, 42, int(w * ratio), 8))
        else:
            surf.fill((255, 70, 50), (40, 42, int(w * self.core_hp / self.core_max), 8))
        pygame.draw.rect(surf, (230, 230, 230), (40, 42, w, 8), 1)


# ---------------------------------------------------------------------------
# 게임
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SKY RAIDER")
        self.clock = pygame.time.Clock()
        self.world = pygame.Surface((WIDTH, HEIGHT))
        self.font_s = pygame.font.SysFont("consolas", 16, bold=True)
        self.font_m = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_l = pygame.font.SysFont("consolas", 52, bold=True)

        self.crater_imgs = {1: make_crater(1), BOMB_CRATER_SCALE: make_crater(BOMB_CRATER_SCALE)}
        self.shadow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.shadow, (0, 0, 0, 80), ship_points(20, 20))

        self.sfx = SoundBank()
        self.hiscore = 0
        self.state = "title"
        self.paused = False
        self.scroll_speed = SCROLL_SPEED
        self.terrain = Terrain()
        self.reset()

    # ---- 초기화 -----------------------------------------------------------
    def reset(self):
        self.player = Player()
        self.shots, self.bombs, self.ebullets = [], [], []
        self.air, self.ground, self.items = [], [], []
        self.particles, self.rings, self.popups, self.craters = [], [], [], []
        self.boss = None
        self.score = 0
        self.stage = 1
        self.stage_timer = 0
        self.next_extra = EXTRA_LIFE_EVERY
        self.air_timer = 90
        self.ground_timer = 60
        self.shake = 0
        self.t = 0
        self.banner = ("STAGE 1", 120)

    @property
    def difficulty(self):
        return (self.stage - 1) + self.stage_timer / (FPS * 60)

    # ---- 유틸 -------------------------------------------------------------
    def fire_aimed(self, x, y, speed, spread=0.0, count=1):
        p = self.player
        ang = math.atan2(p.y - y, p.x - x)
        for i in range(count):
            a = ang + (i - (count - 1) / 2) * spread
            self.ebullets.append(EnemyBullet(x, y, math.cos(a) * speed, math.sin(a) * speed))

    def fire_ring(self, x, y, speed, count, offset=0.0):
        for i in range(count):
            a = offset + i * 2 * math.pi / count
            self.ebullets.append(EnemyBullet(x, y, math.cos(a) * speed, math.sin(a) * speed))

    def explode(self, x, y, size=1.0, ground=False):
        for _ in range(int(20 * size)):
            a = random.uniform(0, math.tau)
            s = random.uniform(0.5, 4.0) * size
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s,
                                           random.randint(20, 40), random.choice(EXPLOSION_COLORS),
                                           random.uniform(2, 4) * size, ground))
        self.rings.append([x, y, 4.0, 30 * size, ground])
        self.shake = max(self.shake, int(5 * size))
        if size >= 2.5:
            self.sfx.play("big_boom")
        elif ground:
            self.sfx.play("ground_boom")
        else:
            self.sfx.play("boom")

    def spark(self, x, y, color):
        self.sfx.play("hit")
        for _ in range(4):
            a = random.uniform(0, math.tau)
            self.particles.append(Particle(x, y, math.cos(a) * 3, math.sin(a) * 3, 10, color, 2))

    def add_score(self, n, x=None, y=None):
        self.score += n
        if x is not None:
            self.popups.append(Popup(x, y, str(n)))
        if self.score >= self.next_extra:
            self.next_extra += EXTRA_LIFE_EVERY
            self.player.lives += 1
            self.popups.append(Popup(self.player.x, self.player.y - 30, "1UP", (120, 255, 120)))
            self.sfx.play("extra")

    def collect_item(self, item):
        p = self.player
        item.dead = True
        if p.power < len(SHOT_LEVELS) - 1:
            p.power += 1
            n = SHOT_LEVELS[p.power][0]
            self.popups.append(Popup(p.x, p.y - 30, f"SHOT x{n}", SHOT_COLORS[p.power]))
        else:
            self.add_score(2000, p.x, p.y - 30)
        self.sfx.play("powerup")

    def fire_shots(self):
        p = self.player
        n, spread, width = SHOT_LEVELS[p.power]
        color = SHOT_COLORS[p.power]
        for i in range(n):
            k = i / (n - 1) * 2 - 1      # -1 ~ 1
            self.shots.append(Shot(p.x + k * width, p.y - 8, k * spread, color))
        self.sfx.play("shot")

    # ---- 적 생성 ----------------------------------------------------------
    def spawn_air_wave(self):
        d = self.difficulty
        roll = random.random()
        if roll < 0.3:
            n = min(6, 3 + int(d))
            x = random.uniform(80, WIDTH - 80)
            for i in range(n):
                self.air.append(AirEnemy("dart", x + (i - n / 2) * 28, -20 - i * 26))
        elif roll < 0.6:
            bx = random.uniform(100, WIDTH - 100)
            for i in range(5):
                self.air.append(AirEnemy("weaver", bx, -20 - i * 36, i * 0.6))
        elif roll < 0.8:
            for _ in range(2 if d >= 2 else 1):
                self.air.append(AirEnemy("spinner", random.uniform(60, WIDTH - 60), -30))
        else:
            self.air.append(AirEnemy("hunter", WIDTH / 3, -20))
            self.air.append(AirEnemy("hunter", WIDTH * 2 / 3, -50))

    def spawn_ground(self):
        for _ in range(10):
            x = random.uniform(30, WIDTH - 30)
            if not self.terrain.is_water(x, -30):
                break
        else:
            return
        weights = [40, 35, 10, 15 if self.difficulty >= 1 else 5]
        kind = random.choices(["turret", "tank", "radar", "bunker"], weights=weights)[0]
        self.ground.append(GroundEnemy(kind, x, -30))

    # ---- 갱신 -------------------------------------------------------------
    def kill_player(self):
        p = self.player
        self.explode(p.x, p.y, 2.0)
        p.alive = False
        p.respawn = 90
        p.lives -= 1
        p.power = max(0, p.power - 1)
        self.sfx.play("death")

    def update_player(self, keys):
        p = self.player
        if not p.alive:
            p.respawn -= 1
            if p.respawn <= 0:
                if p.lives < 0:
                    self.state = "gameover"
                    self.hiscore = max(self.hiscore, self.score)
                else:
                    p.alive = True
                    p.x, p.y = WIDTH / 2, HEIGHT - 100
                    p.invuln = 150
                    self.ebullets.clear()
            return

        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        p.x = clamp(p.x + dx * p.speed, 16, WIDTH - 16)
        p.y = clamp(p.y + dy * p.speed, 40, HEIGHT - 24)

        if p.fire_cd > 0:
            p.fire_cd -= 1
        if (keys[pygame.K_z] or keys[pygame.K_j]) and p.fire_cd <= 0:
            self.fire_shots()
            p.fire_cd = 6
        if (keys[pygame.K_x] or keys[pygame.K_k]) and not self.bombs:
            self.bombs.append(Bomb(p.x, p.y - 10, p.x, p.y - BOMB_RANGE))
            self.sfx.play("bomb")
        if p.invuln > 0:
            p.invuln -= 1

    def bomb_explode(self, x, y):
        self.explode(x, y, 2.0, ground=True)
        self.rings.append([x, y, 10.0, BOMB_RADIUS, True])
        for _ in range(40):
            a = random.uniform(0, math.tau)
            d = random.uniform(0, BOMB_RADIUS)
            self.particles.append(Particle(x + math.cos(a) * d, y + math.sin(a) * d, 0, -0.5,
                                           random.randint(15, 35), random.choice(EXPLOSION_COLORS),
                                           random.uniform(3, 6), True))
        self.craters.append([x, y, BOMB_CRATER_SCALE])
        for g in self.ground:
            if not g.dead and dist2(g.x, g.y, x, y) < (g.r + BOMB_RADIUS) ** 2:
                g.hp -= 1
                g.flash = 5
                if g.hp <= 0:
                    g.dead = True
                    self.explode(g.x, g.y, 1.3, ground=True)
                    self.craters.append([g.x, g.y, 1])
                    self.add_score(g.score, g.x, g.y)
                    if g.kind == "radar":
                        self.items.append(Item(g.x, g.y))

    def update_playing(self, keys):
        self.t += 1
        p = self.player
        self.update_player(keys)

        # 스테이지 진행 / 적 생성
        if self.boss is None:
            self.stage_timer += 1
            if self.stage_timer >= BOSS_TIME:
                self.boss = Boss(self.stage)
                self.banner = ("WARNING!", 150)
                self.sfx.play("warning")
            else:
                self.air_timer -= 1
                if self.air_timer <= 0:
                    self.spawn_air_wave()
                    lo = max(35, int(110 - self.difficulty * 10))
                    self.air_timer = random.randint(lo, lo + 60)
                self.ground_timer -= 1
                if self.ground_timer <= 0:
                    self.spawn_ground()
                    self.ground_timer = max(40, int(120 - self.difficulty * 10)) + random.randint(0, 60)
        else:
            self.boss.update(self)
            if self.boss.dead:
                self.boss = None
                self.stage += 1
                self.stage_timer = 0
                self.banner = (f"STAGE {self.stage}", 150)
                self.sfx.play("clear")

        for s in self.shots:
            s.update()
        for it in self.items:
            it.update()
            if p.alive and not it.dead and dist2(it.x, it.y, p.x, p.y) < 22 ** 2:
                self.collect_item(it)
        for b in self.bombs:
            b.update(self.scroll_speed)
            if b.done:
                self.bomb_explode(b.tx, b.ty)
        for e in self.air:
            e.update(self)
        for g in self.ground:
            g.update(self)
        for b in self.ebullets:
            b.update()

        # 플레이어 탄 vs 공중 적 / 보스
        for s in self.shots:
            if s.dead:
                continue
            if self.boss and self.boss.hit(self, s.x, s.y):
                s.dead = True
                continue
            for e in self.air:
                if not e.dead and dist2(s.x, s.y, e.x, e.y) < (e.r + 4) ** 2:
                    s.dead = True
                    e.hp -= 1
                    e.flash = 4
                    if e.hp <= 0:
                        e.dead = True
                        self.explode(e.x, e.y, 1.0)
                        self.add_score(e.score, e.x, e.y)
                        if random.random() < ITEM_DROP_CHANCE[e.kind]:
                            self.items.append(Item(e.x, e.y))
                    else:
                        self.sfx.play("hit")
                    break

        # 플레이어 피격
        if p.alive and p.invuln <= 0:
            for b in self.ebullets:
                if dist2(b.x, b.y, p.x, p.y) < 8 ** 2:
                    b.dead = True
                    self.kill_player()
                    break
        if p.alive and p.invuln <= 0:
            for e in self.air:
                if not e.dead and dist2(e.x, e.y, p.x, p.y) < (e.r + 8) ** 2:
                    e.dead = True
                    self.explode(e.x, e.y)
                    self.kill_player()
                    break
        if p.alive and p.invuln <= 0 and self.boss and self.boss.collides(p.x, p.y):
            self.kill_player()

        self.shots = [s for s in self.shots if not s.dead]
        self.bombs = [b for b in self.bombs if not b.done]
        self.items = [it for it in self.items if not it.dead]
        self.air = [e for e in self.air if not e.dead]
        self.ground = [g for g in self.ground if not g.dead]
        self.ebullets = [b for b in self.ebullets if not b.dead]

    def update_effects(self):
        for pt in self.particles:
            pt.update(self.scroll_speed)
        self.particles = [pt for pt in self.particles if pt.life > 0]
        for r in self.rings:
            r[2] += max(2.5, r[3] / 12)
            if r[4]:
                r[1] += self.scroll_speed
        self.rings = [r for r in self.rings if r[2] < r[3]]
        for c in self.craters:
            c[1] += self.scroll_speed
        self.craters = [c for c in self.craters if c[1] < HEIGHT + 15 * c[2]]
        for pp in self.popups:
            pp.y -= 0.8
            pp.life -= 1
        self.popups = [pp for pp in self.popups if pp.life > 0]
        if self.shake > 0:
            self.shake -= 1

    # ---- 그리기 -----------------------------------------------------------
    def text(self, surf, msg, font, color, center=None, topleft=None, topright=None):
        img = font.render(msg, True, color)
        shadow = font.render(msg, True, (0, 0, 0))
        rect = img.get_rect()
        if center:
            rect.center = center
        elif topleft:
            rect.topleft = topleft
        elif topright:
            rect.topright = topright
        surf.blit(shadow, rect.move(2, 2))
        surf.blit(img, rect)

    def draw_world(self):
        w = self.world
        self.terrain.draw(w)
        for cx, cy, scale in self.craters:
            img = self.crater_imgs[scale]
            w.blit(img, img.get_rect(center=(int(cx), int(cy))))
        for g in self.ground:
            g.draw(w)
        for b in self.bombs:
            b.draw(w)

        p = self.player
        if self.state == "playing" and p.alive:
            w.blit(self.shadow, (p.x - 20 + 22, p.y - 20 + 30))
        for e in self.air:
            e.draw(w)
        if self.boss:
            self.boss.draw(w, self.t)
        for s in self.shots:
            s.draw(w)
        for it in self.items:
            it.draw(w, self.font_s)
        if self.state == "playing" and p.alive:
            p.draw(w, self.t)
            self.draw_reticle(w)
        for pt in self.particles:
            pt.draw(w)
        for x, y, r, rmax, _ in self.rings:
            width = max(1, int(4 * (1 - r / rmax)))
            pygame.draw.circle(w, (255, 230, 170), (int(x), int(y)), int(r), width)
        for b in self.ebullets:
            b.draw(w, self.t)
        for pp in self.popups:
            self.text(w, pp.text, self.font_s, pp.color, center=(int(pp.x), int(pp.y)))

    def draw_reticle(self, surf):
        p = self.player
        tx, ty = int(p.x), int(p.y - BOMB_RANGE)
        locked = any(dist2(g.x, g.y, tx, ty) < (g.r + BOMB_RADIUS) ** 2 for g in self.ground)
        col = (255, 60, 60) if locked else (230, 230, 230)
        s, l = 12, 6
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx, cy = tx + sx * s, ty + sy * s
                pygame.draw.line(surf, col, (cx, cy), (cx - sx * l, cy), 2)
                pygame.draw.line(surf, col, (cx, cy), (cx, cy - sy * l), 2)
        if locked and (self.t // 4) % 2:
            pygame.draw.circle(surf, col, (tx, ty), 3)

    def draw_hud(self):
        scr = self.screen
        self.text(scr, f"SCORE {self.score:08d}", self.font_s, (255, 255, 255), topleft=(10, 10))
        self.text(scr, f"HI {max(self.hiscore, self.score):08d}", self.font_s, (255, 220, 120),
                  center=(WIDTH // 2 + 40, 18))
        self.text(scr, f"STAGE {self.stage}", self.font_s, (150, 220, 255), topright=(WIDTH - 10, 10))
        for i in range(max(0, self.player.lives)):
            pts = [(x * 0.6 + 20 + i * 22, y * 0.6 + HEIGHT - 22) for x, y in ship_points(0, 0)]
            pygame.draw.polygon(scr, (205, 212, 225), pts)
        power = self.player.power
        self.text(scr, f"SHOT x{SHOT_LEVELS[power][0]}", self.font_s, SHOT_COLORS[power],
                  topright=(WIDTH - 10, HEIGHT - 28))
        if self.boss:
            self.boss.draw_bar(scr)
        text, timer = self.banner
        if timer > 0:
            if (timer // 8) % 2 or text != "WARNING!":
                col = (255, 80, 80) if text == "WARNING!" else (255, 255, 255)
                self.text(scr, text, self.font_l, col, center=(WIDTH // 2, HEIGHT // 2 - 60))
            self.banner = (text, timer - 1)
        if self.paused:
            self.text(scr, "PAUSED", self.font_l, (255, 255, 255), center=(WIDTH // 2, HEIGHT // 2))

    def draw_title(self):
        scr = self.screen
        self.text(scr, "SKY RAIDER", self.font_l, (255, 220, 90), center=(WIDTH // 2, 200))
        self.text(scr, "VERTICAL SCROLLING SHOOTER", self.font_s, (220, 230, 255), center=(WIDTH // 2, 250))
        lines = ["MOVE   : ARROWS / WASD",
                 "SHOT   : Z / J   (air targets)",
                 "BOMB   : X / K   (ground targets)",
                 "ITEM   : P -> SHOT x2/4/8/16",
                 "PAUSE  : P"]
        for i, line in enumerate(lines):
            self.text(scr, line, self.font_s, (255, 255, 255), topleft=(90, 340 + i * 28))
        if (pygame.time.get_ticks() // 500) % 2:
            self.text(scr, "PRESS ENTER TO START", self.font_m, (255, 255, 255), center=(WIDTH // 2, 540))
        self.text(scr, f"HI {self.hiscore:08d}", self.font_s, (255, 220, 120), center=(WIDTH // 2, 30))

    def draw_gameover(self):
        self.draw_hud()
        self.text(self.screen, "GAME OVER", self.font_l, (255, 80, 80), center=(WIDTH // 2, HEIGHT // 2 - 30))
        if (pygame.time.get_ticks() // 500) % 2:
            self.text(self.screen, "PRESS ENTER TO RETRY", self.font_m, (255, 255, 255),
                      center=(WIDTH // 2, HEIGHT // 2 + 30))

    # ---- 메인 루프 --------------------------------------------------------
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.state in ("title", "gameover"):
                        self.reset()
                        self.state = "playing"
                        self.sfx.play("start")
                    elif event.key == pygame.K_p and self.state == "playing":
                        self.paused = not self.paused

            if not self.paused:
                self.terrain.update(self.scroll_speed)
                if self.state == "playing":
                    self.update_playing(pygame.key.get_pressed())
                else:
                    self.t += 1
                self.update_effects()

            self.draw_world()
            ox = oy = 0
            if self.shake > 0:
                ox = random.randint(-self.shake, self.shake)
                oy = random.randint(-self.shake, self.shake)
            self.screen.fill((0, 0, 0))
            self.screen.blit(self.world, (ox, oy))

            if self.state == "title":
                self.draw_title()
            elif self.state == "playing":
                self.draw_hud()
            else:
                self.draw_gameover()

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()
    pygame.quit()
    sys.exit()
