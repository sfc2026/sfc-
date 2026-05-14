import tkinter as tk
from tkinter import ttk
import winsound
import threading
import os
import sys

WORK_MINUTES = 25
SHORT_BREAK_MINUTES = 5
LONG_BREAK_MINUTES = 15
LONG_BREAK_INTERVAL = 4  # long break every 4 pomodoros

COLORS = {
    "work": "#e74c3c",
    "short_break": "#2ecc71",
    "long_break": "#3498db",
    "paused": "#95a5a6",
    "bg": "#1e1e2e",
    "panel": "#2a2a3e",
    "text": "#cdd6f4",
    "subtext": "#6c7086",
    "accent": "#cba6f7",
    "button_bg": "#313244",
    "button_hover": "#45475a",
    "progress_bg": "#313244",
    "ring": "#cba6f7",
}


class PomodoroTimer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Pomodoro Timer")
        self.root.geometry("360x520")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg"])

        # icon
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
            self.root.iconbitmap(os.path.join(base, "tomato.ico"))
        except Exception:
            pass

        # state
        self.seconds = WORK_MINUTES * 60
        self.running = False
        self.paused = False
        self.mode = "work"  # work | short_break | long_break
        self.pomodoro_count = 0
        self.timer_id = None
        self.flash_state = False

        self._build_ui()
        self._update_display()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    # ── UI ──────────────────────────────────────────────────

    def _build_ui(self):
        # title
        title = tk.Label(
            self.root,
            text="POMODORO",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["subtext"],
        )
        title.pack(pady=(16, 4))

        self.mode_label = tk.Label(
            self.root,
            text="Focus",
            font=("Segoe UI", 13),
            bg=COLORS["bg"],
            fg=COLORS["work"],
        )
        self.mode_label.pack()

        # canvas ring
        self.canvas = tk.Canvas(
            self.root,
            width=240,
            height=240,
            bg=COLORS["bg"],
            highlightthickness=0,
        )
        self.canvas.pack(pady=(12, 0))

        # timer text
        self.timer_text = self.canvas.create_text(
            120, 112, text="25:00", font=("Segoe UI", 36, "bold"), fill=COLORS["text"]
        )
        self.status_text = self.canvas.create_text(
            120, 152, text="Ready", font=("Segoe UI", 11), fill=COLORS["subtext"]
        )

        # session counter
        self.counter_label = tk.Label(
            self.root,
            text="Sessions: 0",
            font=("Segoe UI", 10),
            bg=COLORS["bg"],
            fg=COLORS["subtext"],
        )
        self.counter_label.pack(pady=(8, 0))

        # progress bar
        self.progress = ttk.Progressbar(
            self.root,
            orient="horizontal",
            length=300,
            mode="determinate",
            style="TProgressbar",
        )
        self.progress.pack(pady=(12, 16))

        # buttons
        btn_frame = tk.Frame(self.root, bg=COLORS["bg"])
        btn_frame.pack()

        self.start_btn = self._make_button(btn_frame, "▶︎ Start", self._on_start)
        self.start_btn.pack(side="left", padx=4)

        self.pause_btn = self._make_button(btn_frame, "⏸︎ Pause", self._on_pause)
        self.pause_btn.pack(side="left", padx=4)
        self.pause_btn.config(state="disabled")

        self.reset_btn = self._make_button(btn_frame, "↺ Reset", self._on_reset)
        self.reset_btn.pack(side="left", padx=4)

        # mode toggle at bottom
        toggle_frame = tk.Frame(self.root, bg=COLORS["bg"])
        toggle_frame.pack(pady=(16, 4))

        modes = [
            ("Focus", "work"),
            ("Break", "short_break"),
            ("Long", "long_break"),
        ]
        self.mode_buttons = {}
        for label, mode in modes:
            btn = tk.Label(
                toggle_frame,
                text=label,
                font=("Segoe UI", 9),
                bg=COLORS["button_bg"],
                fg=COLORS["subtext"],
                padx=10,
                pady=4,
                cursor="hand2",
            )
            btn.pack(side="left", padx=3)
            btn.bind("<Button-1>", lambda e, m=mode: self._switch_mode(m))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=COLORS["button_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=COLORS["button_bg"]))
            self.mode_buttons[mode] = btn

        self._highlight_mode_button()

        # always-on-top
        self.top_var = tk.BooleanVar(value=False)
        top_cb = tk.Checkbutton(
            self.root,
            text="Always on top",
            variable=self.top_var,
            command=self._toggle_top,
            font=("Segoe UI", 8),
            bg=COLORS["bg"],
            fg=COLORS["subtext"],
            selectcolor=COLORS["bg"],
            activebackground=COLORS["bg"],
            activeforeground=COLORS["subtext"],
        )
        top_cb.pack(pady=(6, 10))

    def _make_button(self, parent, text, command):
        btn = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["button_bg"],
            fg=COLORS["text"],
            padx=16,
            pady=6,
            cursor="hand2",
        )
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.configure(bg=COLORS["button_hover"]))
        btn.bind("<Leave>", lambda e: btn.configure(bg=COLORS["button_bg"]))
        btn.pack_propagate(False)
        return btn

    # ── Actions ─────────────────────────────────────────────

    def _on_start(self):
        if self.paused:
            self.paused = False
            self.running = True
            self._toggle_buttons(running=True)
            self._tick()
        else:
            self.running = True
            self.paused = False
            self._toggle_buttons(running=True)
            self._tick()

    def _on_pause(self):
        self.running = False
        self.paused = True
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self._toggle_buttons(running=False)
        self.canvas.itemconfig(self.status_text, text="Paused", fill=COLORS["paused"])
        self._draw_ring(self.seconds, "paused")

    def _on_reset(self):
        self.running = False
        self.paused = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.seconds = self._mode_duration()
        self._toggle_buttons(running=False)
        self._update_display()

    def _switch_mode(self, mode):
        if self.running or self.paused:
            return  # don't switch while timer is active
        self.mode = mode
        self.seconds = self._mode_duration()
        self._highlight_mode_button()
        self._update_display()

    def _toggle_top(self):
        self.root.attributes("-topmost", self.top_var.get())

    # ── Timer Logic ─────────────────────────────────────────

    def _tick(self):
        if not self.running:
            return

        if self.seconds > 0:
            self.seconds -= 1
            self._update_display()
            self.timer_id = self.root.after(1000, self._tick)
        else:
            self._timer_finished()

    def _timer_finished(self):
        self.running = False
        self.timer_id = None
        self._toggle_buttons(running=False)

        threading.Thread(target=self._play_sound, daemon=True).start()

        if self.mode == "work":
            self.pomodoro_count += 1
            self.counter_label.config(text=f"Sessions: {self.pomodoro_count}")

            if self.pomodoro_count % LONG_BREAK_INTERVAL == 0:
                self.mode = "long_break"
            else:
                self.mode = "short_break"
        else:
            self.mode = "work"

        self.seconds = self._mode_duration()
        self._highlight_mode_button()
        self._update_display()
        self._flash_notify()

    def _flash_notify(self):
        """Brief flash effect when timer finishes."""
        self.flash_state = True
        self._do_flash(4)  # 4 flashes

    def _do_flash(self, count):
        if count <= 0:
            self.flash_state = False
            self.canvas.configure(bg=COLORS["bg"])
            return
        color = COLORS["accent"] if self.flash_state else COLORS["bg"]
        self.canvas.configure(bg=color)
        self.flash_state = not self.flash_state
        self.root.after(250, lambda: self._do_flash(count - 1))

    def _play_sound(self):
        for _ in range(3):
            winsound.Beep(880, 150)
            winsound.Beep(1100, 200)

    # ── Display ─────────────────────────────────────────────

    def _update_display(self):
        total = self._mode_duration()
        elapsed = total - self.seconds
        frac = elapsed / total if total > 0 else 0

        m, s = divmod(self.seconds, 60)
        self.canvas.itemconfig(self.timer_text, text=f"{m:02d}:{s:02d}")
        self.progress["value"] = frac * 100

        mode_info = {
            "work": ("Focus", COLORS["work"]),
            "short_break": ("Break", COLORS["short_break"]),
            "long_break": ("Long Break", COLORS["long_break"]),
        }
        label, color = mode_info[self.mode]
        self.mode_label.config(text=label, fg=color)
        self.canvas.itemconfig(self.status_text, text="", fill=color)

        if not self.running and not self.paused:
            self.canvas.itemconfig(self.status_text, text="Ready")
            color = COLORS["subtext"]

        self._draw_ring(self.seconds, self.mode)

    def _draw_ring(self, remaining, mode):
        self.canvas.delete("ring")
        x0, y0, x1, y1 = 30, 30, 210, 210
        total = self._mode_duration()
        extent = 359.999 * (1 - remaining / total) if total > 0 else 0

        color = COLORS.get(mode, COLORS["ring"])
        if mode == "paused":
            color = COLORS["paused"]

        # background ring
        self.canvas.create_arc(
            x0, y0, x1, y1,
            start=90, extent=-359.999,
            outline=COLORS["progress_bg"],
            width=10,
            style="arc",
            tags="ring",
        )
        # progress ring
        if extent > 0:
            self.canvas.create_arc(
                x0, y0, x1, y1,
                start=90, extent=-extent,
                outline=color,
                width=10,
                style="arc",
                tags="ring",
            )

    def _highlight_mode_button(self):
        for m, btn in self.mode_buttons.items():
            if m == self.mode:
                btn.config(bg=COLORS["accent"], fg=COLORS["bg"])
            else:
                btn.config(bg=COLORS["button_bg"], fg=COLORS["subtext"])

    # ── Helpers ─────────────────────────────────────────────

    def _mode_duration(self):
        if self.mode == "work":
            return WORK_MINUTES * 60
        elif self.mode == "short_break":
            return SHORT_BREAK_MINUTES * 60
        else:
            return LONG_BREAK_MINUTES * 60

    def _toggle_buttons(self, running):
        if running:
            self.start_btn.config(state="disabled", fg=COLORS["subtext"])
            self.pause_btn.config(state="normal", fg=COLORS["text"])
        else:
            self.start_btn.config(state="normal", fg=COLORS["text"])
            self.pause_btn.config(state="disabled", fg=COLORS["subtext"])

    def _on_close(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()


if __name__ == "__main__":
    PomodoroTimer()
