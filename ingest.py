#!/usr/bin/env python3
"""
Ingest documents into the local RAG knowledge base.

Usage:
    python ingest.py                     # (re-)index everything under kb_dir (config.json)
    python ingest.py --path ~/papers     # index a specific folder or file
    python ingest.py --reset             # wipe the store and rebuild from kb_dir
    python ingest.py --stats             # show what's currently indexed
    python ingest.py --query "dark energy from structure"   # test a retrieval

Incremental by default: unchanged files are skipped, changed files re-indexed.
Add papers over time by dropping them in kb_dir and re-running with no args.
"""

import argparse
import logging
import sys

import rag

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _print_stats() -> None:
    s = rag.stats()
    print(f"\nKnowledge base: {s['total_chunks']} chunks from {len(s['sources'])} sources\n")
    for src, info in sorted(s["sources"].items()):
        title = info["title"]
        label = f"{src}" + (f"  — “{title}”" if title and title != src.rsplit('.', 1)[0] else "")
        print(f"  {info['chunks']:>5} chunks   {label}")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest documents into the RAG knowledge base")
    ap.add_argument("--path", help="File or folder to ingest (default: kb_dir from config)")
    ap.add_argument("--reset", action="store_true", help="Wipe the store before ingesting")
    ap.add_argument("--stats", action="store_true", help="Show indexed sources and exit")
    ap.add_argument("--query", help="Run a test retrieval and print the top hits")
    args = ap.parse_args()

    if args.stats:
        _print_stats()
        return

    if args.query:
        hits = rag.search(args.query)
        if not hits:
            print("No results (is the knowledge base empty? run ingest first).")
            return
        print(f"\nTop {len(hits)} for: {args.query!r}\n")
        for h in hits:
            page = f" p.{h['page']}" if h["page"] and h["page"] > 0 else ""
            print(f"[{h['rank']}] score={h['score']:.3f}  {h['title']}{page}  ({h['source']})")
            print(f"    {h['text'][:300].strip()}...\n")
        return

    cfg = rag.get_config()
    target = args.path or cfg["kb_dir"]
    print(f"Ingesting: {target}" + ("  (reset)" if args.reset else ""))
    results = rag.ingest_path(args.path, reset=args.reset)

    if not results:
        print(f"\nNo supported documents found. Drop PDFs/txt/md into {cfg['kb_dir']} "
              f"or pass --path.\n")
        sys.exit(0)

    indexed = sum(1 for r in results if r["status"] == "indexed")
    skipped = sum(1 for r in results if r["status"] == "up-to-date")
    chunks = sum(r["chunks"] for r in results)
    for r in results:
        print(f"  {r['status']:>12}  {r['file']}  ({r['chunks']} chunks)")
    print(f"\nDone: {indexed} indexed, {skipped} up-to-date, {chunks} total chunks.\n")


if __name__ == "__main__":
    main()
