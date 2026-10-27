from collections import Counter
from difflib import SequenceMatcher
import json
import math
import os
import random
import select
import statistics
import sys
import time


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
CHARS_PER_WORD = 5

SENTENCE_POOL = [
    "The advancement of artificial intelligence has revolutionized how we interact with technology. From automated natural language processing to complex data analytics, machine learning algorithms continue to shape the modern digital landscape in unprecedented ways.",
    
    "Python is widely regarded as one of the most accessible yet powerful programming languages in the world. Its clean syntax and extensive ecosystem of libraries make it an ideal choice for web development, data science, automation, and software engineering.",
    
    "Consistency and deliberate practice are the true cornerstones of mastery. Whether you are learning to play a musical instrument, writing code, or improving your typing speed, daily dedication compounds over time to produce remarkable results.",
    
    "Clean code always looks like it was written by someone who cares. Writing maintainable software requires attention to detail, proper documentation, and a willingness to refactor your solutions as requirements evolve over time.",
    
    "Open source software relies on global collaboration, transparent code review, and shared knowledge. Developers from diverse backgrounds contribute to projects that power everything from personal computing devices to global enterprise infrastructure.",
    
    "Deep in the heart of the ancient forest, sunlight filters through the dense canopy, casting intricate patterns of shadow and light on the mossy floor. The quiet rustle of leaves in the gentle breeze provides a sense of profound peace.",
    
    "Time management is not just about fitting as many tasks as possible into a single day; it is about prioritizing meaningful work, establishing clear boundaries, and maintaining sharp focus amidst endless modern distractions."
]


def calculate_metrics(start_time, end_time, target_sentence, user_input):
    """Calculate elapsed time, typing speed, and character accuracy."""
    elapsed_seconds = max(0, end_time - start_time)
    elapsed_minutes = max(elapsed_seconds / 60, 0.001)
    wpm = (len(user_input) / CHARS_PER_WORD) / elapsed_minutes

    edit_row = list(range(len(user_input) + 1))
    for target_char in target_sentence:
        next_row = [edit_row[0] + 1]
        for index, typed_char in enumerate(user_input, start=1):
            next_row.append(
                min(
                    next_row[-1] + 1,
                    edit_row[index] + 1,
                    edit_row[index - 1] + (target_char != typed_char),
                )
            )
        edit_row = next_row

    compared_length = max(len(target_sentence), len(user_input))
    accuracy = (
        (compared_length - edit_row[-1]) / compared_length * 100
        if compared_length
        else 0
    )

    return {
        "elapsed_seconds": round(elapsed_seconds, 2),
        "wpm": round(wpm, 2),
        "accuracy": round(max(0, min(100, accuracy)), 2),
    }


def analyze_mistakes(target_text, user_input):
    substitutions = Counter()
    missed = Counter()
    extra = Counter()

    matcher = SequenceMatcher(None, target_text, user_input, autojunk=False)
    for operation, target_start, target_end, input_start, input_end in matcher.get_opcodes():
        if operation == "replace":
            target_chars = target_text[target_start:target_end]
            input_chars = user_input[input_start:input_end]
            paired_length = min(len(target_chars), len(input_chars))
            for index in range(paired_length):
                if target_chars[index] != input_chars[index]:
                    substitutions[(target_chars[index], input_chars[index])] += 1
            missed.update(target_chars[paired_length:])
            extra.update(input_chars[paired_length:])
        elif operation == "delete":
            missed.update(target_text[target_start:target_end])
        elif operation == "insert":
            extra.update(user_input[input_start:input_end])

    return {
        "substitutions": [
            {"expected": expected, "typed": typed, "count": count}
            for (expected, typed), count in substitutions.most_common()
        ],
        "missed": dict(missed),
        "extra": dict(extra),
    }


def _mistake_total(mistakes):
    return (
        sum(item["count"] for item in mistakes.get("substitutions", []))
        + sum(mistakes.get("missed", {}).values())
        + sum(mistakes.get("extra", {}).values())
    )


def display_results(metrics):
    print("\n" + "=" * 40)
    print("              TEST RESULTS")
    print("=" * 40)
    print(f"Mode:       {metrics.get('mode', 'Standard')}")
    print(f"Time Taken: {metrics['elapsed_seconds']} seconds")
    print(f"Speed:      {metrics['wpm']} WPM")
    print(f"Accuracy:   {metrics['accuracy']}%")
    print(f"Mistakes:   {_mistake_total(metrics['mistakes'])}")
    print("=" * 40)


def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as history_file:
            history = json.load(history_file)
        return history if isinstance(history, list) else []
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []


def save_result_to_history(result_data):
    history = load_history()
    history.append(result_data)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as history_file:
            json.dump(history, history_file, indent=4)
    except OSError:
        print("Error: Could not save score to history file.")


