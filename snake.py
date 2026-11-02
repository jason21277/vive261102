"""
AI 뱀 vs 사람 뱀 - 사과 먹기 대결 (tkinter, 추가 설치 불필요)

조작:
  방향키 / WASD : 사람 뱀(초록) 이동
  P             : 일시정지
  Space / R     : 게임 종료 후 다시 시작
  Esc           : 종료

규칙:
  - 사과를 먹으면 1점 + 몸 길이 1 증가
  - 벽, 자기 몸, 상대 뱀 몸에 부딪히면 패배
  - 머리끼리 정면 충돌하면 무승부
  - 제한 시간이 끝나면 점수가 높은 쪽이 승리
"""

import random
import tkinter as tk
from collections import deque

# ---------------- 설정 ----------------
CELL = 22
COLS, ROWS = 30, 22
SPEED_MS = 110          # 한 틱 간격 (작을수록 빠름)
TIME_LIMIT = 90         # 제한 시간(초)
APPLE_COUNT = 2         # 동시에 놓이는 사과 수

UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)
DIRS = [UP, DOWN, LEFT, RIGHT]

BG = "#1e1e1e"
GRID = "#262626"
HUMAN_HEAD, HUMAN_BODY = "#7CFC00", "#2e8b57"
AI_HEAD, AI_BODY = "#4fc3f7", "#1565c0"
APPLE = "#ff3b3b"


def add(p, d):
    return (p[0] + d[0], p[1] + d[1])


def in_bounds(p):
    return 0 <= p[0] < COLS and 0 <= p[1] < ROWS


class Snake:
    def __init__(self, body, direction, name):
        self.body = deque(body)      # body[0] = 머리
        self.dir = direction
        self.next_dir = direction
        self.name = name
        self.grow = 0
        self.score = 0
        self.alive = True

    @property
    def head(self):
        return self.body[0]

    def set_dir(self, d):
        # 바로 반대 방향으로는 꺾을 수 없음
        if (d[0] + self.dir[0], d[1] + self.dir[1]) != (0, 0):
            self.next_dir = d

    def next_head(self):
        self.dir = self.next_dir
        return add(self.head, self.dir)

    def move(self, new_head):
        self.body.appendleft(new_head)
        if self.grow > 0:
            self.grow -= 1
        else:
            self.body.pop()


