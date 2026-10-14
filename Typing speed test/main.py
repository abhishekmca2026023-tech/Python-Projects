import json
import os
import random
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


def display_results(metrics):
    print("\n" + "=" * 40)
    print("              TEST RESULTS")
    print("=" * 40)
    print(f"Time Taken: {metrics['elapsed_seconds']} seconds")
    print(f"Speed:      {metrics['wpm']} WPM")
    print(f"Accuracy:   {metrics['accuracy']}%")
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
    print(f"{'Test #':<8} {'WPM':<10} {'Accuracy':<12} {'Time (s)':<10}")
    print("-" * 50)
    for index, entry in enumerate(history[-10:], start=1):
        print(
            f"{index:<8} {entry.get('wpm', 0):<10} "
            f"{entry.get('accuracy', 0):<12}% "
            f"{entry.get('elapsed_seconds', 0):<10}"
        )
    print("=" * 50)


def play_game():
    print("\n" + "=" * 40)
    print("       STARTING TYPING TEST")
    print("=" * 40)

    target_sentence = random.choice(SENTENCE_POOL)
    print("\nTarget Sentence:")
    print("-" * 40)
    print(f'"{target_sentence}"')
    print("-" * 40)

    input("\nPress Enter when you are ready to start typing...")
    print("Type the sentence above and press Enter:")
    start_time = time.perf_counter()
    user_input = input(">> ")
    end_time = time.perf_counter()

    metrics = calculate_metrics(start_time, end_time, target_sentence, user_input)
    display_results(metrics)
    save_result_to_history(metrics)

def main():
    while True:
        print("\n" + "=" * 40)
        print("       PYTHON TYPING SPEED TEST")
        print("=" * 40)
        print("1. Start New Test")
        print("2. View History")
        print("3. Exit")
        
        choice = input("\nChoose an option (1-3): ").strip()
        
        if choice == "1":
            play_game()
        elif choice == "2":
            display_history()
        elif choice == "3":
            print("\nThank you for using Python Typing Speed Test. Goodbye!")
            break
        else:
            print("\nInvalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()