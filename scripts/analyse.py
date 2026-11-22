#!/usr/bin/env python3
"""Turn data/slim.jsonl into data/model.json: roots, root words and word families.

Vocabulary
- part:      one piece of a Wiktionary breakdown ("tele-", "-phone", "photograph", "-er")
- root:      a Greek or Latin piece we don't break down further ("tele", "phone", "graph", "vision").
             Spelling variants ("-graph", "grapho-", "-graphy") are grouped as forms of one root.
- root word: a word built from at least two roots ("telephone", "photograph", "independent").
- family:    obvious derivations folded under their root word
             ("photographer", "photographic", "photography" under "photograph").
"""
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from wordfreq import zipf_frequency

DATA = Path(__file__).resolve().parent.parent / "data"

LATIN = {"la", "la-lat", "la-med", "la-new", "la-ecc", "la-vul", "la-late", "la-cla", "la-ren",
         "LL.", "ML.", "NL.", "VL.", "itc-ola"}
GREEK = {"grc", "grc-koi", "grc-att", "grc-ion", "grc-dor", "gkm", "grc-bib", "grc-epi"}

# Endings and prefixes that only make "obvious derivations": they don't count as roots,
# and a word that is just <word> + one of these joins that word's family.
DERIV_SUFFIXES = set("""
s es ed d ing er ers est ly ness ful less ish like ship hood dom y ie ey
al ial ual ical ically ally ic ics ity ty ities ism ist ite ize ise ization isation izer
ation ion tion sion ition ate ated ative ive ivity ivism ous ious eous uous ousness
ary ory ery ry ent ant ence ance ency ancy ment able ible ability ibility ably ibly
ure ian an ean or ee ess et ette let ling ward wards wise fy ify ification ia ial
age ar al ine ile oid oidal ology ologist ological
cy yl ide ane ene ol one ium ose ase th in ite um us on ar ism ia ae ix ex ency acy ure ator ation ization istic istics ality atory esque ative itive ivity ician""".split()) - {"ology", "ologist", "ological", "oid", "oidal"}
DERIV_PREFIXES = {"un", "non", "re", "mis", "over", "under", "out", "self", "pre", "post",
                  "semi", "sub", "super", "anti", "counter", "co"}
DERIV_PREFIXES -= {"sub", "super", "anti", "counter", "co", "pre", "post", "semi"}  # these are kept as roots
IGNORE_PARTS = {"-o-", "-i-", "o", "-o", "o-", "-a-", "-e-", "-s-"}

SHORT_OK = {"gen", "pod", "ped", "oma", "fer", "cid", "lit", "lith", "lyt", "ode", "vor", "cyt", "phyl"}
ROOT_POS = {"prefix", "suffix", "affix", "interfix", "infix", "circumfix", "root"}
WORD_POS = {"noun", "verb", "adj", "adv"}


