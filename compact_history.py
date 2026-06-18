#!/usr/bin/env python3
"""
Compact conversation history using Claude.

Summarizes old exchanges into a memory block, keeps recent exchanges verbatim.
Run this periodically to keep history.json lean while preserving high-level memory.

Usage:
    python compact_history.py              # keep last 30 exchanges
    python compact_history.py --keep 50   # keep last 50 exchanges
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import anthropic

HISTORY_FILE = Path(__file__).parent / "history.json"
CONFIG_FILE = Path(__file__).parent / "config.json"
SUMMARY_MARKER = "[MEMORY —"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compact assistant conversation history")
    parser.add_argument(
        "--keep", type=int, default=30,
        help="Recent exchanges (user+assistant pairs) to keep verbatim (default: 30)"
    )
    args = parser.parse_args()

    if not HISTORY_FILE.exists():
        print("No history.json found — nothing to compact.")
        return

    with open(HISTORY_FILE) as f:
        messages = json.load(f)

    if not messages:
        print("History is empty — nothing to compact.")
        return

    keep_messages = args.keep * 2  # each exchange = 2 messages

    # Strip any leading summary block from a previous compaction
    existing_summary = ""
    if messages and messages[0]["content"].startswith(SUMMARY_MARKER):
        existing_summary = messages[0]["content"]
        messages = messages[2:]

    if len(messages) <= keep_messages:
        total = len(messages) // 2
        print(f"Only {total} exchanges after any prior summary — fewer than --keep {args.keep}. Nothing to do.")
        return

    to_summarize = messages[:-keep_messages]
    to_keep = messages[-keep_messages:]

    print(f"Exchanges to summarize : {len(to_summarize) // 2}")
    print(f"Exchanges to keep full : {len(to_keep) // 2}")

    # Format exchanges for Claude
    history_text = "\n\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in to_summarize
    )

    prior_block = ""
    if existing_summary:
        prior_block = (
            f"\n\nThere is already a memory block from an earlier compaction:\n"
            f"{existing_summary}\n"
            f"Merge it with the new conversations below into one unified summary.\n"
        )

    prompt = (
        "You are summarizing a conversation history between a user and their personal AI assistant.\n"
        "Produce a compact memory block for future conversations."
        f"{prior_block}\n\n"
        "Capture:\n"
        "- Topics and subjects discussed (specific enough to resume intelligently)\n"
        "- Facts the user shared about themselves, their work, projects, or life\n"
        "- Preferences expressed (tone, explanation depth, workflow habits, etc.)\n"
        "- Decisions made or conclusions reached\n"
        "- Recurring interests or themes\n\n"
        "Be specific — 'discussed astrophysics' is too vague; "
        "'discussed Hawking radiation and the black hole information paradox' is right.\n"
        "Write terse bullet-point memory notes, not prose.\n\n"
        "CONVERSATION HISTORY:\n"
        f"{history_text}"
    )

    config_data = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config_data = json.load(f)
    model = config_data.get("claude_model", "claude-sonnet-4-6")

    print(f"Summarizing with {model}…")

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        print(f"Error calling Claude: {e}")
        print("History was NOT modified.")
        sys.exit(1)

    summary = response.content[0].text.strip()

    # Build compacted history: summary pseudo-exchange + recent verbatim exchanges
    date_str = datetime.now().strftime("%Y-%m-%d")
    n_summarized = len(to_summarize) // 2

    summary_header = f"{SUMMARY_MARKER} {n_summarized} exchanges summarized, as of {date_str}]\n\n"
    compacted = [
        {"role": "user", "content": summary_header + summary},
        {"role": "assistant", "content": "Got it — I have that context from our earlier conversations."},
        *to_keep,
    ]

    # Back up before overwriting
    backup = HISTORY_FILE.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak.json")
    shutil.copy(HISTORY_FILE, backup)
    print(f"Backup saved → {backup.name}")

    with open(HISTORY_FILE, "w") as f:
        json.dump(compacted, f, indent=2)

    original_tokens_est = sum(len(m["content"]) for m in to_summarize) // 4
    summary_tokens_est = len(summary) // 4
    print(f"Done.")
    print(f"  Collapsed {n_summarized} exchanges (~{original_tokens_est:,} tokens) → "
          f"1 summary block (~{summary_tokens_est:,} tokens)")
    print(f"  Kept {len(to_keep) // 2} recent exchanges verbatim")


if __name__ == "__main__":
    main()
