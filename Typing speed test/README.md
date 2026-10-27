# Typing Speed Test

A small command-line program for practicing typing speed and accuracy. It includes a standard test, 30- and 60-second sprints, saved results, and a statistics dashboard.

## Run the program

Open a terminal in this folder and run:

```bash
python main.py
```

Choose an option from the menu. Timed sprints need an interactive terminal so the program can read each key as you type.

## How the code is organized

Start reading at `main()`, near the bottom of `main.py`. It displays the menu and calls the function for the selected option.

- `SENTENCE_POOL` contains the passages used for typing tests.
- `play_game()` displays a passage, starts the test, and saves the result.
- `calculate_metrics()` works out elapsed time, words per minute, and accuracy.
- `analyze_mistakes()` counts substitutions, skipped characters, and extra characters.
- `display_history()` shows recent results; `display_dashboard()` summarizes progress and common mistakes.
- `timed_input()` reads individual keys and stops when a sprint's timer expires.

The WPM calculation treats five typed characters as one word. Accuracy compares the typed text with the target text, so both wrong and missing characters count against the score.

## Saved results

Results are stored in `data/history.json`. The file uses JSON, a text format for lists and other structured data. Older results without a mode or mistake breakdown can still be displayed; detailed key analysis builds up as you complete new tests.

To change the practice passages, edit `SENTENCE_POOL` near the top of `main.py`.