"""A small Breakout game built with Python's standard-library tkinter."""

import tkinter as tk


WIDTH = 800
HEIGHT = 600
PADDLE_WIDTH = 110
PADDLE_HEIGHT = 14
BALL_SIZE = 14
BRICK_COLUMNS = 10
BRICK_ROWS = 5
BRICK_WIDTH = 68
BRICK_HEIGHT = 22
BRICK_GAP = 7


class Breakout:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("블록 깨기")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            background="#101827",
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.focus_set()

        self.score = 0
        self.lives = 3
        self.level = 1
        self.state = "ready"
        self.keys: set[str] = set()
        self.paddle_x = WIDTH / 2
        self.ball_x = WIDTH / 2
        self.ball_y = HEIGHT - 90
        self.ball_dx = 0.0
        self.ball_dy = 0.0
        self.bricks: dict[int, int] = {}

        self.canvas.create_text(
            18, 18, anchor="nw", text="", fill="#ffffff", font=("Arial", 13, "bold"), tags="hud"
        )
        self.canvas.create_text(
            WIDTH / 2,
            HEIGHT / 2,
            text="",
            fill="#ffffff",
            font=("Arial", 22, "bold"),
            tags="message",
        )
        self.paddle = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="#38bdf8", outline="", tags="paddle"
        )
        self.ball = self.canvas.create_oval(
            0, 0, 0, 0, fill="#f8fafc", outline="", tags="ball"
        )

        self.canvas.bind("<KeyPress>", self._key_down)
        self.canvas.bind("<KeyRelease>", self._key_up)
        self.canvas.bind("<Motion>", self._mouse_move)
        self.canvas.bind("<Button-1>", self._mouse_move)
        self.root.bind("<FocusOut>", self._clear_keys)

        self._create_level()
        self._place_paddle()
        self._place_ball()
        self._show_message("SPACE를 눌러 시작하세요\n← → 또는 마우스로 패들 이동")
        self._update_hud()
        self._tick()

    def _create_level(self) -> None:
        for brick in self.bricks:
            self.canvas.delete(brick)
        self.bricks.clear()

        total_width = BRICK_COLUMNS * BRICK_WIDTH + (BRICK_COLUMNS - 1) * BRICK_GAP
        left = (WIDTH - total_width) / 2
        colors = ["#fb7185", "#fb923c", "#facc15", "#4ade80", "#60a5fa"]
        for row in range(BRICK_ROWS):
            for column in range(BRICK_COLUMNS):
                x1 = left + column * (BRICK_WIDTH + BRICK_GAP)
                y1 = 72 + row * (BRICK_HEIGHT + BRICK_GAP)
                brick = self.canvas.create_rectangle(
                    x1,
                    y1,
                    x1 + BRICK_WIDTH,
                    y1 + BRICK_HEIGHT,
                    fill=colors[row],
                    outline="#101827",
                    width=2,
                    tags="brick",
                )
                self.bricks[brick] = BRICK_ROWS - row

    def _place_paddle(self) -> None:
        half = PADDLE_WIDTH / 2
        self.paddle_x = max(half, min(WIDTH - half, self.paddle_x))
        y1 = HEIGHT - 48 - PADDLE_HEIGHT
        self.canvas.coords(
            self.paddle,
            self.paddle_x - half,
            y1,
            self.paddle_x + half,
            y1 + PADDLE_HEIGHT,
        )

    def _place_ball(self) -> None:
        half = BALL_SIZE / 2
        self.canvas.coords(
            self.ball,
            self.ball_x - half,
            self.ball_y - half,
            self.ball_x + half,
            self.ball_y + half,
        )

    def _update_hud(self) -> None:
        self.canvas.itemconfigure(
            "hud",
            text=f"점수: {self.score}    목숨: {self.lives}    레벨: {self.level}    P: 일시정지",
        )

    def _show_message(self, message: str) -> None:
        self.canvas.itemconfigure("message", text=message)

    def _key_down(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key in ("left", "right"):
            self.keys.add(key)
        elif key == "space":
            if self.state == "ready":
                self.state = "running"
                self.ball_dx = 3.4
                self.ball_dy = -5.2
                self._show_message("")
            elif self.state in ("game_over", "won"):
                self._reset()
        elif key == "p":
            if self.state == "running":
                self.state = "paused"
                self._show_message("일시정지\nP를 눌러 계속")
            elif self.state == "paused":
                self.state = "running"
                self._show_message("")
        elif key == "r":
            self._reset()

    def _key_up(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym.lower())

    def _clear_keys(self, _event: tk.Event) -> None:
        self.keys.clear()

    def _mouse_move(self, event: tk.Event) -> None:
        self.paddle_x = event.x
        self._place_paddle()

    def _reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self.state = "ready"
        self.paddle_x = WIDTH / 2
        self.ball_x = WIDTH / 2
        self.ball_y = HEIGHT - 90
        self.ball_dx = 0.0
        self.ball_dy = 0.0
        self._create_level()
        self._place_paddle()
        self._place_ball()
        self._show_message("SPACE를 눌러 시작하세요\n← → 또는 마우스로 패들 이동")
        self._update_hud()

    def _move_ball(self) -> None:
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        radius = BALL_SIZE / 2

        if self.ball_x - radius <= 0:
            self.ball_x = radius
            self.ball_dx = abs(self.ball_dx)
        elif self.ball_x + radius >= WIDTH:
            self.ball_x = WIDTH - radius
            self.ball_dx = -abs(self.ball_dx)
        if self.ball_y - radius <= 34:
            self.ball_y = 34 + radius
            self.ball_dy = abs(self.ball_dy)

        self._place_ball()
        ball_box = self.canvas.coords(self.ball)
        paddle_box = self.canvas.coords(self.paddle)
        if (
            self.ball_dy > 0
            and ball_box[2] >= paddle_box[0]
            and ball_box[0] <= paddle_box[2]
            and ball_box[3] >= paddle_box[1]
            and ball_box[1] <= paddle_box[3]
        ):
            offset = (self.ball_x - self.paddle_x) / (PADDLE_WIDTH / 2)
            self.ball_dx = max(-6.0, min(6.0, offset * 5.5))
            self.ball_dy = -max(4.0, (self.ball_dx**2 + self.ball_dy**2) ** 0.5)
            self.ball_y = paddle_box[1] - radius
            self._place_ball()
            ball_box = self.canvas.coords(self.ball)

        for brick, points in list(self.bricks.items()):
            brick_box = self.canvas.coords(brick)
            if (
                ball_box[2] < brick_box[0]
                or ball_box[0] > brick_box[2]
                or ball_box[3] < brick_box[1]
                or ball_box[1] > brick_box[3]
            ):
                continue

            overlap_x = min(ball_box[2] - brick_box[0], brick_box[2] - ball_box[0])
            overlap_y = min(ball_box[3] - brick_box[1], brick_box[3] - ball_box[1])
            if overlap_x < overlap_y:
                self.ball_dx = -self.ball_dx
                self.ball_x += -overlap_x if self.ball_x < (brick_box[0] + brick_box[2]) / 2 else overlap_x
            else:
                self.ball_dy = -self.ball_dy
                self.ball_y += -overlap_y if self.ball_y < (brick_box[1] + brick_box[3]) / 2 else overlap_y
            self.canvas.delete(brick)
            del self.bricks[brick]
            self.score += points * 10
            self._update_hud()
            break

        self._place_ball()

        if self.ball_y - radius > HEIGHT:
            self.lives -= 1
            self._update_hud()
            if self.lives == 0:
                self.state = "game_over"
                self._show_message(f"게임 오버!\n최종 점수: {self.score}\nSPACE 또는 R로 다시 시작")
            else:
                self.state = "ready"
                self.ball_x = WIDTH / 2
                self.ball_y = HEIGHT - 90
                self.ball_dx = 0.0
                self.ball_dy = 0.0
                self._place_ball()
                self._show_message("공을 놓쳤어요!\nSPACE를 눌러 다시 시작")
            return

        if not self.bricks:
            self.level += 1
            self._create_level()
            self.ball_x = WIDTH / 2
            self.ball_y = HEIGHT - 90
            self.ball_dx = 3.4
            self.ball_dy = -5.2
            self._place_ball()
            self._update_hud()

    def _tick(self) -> None:
        if "left" in self.keys:
            self.paddle_x -= 8
        if "right" in self.keys:
            self.paddle_x += 8
        self._place_paddle()

        if self.state == "running":
            self._move_ball()

        self.root.after(16, self._tick)


def main() -> None:
    root = tk.Tk()
    Breakout(root)
    root.mainloop()


if __name__ == "__main__":
    main()
