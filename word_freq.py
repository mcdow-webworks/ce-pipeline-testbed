#!/usr/bin/env python3
"""Word frequency counter — reads text and reports the most common words."""

import re
import sys
from collections import Counter


def count_words(text: str) -> Counter:
    """Return a Counter of word -> count (case-insensitive, punctuation stripped)."""
    words = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?", text.lower())
    return Counter(words)


def top_n(counts: Counter, n: int = 10) -> list[tuple[str, int]]:
    """Return the top N words by frequency as a list of (word, count) tuples."""
    return counts.most_common(n)


def main() -> None:
    """Read from stdin or a filename argument and print the top 10 words."""
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], encoding="utf-8") as f:
                text = f.read()
        except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        text = sys.stdin.read()

    counts = count_words(text)
    for word, count in top_n(counts):
        print(f"{word}: {count}")


if __name__ == "__main__":
    main()
