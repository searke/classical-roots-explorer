#!/usr/bin/env bash
# Download the English Wiktionary (kaikki.org's Wiktextract build, ~3.4 GB) and slim it down.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data
if [ ! -f data/kaikki-en.jsonl ]; then
  curl -sSfL -o data/kaikki-en.jsonl \
    https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl
fi
python3 scripts/extract.py data/kaikki-en.jsonl data/slim.jsonl
