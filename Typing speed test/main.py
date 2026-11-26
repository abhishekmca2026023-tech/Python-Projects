import json
import os
import random
import time
import tkinter as tk
from collections import Counter
from tkinter import messagebox, simpledialog, ttk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEADERBOARD_FILE = os.path.join(SCRIPT_DIR, "typing_leaderboard.json")

TEXT_POOLS = {
    "Easy": [
        "the quick brown fox jumps over the lazy dog near the quiet river bank",
        "building speed on a keyboard takes steady daily practice and good posture",
        "focus on accuracy first and your typing speed will naturally follow over time",
        "a clear morning walk helps reset your mind before starting a busy work day",
    ],
    "Medium": [
        "Success is not final, failure is not fatal: it is the courage to continue that counts.",
        "Premature optimization is the root of all evil in software engineering projects.",
        "Whenever you find yourself on the side of the majority, it is time to pause and reflect.",
        "Simplicity is about subtracting the obvious and adding the meaningful to your work.",
    ],
    "Hard (Symbols & Numbers)": [
        "Invoice #9482-B totaled $1,450.75 (including 8.25% tax) & shipped on 11/13/2026 @ 09:30 AM!",
        "Server 192.168.10.254 responded in 12.4ms — CPU load: 84.5%, RAM: 13.8GB / 16.0GB.",
        "Validate inputs with `^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$` before saving.",
        "Q4 Revenue: $84,920 (+17.4% YoY) | Margin: 32.1% | Ticket ID: [REQ-7741-X].",
    ],
    "Python Code": [
        "squares = {x: x**2 for x in range(1, 25) if x % 2 == 0}",
        "def fib(n): return n if n <= 1 else fib(n - 1) + fib(n - 2)",
        "with open('config.json', 'r', encoding='utf-8') as f: data = json.load(f)",
        "valid_users = list(filter(lambda u: u.get('active') and u['score'] >= 85, users))",
    ],
}


class TypingSpeedApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Advanced Python Typing Speed Test")
        self.root.geometry("920x640")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(False, False)

        # State variables
        self.difficulty_var = tk.StringVar(value="Medium")
        self.duration_var = tk.StringVar(value="Passage")
        self.custom_text = ""

        self.target_text = ""
        self.typed_chars = []
        self.start_time = None
        self.test_active = False
        self.test_finished = False
        self.timer_job = None

        # Telemetry across the whole session/run
        self.completed_chars_offset = 0
        self.completed_correct_offset = 0
        self.total_keystrokes = 0
        self.correct_keystrokes = 0
        self.missed_keys = Counter()
        self.peak_wpm = 0

        self.high_scores = self.load_leaderboard()
        self.build_ui()
        self.reset_test()

        # Bind global key press so the user can type immediately
        self.root.bind("<KeyPress>", self.on_key_press)

    def load_leaderboard(self) -> dict:
        if os.path.exists(LEADERBOARD_FILE):
            try:
                with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return {
                    key: value
                    for key, value in data.items()
                    if isinstance(key, str) and isinstance(value, dict)
                }
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def save_high_score(self, mode_key: str, wpm: int, accuracy: float) -> bool:
        previous = self.high_scores.get(mode_key)
        prev_best = previous.get("wpm", 0) if isinstance(previous, dict) else 0
        if wpm > prev_best:
            self.high_scores[mode_key] = {
                "wpm": wpm,
                "accuracy": accuracy,
                "date": time.strftime("%Y-%m-%d"),
            }
            try:
                with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.high_scores, f, indent=2)
            except OSError:
                pass
            return True
        return False

    def build_ui(self):
        # Top Header & Controls
        header = tk.Frame(self.root, bg="#181825", pady=12, padx=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="⚡ TYPING SPEED LAB",
            font=("Consolas", 18, "bold"),
            fg="#89b4fa",
            bg="#181825",
        ).pack(side="left")

        controls = tk.Frame(header, bg="#181825")
        controls.pack(side="right")

        tk.Label(controls, text="Pool:", fg="#cdd6f4", bg="#181825", font=("Segoe UI", 10)).pack(
            side="left", padx=(0, 5)
        )
        diff_menu = ttk.Combobox(
            controls,
            textvariable=self.difficulty_var,
            values=list(TEXT_POOLS.keys()) + ["Custom"],
            state="readonly",
            width=22,
        )
        diff_menu.pack(side="left", padx=(0, 12))
        diff_menu.bind("<<ComboboxSelected>>", self.on_mode_change)

        tk.Label(controls, text="Mode:", fg="#cdd6f4", bg="#181825", font=("Segoe UI", 10)).pack(
            side="left", padx=(0, 5)
        )
        dur_menu = ttk.Combobox(
            controls,
            textvariable=self.duration_var,
            values=["Passage", "15s", "30s", "60s"],
            state="readonly",
            width=10,
        )
        dur_menu.pack(side="left", padx=(0, 12))
        dur_menu.bind("<<ComboboxSelected>>", self.on_mode_change)

        tk.Button(
            controls,
            text="Restart (Esc)",
            command=self.reset_test,
            bg="#f38ba8",
            fg="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padx=10,
            pady=3,
        ).pack(side="left")

        # Live Metrics Dashboard
        stats_frame = tk.Frame(self.root, bg="#1e1e2e", pady=16, padx=20)
        stats_frame.pack(fill="x")

        self.stat_labels = {}
        metrics = [
            ("net_wpm", "NET WPM", "0", "#a6e3a1"),
            ("raw_wpm", "RAW WPM", "0", "#89dceb"),
            ("accuracy", "ACCURACY", "100.0%", "#f9e2af"),
            ("timer", "TIME", "0.0s", "#cba6f7"),
            ("best", "PERSONAL BEST", "0 WPM", "#fab387"),
        ]

        for key, title, default, color in metrics:
            card = tk.Frame(stats_frame, bg="#313244", padx=16, pady=10)
            card.pack(side="left", expand=True, fill="x", padx=5)
            tk.Label(
                card, text=title, font=("Segoe UI", 8, "bold"), fg="#a6adc8", bg="#313244"
            ).pack(anchor="w")
            val_lbl = tk.Label(
                card, text=default, font=("Consolas", 18, "bold"), fg=color, bg="#313244"
            )
            val_lbl.pack(anchor="w")
            self.stat_labels[key] = val_lbl

        # Target Passage Display
        text_container = tk.Frame(self.root, bg="#1e1e2e", padx=25, pady=5)
        text_container.pack(fill="both", expand=True)

        self.text_box = tk.Text(
            text_container,
            font=("Consolas", 18),
            bg="#181825",
            fg="#585b70",
            wrap="word",
            height=7,
            padx=20,
            pady=20,
            relief="flat",
            state="disabled",
            cursor="arrow",
        )
        self.text_box.pack(fill="both", expand=True)

        # Configure color tags for character states
        self.text_box.tag_config("untyped", foreground="#6c7086")
        self.text_box.tag_config("correct", foreground="#a6e3a1")
        self.text_box.tag_config("wrong", foreground="#f38ba8", background="#452736")
        self.text_box.tag_config("cursor", foreground="#cdd6f4", underline=True)

        # Analytics & Status Footer
        footer = tk.Frame(self.root, bg="#181825", padx=25, pady=14)
        footer.pack(fill="x", side="bottom")

        self.analytics_label = tk.Label(
            footer,
            text="Start typing anywhere to begin the test... Press [Esc] to reset at any time.",
            font=("Consolas", 11),
            fg="#bac2de",
            bg="#181825",
            justify="left",
        )
        self.analytics_label.pack(side="left")

    def get_mode_key(self) -> str:
        return f"{self.difficulty_var.get()} | {self.duration_var.get()}"

    def on_mode_change(self, _event=None):
        # Defocus combobox so spacebar/letters go to the typing handler
        self.root.focus_set()
        if self.difficulty_var.get() == "Custom":
            custom = simpledialog.askstring(
                "Custom Text",
                "Paste or type the passage you want to practice:",
                parent=self.root,
            )
            if custom and custom.strip():
                self.custom_text = " ".join(custom.strip().split())
            else:
                self.difficulty_var.set("Medium")
        self.reset_test()

    def pick_new_passage(self) -> str:
        pool_name = self.difficulty_var.get()
        if pool_name == "Custom" and self.custom_text:
            return self.custom_text
        pool = TEXT_POOLS.get(pool_name, TEXT_POOLS["Medium"])
        choices = [t for t in pool if t != self.target_text] or pool
        return random.choice(choices)

    def reset_test(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

        self.target_text = self.pick_new_passage()
        self.typed_chars = []
        self.start_time = None
        self.test_active = False
        self.test_finished = False

        self.completed_chars_offset = 0
        self.completed_correct_offset = 0
        self.total_keystrokes = 0
        self.correct_keystrokes = 0
        self.missed_keys.clear()
        self.peak_wpm = 0

        best_wpm = self.high_scores.get(self.get_mode_key(), {}).get("wpm", 0)
        self.stat_labels["net_wpm"].config(text="0")
        self.stat_labels["raw_wpm"].config(text="0")
        self.stat_labels["accuracy"].config(text="100.0%")
        self.stat_labels["best"].config(text=f"{best_wpm} WPM")

        dur = self.duration_var.get()
        self.stat_labels["timer"].config(text="0.0s" if dur == "Passage" else dur)
        self.analytics_label.config(
            text="Ready! Start typing to launch timer. [BackSpace] fixes errors, [Esc] resets.",
            fg="#bac2de",
        )

        self.render_text()
        self.root.focus_set()

    def render_text(self):
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", self.target_text)

        typed_len = len(self.typed_chars)
        for i, target_char in enumerate(self.target_text):
            pos_start = f"1.0 + {i} chars"
            pos_end = f"1.0 + {i + 1} chars"
            if i < typed_len:
                tag = "correct" if self.typed_chars[i] == target_char else "wrong"
                self.text_box.tag_add(tag, pos_start, pos_end)
            elif i == typed_len:
                self.text_box.tag_add("cursor", pos_start, pos_end)
            else:
                self.text_box.tag_add("untyped", pos_start, pos_end)

        self.text_box.config(state="disabled")

    def calculate_stats(self):
        if not self.start_time:
            return 0, 0, 100.0, 0.0

        elapsed = max(0.05, time.time() - self.start_time)
        minutes = elapsed / 60.0

        current_correct = sum(
            1 for i, c in enumerate(self.typed_chars) if c == self.target_text[i]
        )
        total_chars = self.completed_chars_offset + len(self.typed_chars)
        total_correct = self.completed_correct_offset + current_correct

        raw_wpm = round((total_chars / 5.0) / minutes)
        net_wpm = round((total_correct / 5.0) / minutes)
        accuracy = (
            round((self.correct_keystrokes / self.total_keystrokes) * 100, 1)
            if self.total_keystrokes > 0
            else 100.0
        )

        if elapsed >= 1.5 and net_wpm > self.peak_wpm:
            self.peak_wpm = net_wpm

        return net_wpm, raw_wpm, accuracy, elapsed

    def update_timer(self):
        if not self.test_active:
            return

        net_wpm, raw_wpm, accuracy, elapsed = self.calculate_stats()
        self.stat_labels["net_wpm"].config(text=str(net_wpm))
        self.stat_labels["raw_wpm"].config(text=str(raw_wpm))
        self.stat_labels["accuracy"].config(text=f"{accuracy}%")

        dur = self.duration_var.get()
        if dur == "Passage":
            self.stat_labels["timer"].config(text=f"{elapsed:.1f}s")
        else:
            limit = int(dur.replace("s", ""))
            remaining = max(0.0, limit - elapsed)
            self.stat_labels["timer"].config(text=f"{remaining:.1f}s")
            if remaining <= 0:
                self.finish_test()
                return

        self.timer_job = self.root.after(100, self.update_timer)

    def on_key_press(self, event: tk.Event):
        if event.keysym == "Escape":
            self.reset_test()
            return

        if self.test_finished:
            return

        if event.keysym == "BackSpace":
            if self.typed_chars:
                removed = self.typed_chars.pop()
                if self.total_keystrokes > 0:
                    self.total_keystrokes -= 1
                if removed == self.target_text[len(self.typed_chars)]:
                    self.correct_keystrokes = max(0, self.correct_keystrokes - 1)
                self.render_text()
            return

        # Ignore modifier keys, navigation keys, and non-printable characters
        if not event.char or len(event.char) != 1 or not event.char.isprintable():
            return

        if not self.test_active:
            self.test_active = True
            self.start_time = time.time()
            self.update_timer()

        typed_len = len(self.typed_chars)
        if typed_len >= len(self.target_text):
            return

        expected_char = self.target_text[typed_len]
        self.total_keystrokes += 1

        if event.char == expected_char:
            self.correct_keystrokes += 1
        else:
            label = "SPACE" if expected_char == " " else expected_char
            self.missed_keys[label] += 1

        self.typed_chars.append(event.char)
        self.render_text()

        # Check if the current passage is finished
        if len(self.typed_chars) == len(self.target_text):
            if self.duration_var.get() == "Passage":
                self.finish_test()
            else:
                # Timed Sprint Mode: bank current passage stats and load next passage
                self.completed_chars_offset += len(self.typed_chars)
                self.completed_correct_offset += sum(
                    1 for i, c in enumerate(self.typed_chars) if c == self.target_text[i]
                )
                self.target_text = self.pick_new_passage()
                self.typed_chars = []
                self.render_text()

    def finish_test(self):
        self.test_active = False
        self.test_finished = True
        if self.timer_job:
            self.root.after_cancel(self.timer_job)

        net_wpm, raw_wpm, accuracy, elapsed = self.calculate_stats()
        cpm = round(net_wpm * 5)
        is_record = self.save_high_score(self.get_mode_key(), net_wpm, accuracy)

        best_wpm = self.high_scores.get(self.get_mode_key(), {}).get("wpm", net_wpm)
        self.stat_labels["best"].config(text=f"{best_wpm} WPM")

        if self.missed_keys:
            top_misses = ", ".join(
                f"'{k}' ({v}x)" for k, v in self.missed_keys.most_common(5)
            )
            miss_summary = f"Problem Keys: {top_misses}"
        else:
            miss_summary = "Flawless run! Zero mistyped characters."

        banner = "🏆 NEW RECORD! " if is_record else "Test Complete! "
        self.analytics_label.config(
            text=(
                f"{banner}Net: {net_wpm} WPM ({cpm} CPM) | Peak: {self.peak_wpm} WPM | "
                f"{miss_summary} | Press [Esc] to play again."
            ),
            fg="#a6e3a1" if is_record else "#f9e2af",
        )


def run_cli_app():
    """Fallback terminal interface for headless environments without a display."""
    leaderboard_path = LEADERBOARD_FILE

    def load_history():
        try:
            with open(leaderboard_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}

    def save_history(history):
        try:
            with open(leaderboard_path, "w", encoding="utf-8") as handle:
                json.dump(history, handle, indent=2)
        except OSError:
            print("Unable to save leaderboard.")

    def calculate_results(start_time, end_time, text, user_input):
        elapsed = max(end_time - start_time, 0.05)
        minutes = elapsed / 60.0
        correct_chars = sum(1 for expected, actual in zip(text, user_input) if expected == actual)
        total_chars = max(len(user_input), 1)
        raw_wpm = (len(user_input) / 5.0) / minutes
        net_wpm = (correct_chars / 5.0) / minutes
        accuracy = (correct_chars / total_chars) * 100 if total_chars else 100.0
        return {
            "elapsed": round(elapsed, 2),
            "raw_wpm": round(raw_wpm, 2),
            "net_wpm": round(net_wpm, 2),
            "accuracy": round(accuracy, 2),
        }

    def choose_text(mode):
        pool = TEXT_POOLS.get(mode, TEXT_POOLS["Medium"])
        return random.choice(pool)

    def record_result(mode, metrics):
        history = load_history()
        previous = history.get(mode, {})
        best = previous.get("wpm", 0)
        if metrics["net_wpm"] > best:
            history[mode] = {
                "wpm": metrics["net_wpm"],
                "accuracy": metrics["accuracy"],
                "elapsed": metrics["elapsed"],
            }
            save_history(history)

    while True:
        print("\n=== TYPING SPEED TEST (CLI MODE) ===")
        print("1. Easy")
        print("2. Medium")
        print("3. Hard")
        print("4. Python Code")
        print("5. Show Best Scores")
        print("6. Exit")

        try:
            choice = input("Choose an option (1-6): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nProgram closed.")
            return

        if choice == "1":
            mode = "Easy"
            duration = None
        elif choice == "2":
            mode = "Medium"
            duration = None
        elif choice == "3":
            mode = "Hard (Symbols & Numbers)"
            duration = None
        elif choice == "4":
            mode = "Python Code"
            duration = None
        elif choice == "5":
            scores = load_history()
            if not scores:
                print("No saved scores yet.")
            else:
                print("\nBest scores:")
                for key, value in sorted(scores.items()):
                    print(f"  {key}: {value['wpm']} WPM | {value['accuracy']}% accuracy")
            continue
        elif choice == "6":
            print("Goodbye!")
            return
        else:
            print("Invalid option. Please choose 1-6.")
            continue

        phrase = choose_text(mode)
        print(f"\nMode: {mode}")
        print("Type this exactly:")
        print(phrase)
        print("Press Enter when ready...")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print("\nTyping cancelled.")
            return

        start_time = time.perf_counter()
        try:
            typed = input(">> ")
        except (EOFError, KeyboardInterrupt):
            print("\nTyping cancelled.")
            return
        end_time = time.perf_counter()

        metrics = calculate_results(start_time, end_time, phrase, typed)
        print(f"\nTime: {metrics['elapsed']}s")
        print(f"Raw WPM: {metrics['raw_wpm']}")
        print(f"Net WPM: {metrics['net_wpm']}")
        print(f"Accuracy: {metrics['accuracy']}%")
        record_result(mode, metrics)


if __name__ == "__main__":
    if os.name == "nt" or os.environ.get("DISPLAY"):
        try:
            app_root = tk.Tk()
            app = TypingSpeedApp(app_root)
            app_root.mainloop()
        except tk.TclError:
            run_cli_app()
    else:
        run_cli_app()