def strip_marks(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def origin(src, ety=""):
    """'Latin', 'Greek' or None, from the first classical language in the etymology chain."""
    langs = [lang for lang, _ in src]
    if any(l in GREEK for l in langs):
        return "Greek"                   # Latin words borrowed from Greek count as Greek
    if any(l in LATIN for l in langs):
        return "Latin"
    g, l = ety.find("Ancient Greek"), ety.find("Latin")
    if g >= 0 and (l < 0 or g < l):
        return "Greek"
    if l >= 0:
        return "Latin"
    return None


def any_origin(recs):
    for r in recs:
        o = origin(r["src"], r["ety"])
        if o:
            return o
    return None


def root_key(part):
    """Group spelling variants: -graph, grapho-, -graphy, graph → graph."""
    s = strip_marks(part.lower()).strip("-")
    for end in ("ically", "ical", "ists", "ist", "ics", "ic", "ia", "y"):
        if s.endswith(end) and len(s) - len(end) >= 3:
            s = s[: -len(end)]
            break
    s = re.sub(r"[oaie]+$", "", s) if len(s) > 3 else s
    return s


def main():
    entries = defaultdict(list)          # word -> records (real entries)
    every = defaultdict(list)            # word -> all records, incl. "alternative form of"
    for line in open(DATA / "slim.jsonl", encoding="utf-8"):
        r = json.loads(line)
        every[r["w"]].append(r)
        if "form_of" not in r:
            entries[r["w"]].append(r)

    def best(word, pos_set=None):
        recs = entries.get(word, [])
        recs = [r for r in recs if not pos_set or r["pos"] in pos_set]
        with_parts = [r for r in recs if r["parts"]]
        return (with_parts or recs or [None])[0]

    # ---- classify parts
    def is_deriv_suffix(p):
        return p.startswith("-") and p.strip("-").lower() in DERIV_SUFFIXES

    def is_deriv_prefix(p):
        return p.endswith("-") and p.strip("-").lower() in DERIV_PREFIXES

    def part_origin(p):
        bound = p.startswith("-") or p.endswith("-")
        o = any_origin(every.get(p, []))
        if o is None and not bound:
            for alt in (p + "-", "-" + p):
                o = any_origin(every.get(alt, []))
                if o:
                    break
        if o and bound and len(p.strip("-")) <= 3 and p.startswith("-") and p.strip("-") not in SHORT_OK:
            return None                  # short endings like -ic, -yl are grammar, not roots
        return o

    # ---- inventory of known pieces, used to split Latin/Greek borrowings that
    #      Wiktionary doesn't break down (transport → trans + port)
    part_count = defaultdict(int)
    for recs in entries.values():
        for r in recs:
            for p in r["parts"] or []:
                part_count[p] += 1
    prefixes, suffixes, free = set(), set(), set()
    for p, n in part_count.items():
        bare = p.strip("-").lower()
        if not bare.isalpha() or n < 2 or len(bare) < 2:
            continue
        if part_origin(p) is None:
            continue
        if p.endswith("-") and not p.startswith("-"):
            if bare not in DERIV_PREFIXES:
                prefixes.add(bare)
        elif p.startswith("-") and not p.endswith("-"):
            if bare not in DERIV_SUFFIXES and len(bare) >= 3:
                suffixes.add(bare)
        elif "-" not in p and len(bare) >= 4:
            free.add(bare)
    deriv_end = {d for d in DERIV_SUFFIXES if len(d) >= 1}

    def segment(word):
        n = len(word)
        best_seg = {0: (0, [])}
        # states: position -> (cost, tokens); tokens are (text, kind)
        for i in range(n):
            if i not in best_seg:
                continue
            cost, toks = best_seg[i]
            in_suffix = toks and toks[-1][1] == "d"
            for j in range(i + 2, n + 1):
                piece = word[i:j]
                if i == 0 and j == n:
                    continue                 # the whole word isn't a split
                cands = []
                only_prefixes = all(k == "p" for _, k in toks)
                if not in_suffix:
                    if piece in prefixes and j < n and only_prefixes:
                        cands.append("p")
                    if piece in free and len(piece) >= 4:
                        cands.append("f")
                    if piece in suffixes and toks:
                        cands.append("s")
                if piece in deriv_end and i > 0 and toks:
                    cands.append("d")
                for kind in cands:
                    nt = toks + [(piece, kind)]
                    c = cost + 1
                    for k in [j] + ([j + 1] if j < n and word[j] in "oi" and kind in "pf" else []):
                        if k not in best_seg or best_seg[k][0] > c:
                            best_seg[k] = (c, nt)
        if n not in best_seg:
            return None
        toks = best_seg[n][1]
        roots = [t for t in toks if t[1] != "d"]
        if len(roots) < 2 or not any(k in "ps" for _, k in roots):
            return None
        fmt = {"p": lambda t: t + "-", "s": lambda t: "-" + t, "f": lambda t: t, "d": lambda t: "-" + t}
        return [fmt[k](t) for t, k in toks]

    n_seg = 0
    for w, recs in entries.items():
        if not w.isalpha() or not w.islower() or len(w) < 6:
            continue
        main = [r for r in recs if r["pos"] in WORD_POS]
        if not main or any(r["parts"] for r in main) or not any_origin(main):
            continue
        if zipf_frequency(w, "en") < 2.0:
            continue
        seg = segment(w)
        if seg:
            main[0]["parts"] = seg
            main[0]["guessed"] = True
            n_seg += 1
    print("split", n_seg, "unanalysed Latin/Greek words using known pieces")
    for t in ():
        print("SEG", t, segment(t), "tele" in prefixes, "vision" in free, "manu" in prefixes, "script" in free, part_count.get("vision"), part_count.get("script"), any_origin(entries[t]), zipf_frequency(t, "en"))

    # ---- expand a word into its roots (recursively through English words)
    memo = {}

    def expand(word, depth=0):
        """Return (roots, base) where roots is a list of (part, origin) and base is the
        family head if this word is an obvious derivation of another word."""
        if word in memo:
            return memo[word]
        memo[word] = ([], None)          # guard against cycles
        rec = best(word, WORD_POS)
        roots, base = [], None
        if rec and rec["parts"] and depth < 6:
            parts = [p for p in rec["parts"] if p not in IGNORE_PARTS]
            content = [p for i, p in enumerate(parts)
                       if not is_deriv_suffix(p) and not is_deriv_prefix(p)
                       and not (i > 0 and p.lower() in DERIV_SUFFIXES)]
            # obvious derivation: one real word plus only derivational affixes
            if len(content) == 1 and len(parts) > 1 and not content[0].endswith("-") \
                    and not content[0].startswith("-") and content[0] in entries:
                base = content[0]
                sub_roots, sub_base = expand(base, depth + 1)
                roots = sub_roots
                base = sub_base or base
            else:
                for p in content:
                    bare = not (p.startswith("-") or p.endswith("-"))
                    if bare and p in entries and best(p, WORD_POS) and best(p, WORD_POS)["parts"]:
                        sub_roots, sub_base = expand(p, depth + 1)
                        if sub_roots:
                            roots += sub_roots
                            continue
                        if sub_base:             # dependent → depend
                            p = sub_base
                    o = part_origin(p)
                    roots.append((p, o))
        memo[word] = (roots, base)
        return memo[word]

    words = {}
    for w in entries:
        if not w.isalpha() or not w.islower() or len(w) < 4:
            continue
        rec = best(w, WORD_POS)
        if not rec or not rec["parts"]:
            continue
        roots, base = expand(w)
        classical = [(p, o) for p, o in roots if o]
        words[w] = {"roots": roots, "base": base, "classical": classical, "rec": rec}

    # ---- keep words with ≥2 classical roots that people actually use
    model_words = {}
    families = defaultdict(list)
    for w, v in words.items():
        z = zipf_frequency(w, "en")
        if v["base"]:
            if z >= 1.5:
                families[v["base"]].append((w, z))
            continue
        if len(v["classical"]) < 2 or z < 1.5:
            continue
        bound = [p for p, _ in v["classical"] if p.startswith("-") or p.endswith("-")]
        free_ok = [p for p, _ in v["classical"] if p not in bound and len(p) >= 4]
        if not bound or len(bound) + len(free_ok) < 2:
            continue                     # pay+wall, cross+bar: plain compounds, not classical
        model_words[w] = {"z": z, "roots": v["classical"], "all": v["roots"], "rec": v["rec"]}

    # ---- fold words built from the same roots in the same order into the most common one
    #      (photography, photographic → photograph; democrat, democratic → democracy)
    def keyseq(w):
        return tuple(root_key(p) for p, _ in model_words[w]["roots"])

    by_seq = defaultdict(list)
    for w in model_words:
        by_seq[keyseq(w)].append(w)
    for seq, ws in by_seq.items():
        if len(ws) < 2:
            continue
        head = min(ws, key=lambda w: (len(w), -model_words[w]["z"]))
        for w in ws:
            if w != head and (w.startswith(head[:max(4, len(head) - 3)]) or head.startswith(w[:max(4, len(w) - 3)])):
                families[head].append((w, model_words[w]["z"]))
                families[head] += families.pop(w, [])
                model_words[w]["folded"] = head
    model_words = {w: v for w, v in model_words.items() if "folded" not in v}

    # ---- roots: group spelling variants under one key
    keys = defaultdict(lambda: defaultdict(int))
    for w, v in model_words.items():
        for p, o in v["roots"]:
            keys[root_key(p)][p] += 1
    alias = {}
    for k in keys:                       # -ology → -logy, -grapher → -graph
        if k.startswith("o") and k[1:] in keys:
            alias[k] = k[1:]
        elif k.endswith("er") and len(k) >= 6 and k[:-2] in keys:
            alias[k] = k[:-2]
    canon = lambda p: alias.get(root_key(p), root_key(p))

    roots = {}
    for w, v in model_words.items():
        for p, o in v["roots"]:
            k = canon(p)
            r = roots.setdefault(k, {"forms": defaultdict(int), "origin": defaultdict(int), "words": []})
            r["forms"][p] += 1
            r["origin"][o] += 1
            if w not in r["words"]:
                r["words"].append(w)

    def gloss_of(form):
        for f in (form, form.strip("-") + "-", "-" + form.strip("-"), form.strip("-")):
            for r in every.get(f, []):
                if r["gloss"]:
                    return r["gloss"][0]
        return ""

    out_roots = {}
    for k, r in roots.items():
        forms = sorted(r["forms"], key=lambda f: -r["forms"][f])
        out_roots[k] = {
            "forms": forms,
            "label": next((f.strip("-") for f in forms if f.strip("-") == forms[0].strip("-") + "o"),
                          forms[0].strip("-")),
            "origin": max(r["origin"], key=r["origin"].get),
            "meaning": gloss_of(forms[0])[:160],
            "words": r["words"],
        }

    out_words = {}
    for w, v in model_words.items():
        rec = v["rec"]
        fam = sorted({f for f, _ in families.get(w, []) if f != w and f not in model_words})
        out_words[w] = {
            "z": round(v["z"], 2),
            "parts": [[p, canon(p) if any(p == q for q, _ in v["roots"]) else None] for p, _ in v["all"]],
            "roots": [canon(p) for p, _ in v["roots"]],
            "gloss": rec["gloss"][:2],
            "pos": rec["pos"],
            "guessed": bool(rec.get("guessed")),
            "family": fam[:12],
        }
    json.dump({"roots": out_roots, "words": out_words}, open(DATA / "model.json", "w"), ensure_ascii=False)
    print(len(out_words), "root words;", len(out_roots), "roots;",
          sum(len(v["family"]) for v in out_words.values()), "family members →", DATA / "model.json")
    return out_words, out_roots


if __name__ == "__main__":
    W, R = main()
    import random
    random.seed(5)
    for w in random.sample(sorted(W), 30):
        print(w, W[w]["z"], [p for p, _ in W[w]["parts"]], W[w]["family"][:5])
    for w in ("telephone", "photograph", "independent", "democracy", "television", "biology", "transport"):
        print(w, W.get(w, {}).get("parts"), W.get(w, {}).get("family"))
    top = sorted(R, key=lambda k: -len(R[k]["words"]))[:50]
    print([(R[k]["label"], len(R[k]["words"]), R[k]["origin"][0]) for k in top])
