#!/usr/bin/env python3
"""Word frequency counter — reads text and reports the most common words."""

import re
import sys
from collections import Counter


def count_words(text):
    """Return a dict of word -> count (case-insensitive, punctuation stripped)."""
    words = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?", text.lower())
    return dict(Counter(words))


def top_n(counts, n=10):
    """Return the top N words by frequency as a list of (word, count) tuples."""
    return Counter(counts).most_common(n)


def main():
    """Read from stdin or a filename argument and print the top 10 words."""
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    counts = count_words(text)
    for word, count in top_n(counts):
        print(f"{word}: {count}")


if __name__ == "__main__":
    main()
