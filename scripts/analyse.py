#!/usr/bin/env python3
"""Turn data/slim.jsonl into data/model.json: roots, the words built from them, and word families.

Vocabulary
- root:   a Greek or Latin building block: a prefix (tele-, trans-), a suffix or combining form
          (-graph, -logy, -cide) or a short Latin/Greek stem that English uses (port, duct, vision).
          Spelling variants (-gen, -genic, geno-, -genesis) are grouped as forms of one root.
- word:   any English word containing at least one root (generate, hydrogen, telephone).
- family: obvious derivations folded under their word
          ("generation", "generator" under "generate"; "photographer" under "photograph").

How a word gets its roots
1. Wiktionary breakdown ("tele- + -phone"), followed recursively through English words.
2. Otherwise, for Latin/Greek borrowings: the word is matched against known roots
   (optional prefixes + a stem), and the match must be confirmed by the word's etymology:
   generate ← Latin generō contains "gen"; agenda ← Latin agō does not.
"""
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from wordfreq import zipf_frequency

import roots_list

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

MERGE_TAILS = ("esis", "etic", "ous", "ic", "ia", "y", "ist", "ism", "ize", "ate", "ation", "ator",
               "ive", "al", "ity", "er", "or", "ant", "ent", "ure", "ion", "us", "um", "ics", "ical", "e")
