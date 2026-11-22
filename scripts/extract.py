#!/usr/bin/env python3
"""Stream the kaikki.org English Wiktionary dump and keep only what the site needs.

Input:  data/kaikki-en.jsonl  (≈3.4 GB, from scripts/fetch_data.sh)
Output: data/slim.jsonl       one line per (word, pos) with parts, origin and glosses
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
PART_TEMPLATES = {"af", "affix", "compound", "com", "confix", "con", "prefix", "pre",
                  "suffix", "suf", "surf", "surface analysis"}
SOURCE_TEMPLATES = {"der", "der+", "bor", "bor+", "lbor", "lbor+", "inh", "inh+", "uder", "ubor", "slbor"}


def positional(args, start):
    out, i = [], start
    while str(i) in args:
        v = args[str(i)].strip()
        if v:
            out.append(v)
        i += 1
    return out


def parts_from(t):
    """Return the list of English parts a template describes, or None."""
    name, a = t["name"], t["args"]
    if name == "etymon":
        if a.get("2") == ":af" and a.get("1") == "en":
            return [p.split("<")[0] for p in positional(a, 3)]
        return None
    if name not in PART_TEMPLATES:
        return None
    if name in ("surf", "surface analysis"):
        start = 2
        if a.get("1", "").startswith("+"):
            if a.get("2") != "en":
                return None
            start = 3
        elif a.get("1") != "en":
            return None
        ps = positional(a, start)
    else:
        if a.get("1") != "en":
            return None
        ps = positional(a, 2)
    if name in ("prefix", "pre") and len(ps) >= 2:
        ps = [ps[0].rstrip("-") + "-"] + ps[1:]
    elif name in ("suffix", "suf") and len(ps) >= 2:
        ps = ps[:1] + ["-" + p.lstrip("-") for p in ps[1:]]
    elif name in ("confix", "con"):
        if len(ps) == 2:
            ps = [ps[0].rstrip("-") + "-", "-" + ps[1].lstrip("-")]
        elif len(ps) == 3:
            ps = [ps[0].rstrip("-") + "-", ps[1], "-" + ps[2].lstrip("-")]
    ps = [p.split("<")[0].strip() for p in ps]
    return ps if len(ps) >= 2 else None


def main(src, dst):
    kept = 0
    with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as out:
        for line in f:
            e = json.loads(line)
            if e.get("lang_code") != "en":
                continue
            word, pos = e["word"], e.get("pos")
            if pos in ("name", "phrase", "proverb", "character", "symbol", "punct", "contraction"):
                continue
            if " " in word or any(c.isupper() for c in word):
                continue
            parts = None
            for t in e.get("etymology_templates", []):
                p = parts_from(t)
                if p:
                    parts = p
                    break
            langs = []
            for t in e.get("etymology_templates", []):
                if t["name"] in SOURCE_TEMPLATES or (t["name"] == "etymon" and ":" in t["args"].get("3", "")):
                    a = t["args"]
                    if t["name"] == "etymon":
                        lang, src_word = a["3"].split(":", 1)
                        src_word = src_word.split("<")[0]
                    else:
                        lang, src_word = a.get("2", ""), a.get("3", "")
                    langs.append([lang, src_word])
            glosses = []
            for s in e.get("senses", []):
                if "form-of" in s.get("tags", []) or "alt-of" in s:
                    continue
                for g in s.get("glosses", [])[:1]:
                    glosses.append(g)
                if len(glosses) >= 3:
                    break
            form_of = [f.get("word") for s in e.get("senses", []) for f in s.get("form_of", [])][:1]
            if not glosses and not form_of:
                continue
            rec = {"w": word, "pos": pos, "parts": parts, "src": langs[:8], "gloss": glosses,
                   "ety": (e.get("etymology_text") or "")[:400]}
            if form_of:
                rec["form_of"] = form_of[0]
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            kept += 1
    print(f"kept {kept} entries → {dst}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DATA / "kaikki-en.jsonl",
         sys.argv[2] if len(sys.argv) > 2 else DATA / "slim.jsonl")