class SnakeAI:
    """BFS로 가장 가까운 사과를 찾고, 막다른 길을 피하도록 공간을 검사하는 AI."""

    def __init__(self, me: Snake, enemy: Snake):
        self.me = me
        self.enemy = enemy

    def blocked_cells(self):
        blocked = set(self.me.body) | set(self.enemy.body)
        # 다음 틱에 꼬리는 비워지므로 통과 가능 (자라는 중이 아니라면)
        if self.me.grow == 0:
            blocked.discard(self.me.body[-1])
        if self.enemy.grow == 0 and self.enemy.alive:
            blocked.discard(self.enemy.body[-1])
        return blocked

    def flood_size(self, start, blocked, limit):
        if start in blocked or not in_bounds(start):
            return 0
        seen = {start}
        q = deque([start])
        while q and len(seen) < limit:
            c = q.popleft()
            for d in DIRS:
                n = add(c, d)
                if in_bounds(n) and n not in blocked and n not in seen:
                    seen.add(n)
                    q.append(n)
        return len(seen)

    def bfs_first_step(self, start, targets, blocked):
        """start에서 targets 중 가장 가까운 곳까지의 첫 이동 방향."""
        q = deque()
        seen = {start}
        for d in DIRS:
            n = add(start, d)
            if in_bounds(n) and n not in blocked and n not in seen:
                if n in targets:
                    return d
                seen.add(n)
                q.append((n, d))
        while q:
            c, first = q.popleft()
            for d in DIRS:
                n = add(c, d)
                if in_bounds(n) and n not in blocked and n not in seen:
                    if n in targets:
                        return first
                    seen.add(n)
                    q.append((n, first))
        return None

    def choose(self, apples):
        me, head = self.me, self.me.head
        blocked = self.blocked_cells()
        need = len(me.body) + 2

        # 상대 머리가 다음에 갈 수 있는 칸 (정면 충돌 위험)
        danger = set()
        if self.enemy.alive:
            for d in DIRS:
                danger.add(add(self.enemy.head, d))

        candidates = []
        for d in DIRS:
            if (d[0] + me.dir[0], d[1] + me.dir[1]) == (0, 0):
                continue
            n = add(head, d)
            if not in_bounds(n) or n in blocked:
                continue
            space = self.flood_size(n, blocked | {head}, need)
            candidates.append((d, n, space))

        if not candidates:
            return me.dir  # 갈 곳이 없음

        # 1) 사과로 가는 최단 경로가 안전하면 그 길로
        step = self.bfs_first_step(head, set(apples), blocked)
        if step is not None:
            for d, n, space in candidates:
                if d == step and space >= need and n not in danger:
                    return d

        # 2) 아니면 가장 넓은 공간이 남는 방향 (위험 칸은 후순위)
        candidates.sort(key=lambda c: (c[1] not in danger, c[2]), reverse=True)
        return candidates[0][0]


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Snake Battle - 사람 vs AI")
        root.resizable(False, False)

        self.info = tk.Label(root, font=("Consolas", 14, "bold"),
                             bg="#111", fg="white", pady=6)
        self.info.pack(fill="x")
        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        keymap = {
            "Up": UP, "Down": DOWN, "Left": LEFT, "Right": RIGHT,
            "w": UP, "s": DOWN, "a": LEFT, "d": RIGHT,
            "W": UP, "S": DOWN, "A": LEFT, "D": RIGHT,
        }
        for key, d in keymap.items():
            root.bind(f"<{key}>", lambda e, d=d: self.human.set_dir(d))
        root.bind("<p>", lambda e: self.toggle_pause())
        root.bind("<P>", lambda e: self.toggle_pause())
        root.bind("<space>", lambda e: self.restart_if_over())
        root.bind("<r>", lambda e: self.restart_if_over())
        root.bind("<R>", lambda e: self.restart_if_over())
        root.bind("<Escape>", lambda e: root.destroy())

        self.after_id = None
        self.reset()

    # ---------- 상태 ----------
    def reset(self):
        mid = ROWS // 2
        self.human = Snake([(5, mid), (4, mid), (3, mid)], RIGHT, "사람")
        self.ai = Snake([(COLS - 6, mid), (COLS - 5, mid), (COLS - 4, mid)],
                        LEFT, "AI")
        self.brain = SnakeAI(self.ai, self.human)
        self.apples = set()
        for _ in range(APPLE_COUNT):
            self.spawn_apple()
        self.ticks_left = TIME_LIMIT * 1000 // SPEED_MS
        self.paused = False
        self.over = False
        self.message = ""
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.loop()

    def spawn_apple(self):
        occupied = set(self.human.body) | set(self.ai.body) | self.apples
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in occupied]
        if free:
            self.apples.add(random.choice(free))

    def toggle_pause(self):
        if not self.over:
            self.paused = not self.paused
            self.draw()

    def restart_if_over(self):
        if self.over:
            self.reset()

    # ---------- 게임 진행 ----------
    def step(self):
        h, a = self.human, self.ai
        a.set_dir(self.brain.choose(self.apples))

        nh, na = h.next_head(), a.next_head()

        # 다음 틱 꼬리가 빠지는지 고려해서 충돌 판정
        def body_after(s):
            body = list(s.body)
            return set(body if s.grow > 0 else body[:-1])

        hb, ab = body_after(h), body_after(a)
        h_dead = not in_bounds(nh) or nh in hb or nh in ab
        a_dead = not in_bounds(na) or na in ab or na in hb
        if nh == na:
            h_dead = a_dead = True

        if h_dead or a_dead:
            h.alive, a.alive = not h_dead, not a_dead
            self.finish()
            return

        for s, nxt in ((h, nh), (a, na)):
            s.move(nxt)
            if nxt in self.apples:
                self.apples.remove(nxt)
                s.score += 1
                s.grow += 1
                self.spawn_apple()

        self.ticks_left -= 1
        if self.ticks_left <= 0:
            self.finish()

    def finish(self):
        self.over = True
        h, a = self.human, self.ai
        if not h.alive and not a.alive:
            self.message = "정면 충돌! 무승부"
        elif not h.alive:
            self.message = "사람 뱀 충돌 - AI 승리!"
        elif not a.alive:
            self.message = "AI 뱀 충돌 - 사람 승리!"
        elif h.score > a.score:
            self.message = "시간 종료 - 사람 승리!"
        elif a.score > h.score:
            self.message = "시간 종료 - AI 승리!"
        else:
            self.message = "시간 종료 - 무승부"

    def loop(self):
        if not self.paused and not self.over:
            self.step()
        self.draw()
        self.after_id = self.root.after(SPEED_MS, self.loop)

    # ---------- 그리기 ----------
    def draw_cell(self, p, color, pad=1, oval=False):
        x, y = p[0] * CELL, p[1] * CELL
        shape = self.canvas.create_oval if oval else self.canvas.create_rectangle
        shape(x + pad, y + pad, x + CELL - pad, y + CELL - pad,
              fill=color, outline="")

    def draw_snake(self, s, head_color, body_color):
        for i, p in enumerate(s.body):
            self.draw_cell(p, head_color if i == 0 else body_color,
                           pad=1 if i == 0 else 2)

    def draw(self):
        c = self.canvas
        c.delete("all")
        for x in range(0, COLS * CELL, CELL):
            c.create_line(x, 0, x, ROWS * CELL, fill=GRID)
        for y in range(0, ROWS * CELL, CELL):
            c.create_line(0, y, COLS * CELL, y, fill=GRID)

        for p in self.apples:
            self.draw_cell(p, APPLE, pad=3, oval=True)
        self.draw_snake(self.ai, AI_HEAD, AI_BODY)
        self.draw_snake(self.human, HUMAN_HEAD, HUMAN_BODY)

        secs = max(0, self.ticks_left * SPEED_MS // 1000)
        self.info.config(
            text=f"사람(초록) {self.human.score}   :   {self.ai.score} AI(파랑)"
                 f"      남은 시간 {secs}s")

        cx, cy = COLS * CELL // 2, ROWS * CELL // 2
        if self.over:
            c.create_rectangle(cx - 220, cy - 50, cx + 220, cy + 50,
                               fill="#000", outline="white")
            c.create_text(cx, cy - 12, text=self.message, fill="white",
                          font=("Malgun Gothic", 18, "bold"))
            c.create_text(cx, cy + 22, text="Space / R : 다시 시작   Esc : 종료",
                          fill="#bbb", font=("Malgun Gothic", 11))
        elif self.paused:
            c.create_text(cx, cy, text="일시정지 (P)", fill="white",
                          font=("Malgun Gothic", 22, "bold"))


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()