def display_history():
    history = load_history()
    if not history:
        print("\nNo history found yet. Play a game to record stats!")
        return

    print("\n" + "=" * 50)
    print("                 PAST SCORES")
    print("=" * 50)
    print(f"{'Test #':<8} {'Mode':<15} {'WPM':<10} {'Accuracy':<12} {'Time (s)':<10}")
    print("-" * 65)
    for index, entry in enumerate(history[-10:], start=1):
        print(
            f"{index:<8} {entry.get('mode', 'Standard'):<15} "
            f"{entry.get('wpm', 0):<10} "
            f"{entry.get('accuracy', 0):<12}% "
            f"{entry.get('elapsed_seconds', 0):<10}"
        )
    print("=" * 65)


def _dashboard_entries(history):
    entries = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        try:
            wpm = float(entry["wpm"])
            accuracy = float(entry["accuracy"])
            elapsed_seconds = float(entry["elapsed_seconds"])
        except (KeyError, TypeError, ValueError):
            continue
        if not all(
            math.isfinite(value) and value >= 0
            for value in (wpm, accuracy, elapsed_seconds)
        ):
            continue
        entries.append({
            "wpm": wpm,
            "accuracy": accuracy,
            "elapsed_seconds": elapsed_seconds,
            "mode": str(entry.get("mode") or "Standard"),
        })
    return entries


def display_dashboard():
    entries = _dashboard_entries(load_history())
    if not entries:
        print("\nNo valid test results yet. Play a game to populate your dashboard!")
        return

    wpms = [entry["wpm"] for entry in entries]
    accuracies = [entry["accuracy"] for entry in entries]
    total_time = sum(entry["elapsed_seconds"] for entry in entries)
    best_entry = max(entries, key=lambda entry: entry["wpm"])
    best_accuracy_entry = max(entries, key=lambda entry: entry["accuracy"])

    print("\n" + "=" * 64)
    print("                    STATISTICS DASHBOARD")
    print("=" * 64)
    print(f"Tests completed:       {len(entries)}")
    print(f"Average speed:         {statistics.mean(wpms):.2f} WPM")
    print(f"Median speed:          {statistics.median(wpms):.2f} WPM")
    print(f"Personal best:         {best_entry['wpm']:.2f} WPM ({best_entry['mode']})")
    print(f"Average accuracy:      {statistics.mean(accuracies):.2f}%")
    print(f"Best accuracy:         {best_accuracy_entry['accuracy']:.2f}% ({best_accuracy_entry['mode']})")
    print(f"Practice time:         {total_time / 60:.1f} minutes")
    consistency = statistics.pstdev(wpms) if len(wpms) > 1 else 0
    print(f"Speed variation:       {consistency:.2f} WPM standard deviation")

    recent = entries[-5:]
    previous = entries[max(0, len(entries) - 10):max(0, len(entries) - 5)]
    if previous:
        difference = statistics.mean(entry["wpm"] for entry in recent) - statistics.mean(
            entry["wpm"] for entry in previous
        )
        direction = "up" if difference > 0 else "down" if difference < 0 else "unchanged"
        print(
            f"Recent momentum:       {direction} {abs(difference):.2f} WPM "
            f"(latest {len(recent)} vs previous {len(previous)} tests)"
        )
    else:
        print("Recent momentum:       Need more tests to compare sessions")

    print("\nMODE BREAKDOWN")
    print(f"{'Mode':<22} {'Tests':>5} {'Avg WPM':>10} {'Avg accuracy':>15}")
    print("-" * 56)
    modes = {}
    for entry in entries:
        modes.setdefault(entry["mode"], []).append(entry)
    for mode, mode_entries in modes.items():
        print(
            f"{mode:<22} {len(mode_entries):>5} "
            f"{statistics.mean(entry['wpm'] for entry in mode_entries):>10.2f} "
            f"{statistics.mean(entry['accuracy'] for entry in mode_entries):>14.2f}%"
        )

    print("\nRECENT SPEED (oldest to newest)")
    graph_entries = entries[-10:]
    maximum_wpm = max(entry["wpm"] for entry in graph_entries)
    for index, entry in enumerate(graph_entries, start=1):
        bar_length = max(1, round(entry["wpm"] / maximum_wpm * 20)) if maximum_wpm else 1
        print(f"{index:>2}. {entry['mode']:<22} {entry['wpm']:>6.2f} |{'#' * bar_length}")

    substitutions = Counter()
    weak_keys = Counter()
    missed_keys = Counter()
    extra_keys = Counter()
    for entry in load_history():
        mistakes = entry.get("mistakes") if isinstance(entry, dict) else None
        if not isinstance(mistakes, dict):
            continue
        for item in mistakes.get("substitutions", []):
            if not isinstance(item, dict):
                continue
            expected = item.get("expected")
            typed = item.get("typed")
            count = item.get("count")
            if not isinstance(expected, str) or len(expected) != 1 or not isinstance(typed, str) or len(typed) != 1:
                continue
            if not isinstance(count, int) or count < 1:
                continue
            substitutions[(expected, typed)] += count
            weak_keys[expected] += count
        for key, count in mistakes.get("missed", {}).items():
            if isinstance(key, str) and len(key) == 1 and isinstance(count, int) and count > 0:
                missed_keys[key] += count
                weak_keys[key] += count
        for key, count in mistakes.get("extra", {}).items():
            if isinstance(key, str) and len(key) == 1 and isinstance(count, int) and count > 0:
                extra_keys[key] += count

    print("\nKEY & MISTAKE ANALYSIS")
    if not weak_keys and not extra_keys:
        print("No mistake details in history yet. New tests will build this analysis.")
    else:
        print("Most error-prone expected keys:")
        for key, count in weak_keys.most_common(5):
            print(f"  {key!r}: {count} errors")
        if substitutions:
            print("Common substitutions:")
            for (expected, typed), count in substitutions.most_common(5):
                print(f"  {expected!r} typed as {typed!r}: {count}")
        if missed_keys:
            print("Often skipped keys:")
            for key, count in missed_keys.most_common(5):
                print(f"  {key!r}: {count} times")
        if extra_keys:
            print("Often added keys:")
            for key, count in extra_keys.most_common(5):
                print(f"  {key!r}: {count} times")
    print("=" * 64)