# Three-letter stems are only matched inside words when they are well-known Latin/Greek roots;
# otherwise "ter" would claim terror and "the" thesaurus.
SHORT_STEMS = set("""
gen fer duc mit mis pon pos vid vis cap cep cip fac fec fic jac leg lec loc man mov mot nat pel
rog rup sec sed sid ten tin tor ven ver vit viv voc aud cad cid cis cur dic don fid fin flu hab
jud jur lab lat lev lib lit loq luc mar mat med mem min mon mor mut neg nom nov opt pac par pat
pet ple pop pot pug put rad reg rid rot sal san sci sen sol son sta sum tac tim tox tri uni urb
vac vad val vol vor log pod ped bio geo neo hom iso pan syn the dem dyn erg gam gon gyn hem
hyd kin lex lys mer mon morph nym pha phi pod pyr the tom top typ xen zoo""".split()) - {"the"}
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
        if s.endswith(end) and len(s) - len(end) >= 4:
            s = s[: -len(end)]
            break
    if len(s) > 3 and s.endswith("o"):    # combining vowel: photo- → phot, geno- → gen
        s = s[:-1]
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

    # ---- 1. the root inventory
    part_count = defaultdict(int)
    for recs in entries.values():
        for r in recs:
            for p in r["parts"] or []:
                part_count[p] += 1
    forms = {}                            # form as written ("tele-", "-graph", "port") -> origin
    for p, n in part_count.items():
        bare = p.strip("-").lower()
        if not bare.isalpha() or bare != strip_marks(bare):
            continue
        o = part_origin(p)
        if o is None:
            continue
        if p.endswith("-") and not p.startswith("-"):
            if bare not in DERIV_PREFIXES and len(bare) >= 2:
                forms[p] = o
        elif p.startswith("-") and not p.endswith("-"):
            if bare not in DERIV_SUFFIXES and (len(bare) >= 4 or bare in SHORT_OK):
                forms[p] = o
        elif "-" not in p and 4 <= len(bare) <= 6 and n >= 2:
            recs = entries.get(p, [])
            classical_rec = any(origin(r["src"], r["ety"]) and not r["parts"] for r in recs)
            if classical_rec:
                forms[p] = o                    # free Latin/Greek stem used as a building block

    # group spellings into roots
    keys = defaultdict(list)
    for f in forms:
        keys[root_key(f)].append(f)
    alias = {}
    for k in sorted(keys, key=len):
        if k.startswith("o") and k[1:] in keys:
            alias[k] = k[1:]                    # -ology → -logy
            continue
        for tail in MERGE_TAILS:                # -genesis, -genous → -gen; -grapher → -graph
            if k.endswith(tail) and len(k) - len(tail) >= 3 and k[: -len(tail)] in keys:
                alias[k] = alias.get(k[: -len(tail)], k[: -len(tail)])
                break
    canon = lambda f: alias.get(root_key(f), root_key(f))

    # well-known Latin/Greek stems from roots_list.py (dict, ject, struct…)
    curated_meaning = {}
    for cr in roots_list.load():
        sps = [sp for sp in cr["spellings"] if len(sp) >= 3]
        if not sps:
            continue
        k0 = canon(sps[0])
        for sp in sps:
            forms.setdefault(sp, cr["origin"])
            if root_key(sp) != k0 and root_key(sp) not in alias:
                alias[root_key(sp)] = k0
            if len(sp) == 3:
                SHORT_STEMS.add(sp)
        curated_meaning[k0] = cr["meaning"]
    for head, members in roots_list.PREFIX_FAMILIES.items():
        for m_ in members.split():
            if m_ + "-" in forms:
                alias[root_key(m_ + "-")] = canon(head + "-")
    stems = defaultdict(set)                    # bare spelling -> forms
    for f in forms:
        stems[f.strip("-").lower()].add(f)
    prefixes = {f.strip("-") for f in forms if f.endswith("-") and not f.startswith("-")}
    end_forms = sorted({f.strip("-") for f in forms if f.startswith("-")}, key=len, reverse=True)
    print(len(forms), "root spellings in", len({canon(f) for f in forms}), "roots")

    # ---- 2. etymology check for matched stems
    def sources(word):
        """Latin/Greek source words in the word's etymology, plain lowercase letters."""
        out = set()
        for r in entries.get(word, []):
            for lang, sw in r["src"]:
                if lang in LATIN:
                    out.update(strip_marks(sw).lower().replace("-", " ").split())
            ety = r["ety"]
            for m in re.finditer(r"(?:Latin|Greek)\s+([^\s,()“”]+)", ety):
                out.add(strip_marks(m.group(1)).lower())
            for m in re.finditer(r"\(([^)“”,]+?)[,)]", ety):     # Greek transliterations: (génos)
                t = strip_marks(m.group(1)).lower().strip()
                if t.isalpha():
                    out.add(t)
        return {t for t in out if t.isalpha()}

    variants = defaultdict(set)
    for f in forms:
        variants[canon(f)].add(f.strip("-").lower())

    def confirmed(word, pre, stem, later=False):
        """Does the etymology show this root? Any spelling of the root counts:
        contain ← Latin contineō (con + tin, a spelling of ten/tain)."""
        norm = lambda x: x.replace("j", "i").replace("v", "u")   # Latin iectum, uisus
        srcs = {norm(t) for t in sources(word)}
        k = canon(next(iter(sorted(stems[stem])))) if stem in stems else None
        for v in {stem} | variants.get(k, set()):
            s4 = norm(v[:3] if later else v[:4])      # later pieces: vision ← Latin vīsus
            if len(s4) < 3:
                continue
            for t in srcs:
                if t.startswith(s4) or t.startswith(norm(pre) + s4):
                    return True
                if pre and 0 < t.find(s4) <= 5:          # predict ← praedīcō
                    return True
        return False

    def stem_match(word, need_confirm=True):
        """generate → gen + -erate; transport → trans- + port; television → tele + vision."""
        w = word.lower()
        best_m = [None]

        def consider(pieces, pos):
            covered = sum(len(t) for t, _ in pieces)
            score = (covered, -len(pieces))
            if best_m[0] is None or score > best_m[0][0]:
                best_m[0] = (score, list(pieces), w[pos:])

        def walk(pos, pieces):
            n_stems = sum(1 for _, kind in pieces if kind == "s")
            if n_stems < 3:
                for L in range(min(9, len(w) - pos), 2, -1):
                    s_ = w[pos:pos + L]
                    if s_ not in stems or (n_stems and L < 4) or (L == 3 and s_ not in SHORT_STEMS):
                        continue
                    if L == len(w) and (pieces or L < 4):
                        continue                         # "vision" itself is fine, "pro" alone isn't
                    pre = "".join(t for t, kind in pieces if kind == "p")
                    if need_confirm and not confirmed(word, pre if not n_stems else "", s_, later=bool(n_stems)):
                        continue
                    nxt = pieces + [(s_, "s")]
                    consider(nxt, pos + L)
                    walk(pos + L, nxt)
                    if pos + L < len(w) and w[pos + L] in "oi":     # linking vowel: tele-o-, bi-o-
                        walk(pos + L + 1, nxt)
                    if L >= 5 and n_stems < 2:                       # manus|script share the s
                        walk(pos + L - 1, pieces + [(s_[:-1], "s")])
            if not n_stems and len(pieces) < 2:
                for L in range(2, min(7, len(w) - pos - 2)):
                    p_ = w[pos:pos + L]
                    if p_ in prefixes:
                        walk(pos + L, pieces + [(p_, "p")])
        walk(0, [])
        if not best_m[0]:
            return None
        _, pieces, rest = best_m[0]
        out = []
        for i_, (t, kind) in enumerate(pieces):
            if kind == "p":
                out.append((t + "-", canon(t + "-")))
            else:
                src_t = t if t in stems else next(x for x in stems if x.startswith(t) and len(x) == len(t) + 1)
                k = canon(next(iter(sorted(stems[src_t]))))
                shorter = [x for x in stems if len(x) >= 3 and t.startswith(x) and x != t
                           and any(canon(f) == k for f in stems[x])] if i_ == len(pieces) - 1 else []
                out.append((min(shorter, key=len) if shorter else t, k))
                if shorter:                          # gene-ro → gen-ero
                    extra = t[len(min(shorter, key=len)):]
                    rest = extra + rest
        if rest:
            end = next((e for e in end_forms if rest.endswith(e) and len(e) >= 3
                        and len(rest) - len(e) <= 2 and e not in DERIV_SUFFIXES), None)
            if end and len(rest) > len(end):
                out.append(("-" + rest[: -len(end)], None))
            if end:
                out.append(("-" + end, canon("-" + end)))
            else:
                out.append(("-" + rest, None))
        if not any(k for _, k in out[1:]) and len(out) == 1:
            return out
        return out

    # ---- 3. words → roots
    memo = {}

    def roots_of(word, depth=0):
        """Return (parts, base): parts is a list of (spelling, root key or None);
        base is set when the word is an obvious derivation of another word."""
        if word in memo:
            return memo[word]
        memo[word] = ([], None)
        rec = best(word, WORD_POS)
        parts, base = [], None
        if rec and rec["parts"] and depth < 6:
            ps = [p for p in rec["parts"] if p not in IGNORE_PARTS]
            content = [p for i, p in enumerate(ps) if not is_deriv_suffix(p) and not is_deriv_prefix(p)
                       and not (i > 0 and p.lower() in DERIV_SUFFIXES)]
            if len(content) == 1 and len(ps) > 1 and "-" not in content[0] and content[0] in entries:
                base = content[0]                     # photographer = photograph + -er
                sub, sub_base = roots_of(base, depth + 1)
                parts, base = sub, (sub_base or base)
            else:
                plain_base = all(not part_origin(c) for c in content if "-" not in c) and \
                    not any(c in forms and c.endswith("-") for c in content)
                for p in ps:
                    if p not in content:
                        parts.append((p, None))
                    elif p in forms and p.startswith("-") and plain_base and \
                            any("-" not in c for c in content):
                        parts.append((p, None))          # hand-some, two-fold: English suffix
                    elif p in forms:
                        parts.append((p, canon(p)))
                    elif "-" not in p and p in entries:
                        sub, _ = roots_of(p, depth + 1)
                        parts += sub if any(k for _, k in sub) else [(p, None)]
                    elif "-" not in p:               # a Latin/Greek word, e.g. generō
                        m = stem_match(strip_marks(p).lower(), need_confirm=False)
                        parts += m if m else [(p, None)]
                    else:
                        parts.append((p, None))
        elif rec and any_origin(entries.get(word, [])):
            m = stem_match(word)
            if m:
                parts = m
        memo[word] = (parts, base)
        return memo[word]

    model_words, families = {}, defaultdict(list)
    for w in entries:
        if not w.isalpha() or not w.islower() or len(w) < 3:
            continue
        if not best(w, WORD_POS):
            continue
        z = zipf_frequency(w, "en")
        if z < 2.0:
            continue
        parts, base = roots_of(w)
        if base:
            families[base].append(w)
            continue
        keyed = [k for _, k in parts if k]
        if not keyed:
            continue
        model_words[w] = {"z": z, "parts": parts, "roots": keyed, "rec": best(w, WORD_POS),
                          "guessed": not best(w, WORD_POS)["parts"]}

    # ---- 4. fold obvious derivations that Wiktionary didn't mark
    #      (generation, generator → generate; photography → photograph)
    def deriv_tail(rest):
        rest = rest.lstrip("-")
        if not rest:
            return True
        for d in sorted(DERIV_SUFFIXES | {"ation", "ational", "ationally", "ator", "ators", "ive", "ively",
                                          "ally", "ically", "y", "ies", "ers"}, key=len, reverse=True):
            if rest.startswith(d) and deriv_tail(rest[len(d):]):
                return True
        return False

    by_seq = defaultdict(list)
    for w, v in model_words.items():
        by_seq[tuple(v["roots"])].append(w)
    for seq, ws in by_seq.items():
        for w in sorted(ws, key=len):
            if "folded" in model_words[w]:
                continue
            stem = w[:-1] if w[-1] in "ey" and len(w) > 5 else w
            if len(stem) < 5:
                continue
            for o in ws:
                if o != w and "folded" not in model_words[o] and o.startswith(stem) and deriv_tail(o[len(stem):]):
                    model_words[o]["folded"] = w
                    families[w].append(o)
    for w, v in list(model_words.items()):
        if "folded" in v:
            families[v["folded"]] += families.pop(w, [])
    model_words = {w: v for w, v in model_words.items() if "folded" not in v}

    # ---- 5. drop "roots" that are really just a word (agenda, acacia): a root must help
    #      build at least two words other than itself
    bound_keys = {canon(f) for f in forms if "-" in f} | set(curated_meaning)
    cw = {}

    def classical_word(w):
        """Is this word itself of Greek/Latin make (by etymology or by its Wiktionary parts)?"""
        if w not in cw:
            recs = entries.get(w, [])
            # the etymology templates name a Latin/Greek source (not just an ancestor deep in
            # the etymology tree), or Wiktionary builds it with a Greek/Latin prefix/suffix
            o = any(l in LATIN or l in GREEK for r in recs for l, _ in r["src"])
            if not o:
                rec = best(w, WORD_POS)
                o = bool(rec and rec["parts"] and any(p in forms and "-" in p for p in rec["parts"]))
            cw[w] = o
        return cw[w]
    # only words that are themselves Greek/Latin-made: keeps basketball, airport, phonebook out
    model_words = {w: v for w, v in model_words.items()
                   if classical_word(w) or (v["guessed"] and len(v["roots"]) >= 2)}   # tele+vision
    for _ in range(3):
        users = defaultdict(set)
        for w, v in model_words.items():
            ks = [k for _, k in v["parts"] if k]
            for p, k in v["parts"]:
                if not k or w == p.strip("-"):
                    continue
                # a free stem (port, vision) only counts where it combines with a prefix or
                # suffix root (import, transport); that keeps out basket-ball, foot-ball
                if not classical_word(w):
                    continue                 # basketball, burdensome, offside don't vouch for a root
                if k in bound_keys or any(o != k and o in bound_keys for o in ks):
                    users[k].add(w)
        total = defaultdict(set)
        for w, v in model_words.items():
            for k in v["roots"]:
                total[k].add(w)
        # a root needs ≥2 Greek/Latin words vouching for it, and they must be a good share of
        # all its words (ball, paper, point mostly build plain English compounds)
        weak = {k for k in total if len(users[k]) < (2 if k in bound_keys else 3)}
        for w, v in model_words.items():
            v["parts"] = [(p, None if k in weak else k) for p, k in v["parts"]]
            v["roots"] = [k for _, k in v["parts"] if k]
        model_words = {w: v for w, v in model_words.items() if v["roots"]}

    # ---- 6. output
    roots = {}
    for w, v in model_words.items():
        for p, k in v["parts"]:
            if not k:
                continue
            r = roots.setdefault(k, {"forms": defaultdict(int), "words": []})
            r["forms"][p] += 1
            if w not in r["words"]:
                r["words"].append(w)

    def gloss_of(form):
        for f in (form, form.strip("-") + "-", "-" + form.strip("-"), form.strip("-")):
            for r in every.get(f, []):
                if r["gloss"]:
                    return r["gloss"][0]
        return ""

    def origin_of(k):
        votes = defaultdict(int)
        for f in keys_forms[k]:
            votes[forms[f]] += 1
        return max(votes, key=votes.get) if votes else None

    keys_forms = defaultdict(list)
    for f in forms:
        keys_forms[canon(f)].append(f)

    out_roots = {}
    for k, r in roots.items():
        fs = sorted(r["forms"], key=lambda f: -r["forms"][f])
        bare = [f.strip("-") for f in fs]
        label = bare[0]
        if re.search(r"[^aeiouy]{2}$", label) and label + "o" in bare:
            label += "o"                         # micr → micro, hydr → hydro
        shortest = min(bare, key=len)
        if len(shortest) >= 3 and label.startswith(shortest) and label != shortest \
                and r["forms"].get(fs[bare.index(shortest)], 0) * 4 >= r["forms"][fs[0]]:
            label = shortest                     # geno → gen
        out_roots[k] = {"forms": fs, "label": label, "origin": origin_of(k),
                        "meaning": curated_meaning.get(k) or gloss_of(fs[0])[:160], "words": r["words"]}

    out_words = {}
    for w, v in model_words.items():
        rec = v["rec"]
        out_words[w] = {
            "z": round(v["z"], 2),
            "parts": [[p, k] for p, k in v["parts"]],
            "roots": v["roots"],
            "gloss": rec["gloss"][:2],
            "pos": rec["pos"],
            "guessed": v["guessed"],
            "family": sorted({f for f in families.get(w, []) if f != w and f not in model_words})[:12],
        }
    json.dump({"roots": out_roots, "words": out_words}, open(DATA / "model.json", "w"), ensure_ascii=False)
    print(len(out_words), "words;", len(out_roots), "roots;",
          sum(len(v["family"]) for v in out_words.values()), "family members →", DATA / "model.json")
    return out_words, out_roots


if __name__ == "__main__":
    W, R = main()
    import random
    random.seed(5)
    for w in random.sample(sorted(W), 25):
        print(w, W[w]["z"], ["%s%s" % (p, "" if k else "·") for p, k in W[w]["parts"]], W[w]["family"][:4])
    for w in ("generate", "gene", "genetic", "general", "hydrogen", "agenda", "portrait", "transport",
              "television", "telephone", "photograph", "independent", "manuscript", "biology"):
        print(w, W.get(w, {}).get("parts"), W.get(w, {}).get("family"))
    for k in ("gen", "port", "graph"):
        if k in R:
            print(k, R[k]["label"], R[k]["forms"][:8], len(R[k]["words"]), R[k]["words"][:25])
    labels = sorted(R[k]["label"] for k in R)
    print(len(labels), labels[:80])