def _record_typed_key(key, typed_chars):
    if key in ("\r", "\n"):
        return
    if key in ("\b", "\x7f"):
        if typed_chars:
            typed_chars.pop()
            print("\b \b", end="", flush=True)
    elif key == "\x03":
        raise KeyboardInterrupt
    elif key.isprintable():
        typed_chars.append(key)
        print(key, end="", flush=True)


def timed_input(duration_seconds):
    if not sys.stdin.isatty():
        raise RuntimeError("Timed sprints require an interactive terminal.")

    print(f"Type the passage below. The {duration_seconds}-second sprint ends automatically.")
    print("Start typing:")
    start_time = time.perf_counter()
    deadline = start_time + duration_seconds
    typed_chars = []

    if os.name == "nt":
        import msvcrt

        while (remaining := deadline - time.perf_counter()) > 0:
            if not msvcrt.kbhit():
                time.sleep(min(0.01, remaining))
                continue
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                msvcrt.getwch()
                continue
            _record_typed_key(key, typed_chars)
    else:
        import codecs
        import termios
        import tty

        file_descriptor = sys.stdin.fileno()
        terminal_settings = termios.tcgetattr(file_descriptor)
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        try:
            tty.setcbreak(file_descriptor)
            while (remaining := deadline - time.perf_counter()) > 0:
                readable, _, _ = select.select([file_descriptor], [], [], remaining)
                if not readable:
                    break
                key = decoder.decode(os.read(file_descriptor, 1))
                if key:
                    _record_typed_key(key, typed_chars)
        finally:
            termios.tcsetattr(file_descriptor, termios.TCSADRAIN, terminal_settings)

    print()
    return "".join(typed_chars), start_time, time.perf_counter()


def play_game(sprint_duration=None):
    print("\n" + "=" * 40)
    mode = f"{sprint_duration}-second Sprint" if sprint_duration else "Standard"
    print(f"       STARTING {mode.upper()}")
    print("=" * 40)

    if sprint_duration:
        target_parts = []
        target_length = 0
        while target_length < 700:
            sentence = random.choice(SENTENCE_POOL)
            target_parts.append(sentence)
            target_length += len(sentence) + 1
        target_sentence = " ".join(target_parts)
    else:
        target_sentence = random.choice(SENTENCE_POOL)

    print("\nTarget Passage:" if sprint_duration else "\nTarget Sentence:")
    print("-" * 40)
    print(f'"{target_sentence}"')
    print("-" * 40)

    input("\nPress Enter when you are ready...")
    if sprint_duration:
        try:
            user_input, start_time, end_time = timed_input(sprint_duration)
        except RuntimeError as error:
            print(f"\n{error}")
            return
        accuracy_target = target_sentence[:len(user_input)]
    else:
        print("Type the sentence above and press Enter:")
        start_time = time.perf_counter()
        user_input = input(">> ")
        end_time = time.perf_counter()
        accuracy_target = target_sentence

    metrics = calculate_metrics(start_time, end_time, accuracy_target, user_input)
    metrics["mode"] = mode
    metrics["mistakes"] = analyze_mistakes(accuracy_target, user_input)
    display_results(metrics)
    save_result_to_history(metrics)

def main():
    while True:
        print("\n" + "=" * 40)
        print("       PYTHON TYPING SPEED TEST")
        print("=" * 40)
        print("1. Standard Test")
        print("2. 30-second Sprint")
        print("3. 60-second Sprint")
        print("4. View History")
        print("5. Statistics Dashboard")
        print("6. Exit")
        
        choice = input("\nChoose an option (1-6): ").strip()
        
        if choice == "1":
            play_game()
        elif choice == "2":
            play_game(sprint_duration=30)
        elif choice == "3":
            play_game(sprint_duration=60)
        elif choice == "4":
            display_history()
        elif choice == "5":
            display_dashboard()
        elif choice == "6":
            print("\nThank you for using Python Typing Speed Test. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please enter a number from 1 to 6.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTyping test cancelled. Goodbye!")