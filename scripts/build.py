#!/usr/bin/env python3
"""Build the Greek & Latin roots explorer as a static site in docs/.

Needs data/model.json (scripts/fetch_data.sh, then scripts/analyse.py).
"""
import html
import json
import shutil
from collections import defaultdict
from pathlib import Path

import graph
import maps

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "docs"

LEVELS = {
    1: ("Everyday", "words almost everyone knows"),
    2: ("Common", "words you meet often in news and books"),
    3: ("Educated", "words a well-read adult knows"),
    4: ("Specialist", "words mostly used in a field: science, medicine, law…"),
    5: ("Rare", "words you will hardly ever meet"),
}
ZIPF_CUTS = [(4.5, 1), (3.8, 2), (3.0, 3), (2.3, 4)]


def level(z):
    for cut, lv in ZIPF_CUTS:
        if z >= cut:
            return lv
    return 5


def esc(s):
    return html.escape(str(s))


CSS = """
:root{--bg:#f7f5f0;--fg:#22201c;--muted:#746d63;--line:#e3ddd2;--accent:#1f5f8b;
--card:#fff;--hl:#dcebf5;--greek:#1f5f8b;--latin:#9b3d2a}
@media (prefers-color-scheme:dark){:root{--bg:#18191b;--fg:#ebe7df;--muted:#a19a8f;
--line:#34363a;--accent:#7fbbe6;--card:#222427;--hl:#21394b;--greek:#7fbbe6;--latin:#f0957d}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:inherit;text-decoration:none}
main{max-width:900px;margin:0 auto;padding:24px 16px 64px}
header.site{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;
border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:24px}
header.site>a{font-weight:600}
nav.top{display:flex;gap:14px;font-size:14px}nav.top a{color:var(--muted);font-weight:500}
nav.top a:hover{color:var(--accent)}
.muted{color:var(--muted)}
h1,h2,h3{line-height:1.25}
.serif{font-family:Georgia,"Iowan Old Style","Palatino Linotype",serif}
.hero{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.big{font-size:84px;line-height:1;font-family:Georgia,"Iowan Old Style",serif;font-style:italic;overflow-wrap:anywhere}
.meta dt{color:var(--muted);font-size:13px}.meta dd{margin:0 0 6px}
.form-tag{display:inline-block;padding:1px 10px;border-radius:99px;background:var(--hl);
margin:2px 4px 2px 0;font-weight:600;font-family:Georgia,serif;font-style:italic}
section.form{margin-top:32px}
section.form h2{font-size:22px;border-bottom:2px solid var(--accent);display:inline-block;padding-bottom:2px;
margin-bottom:8px;font-family:Georgia,serif;font-style:italic}
h3{font-size:14px;color:var(--muted);font-weight:500;margin:16px 0 6px}
ul.words{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px}
ul.words li{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--lc);border-radius:10px;padding:10px 12px}
.w{font-size:22px;font-family:Georgia,serif;font-weight:600}
.parts{font-size:14px;margin:2px 0;display:flex;flex-wrap:wrap;gap:2px 6px;align-items:baseline}
.parts a{color:var(--accent);border-bottom:1px solid transparent;font-style:italic;font-family:Georgia,serif}
.parts a:hover{border-color:var(--accent)}
.parts .self{color:var(--fg);font-weight:700;font-style:italic;font-family:Georgia,serif}
.parts .plain{color:var(--muted);font-style:italic;font-family:Georgia,serif}
.parts .plus{color:var(--muted)}
.guess{font-size:11px;color:var(--muted);border:1px dashed var(--line);border-radius:6px;padding:0 4px}
.g{font-size:13px;color:var(--muted)}
.fam{font-size:12px;color:var(--muted);margin-top:4px}.fam b{font-weight:600}
.badge{float:right;font-size:11px;font-weight:600;color:#fff;background:var(--lc);border-radius:99px;padding:1px 8px;margin-top:6px}
.og{font-size:11px;font-weight:700;border-radius:4px;padding:0 5px;color:#fff}
.og.G{background:var(--greek)}.og.L{background:var(--latin)}
.row{margin-top:28px}.row h2{font-size:28px;margin:0 0 8px;color:var(--accent)}
.kl{display:flex;flex-wrap:wrap;gap:5px}
.kl a{display:inline-flex;flex-direction:column;align-items:center;min-width:56px;padding:4px 8px;border-radius:8px;
background:var(--card);border:1px solid var(--line);border-bottom:4px solid var(--lc)}
.kl a:hover{border-color:var(--accent)}
.kl a span{font-size:18px;font-family:Georgia,serif;font-style:italic;line-height:1.3}
.kl a small{font-size:10px;color:var(--muted)}
nav.rows{display:flex;flex-wrap:wrap;gap:4px;margin:12px 0}
nav.rows a{padding:0 9px;border:1px solid var(--line);border-radius:99px;font-family:Georgia,serif}
input#q{width:100%;font-size:18px;padding:10px 12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg)}
.hidden{display:none!important}
:root{--l1:#2e9e5b;--l2:#2a8fb0;--l3:#d39b1c;--l4:#e0612f;--l5:#8e4fc2}
.lv1{--lc:var(--l1)}.lv2{--lc:var(--l2)}.lv3{--lc:var(--l3)}.lv4{--lc:var(--l4)}.lv5{--lc:var(--l5)}
.legend{display:flex;flex-wrap:wrap;gap:6px;margin:16px 0 0;align-items:center}
.legend button,.legend span[data-lv]{font:inherit;font-size:13px;cursor:pointer;border:2px solid var(--lc);
background:var(--card);color:var(--fg);border-radius:99px;padding:2px 10px}
.legend button.off{opacity:.35;text-decoration:line-through}
.legend [data-lv] i{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--lc);margin-right:6px}
.how{margin-top:10px;font-size:14px}.how summary{cursor:pointer;color:var(--accent)}
.how ul{margin:6px 0;padding-left:20px}.how p{margin:6px 0}
.pills{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.pill2{display:inline-block;border:1px solid var(--line);background:var(--card);border-radius:99px;padding:0 10px;font-size:13px;font-weight:600}
.pill2:hover{border-color:var(--accent)}
.lvlpill{display:inline-block;color:#fff;background:var(--lc);border-radius:99px;padding:0 10px;font-size:13px;font-weight:600}
.hoods{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px;margin-top:16px}
.hood{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;display:block}
.hood:hover{border-color:var(--accent)}
.hood h3{margin:0;font-size:17px;color:var(--fg)}
.hood .hub{font-size:26px;float:right;line-height:1;font-family:Georgia,serif;font-style:italic;color:var(--accent)}
.hood .ks{font-size:15px;margin-top:6px;font-family:Georgia,serif;font-style:italic;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin:16px 0}
.stats div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 12px}
.stats b{display:block;font-size:22px}.stats span{font-size:12px;color:var(--muted)}
"""


def page(title, body, depth):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><link rel="stylesheet" href="{up}style.css"></head>
<body><main>
<header class="site"><a href="{up}index.html">Roots · Greek &amp; Latin in English</a>
<nav class="top"><a href="{up}index.html">A–Z</a><a href="{up}neighbourhoods.html">Neighbourhoods</a>
<a href="{up}core.html">Core</a><a href="{up}map.html">Map</a></nav></header>
{body}
<footer class="muted" style="margin-top:48px;font-size:12px">
Data: <a href="https://en.wiktionary.org/">English Wiktionary</a> (CC BY-SA 4.0) via
<a href="https://kaikki.org/">kaikki.org</a>; word frequencies from wordfreq.</footer>
</main></body></html>"""


def legend(toggle):
    tag = "button" if toggle else "span"
    items = "".join(f'<{tag} class="lv{n}" data-lv="{n}" title="{esc(d)}"><i></i>{esc(name)}</{tag}>'
                    for n, (name, d) in LEVELS.items())
    hint = ("Level = how common the word is. Tap to hide/show a level." if toggle
            else "Tile colour = how common the root's best-known word is.")
    rows = "".join(f"<li><b class='lv{n}' style='color:var(--lc)'>{esc(name)}</b> — {esc(d)}</li>"
                   for n, (name, d) in LEVELS.items())
    explain = ("<details class='how'><summary>How are levels decided?</summary>"
               "<p>Levels come from how often a word appears in everyday English (books, news, subtitles, "
               "the web), using the <i>wordfreq</i> word lists:</p><ul>" + rows + "</ul>"
               "<p>A root's level is the level of its most common word, so <i>tele</i> is Everyday "
               "because of <i>television</i>.</p></details>")
    return f'<div class="legend">{items}<span class="muted" style="font-size:12px">{hint}</span></div>' + explain


FILTER_JS = """<script>
document.querySelectorAll('.legend button').forEach(b=>b.addEventListener('click',()=>{
 b.classList.toggle('off');
 const off=[...document.querySelectorAll('.legend button.off')].map(x=>x.dataset.lv);
 document.querySelectorAll('ul.words li').forEach(li=>li.classList.toggle('hidden',off.includes(li.dataset.lv)));
}));
</script>"""


def build():
    m = json.loads((DATA / "model.json").read_text("utf-8"))
    words, roots = m["words"], m["roots"]
    for w, v in words.items():
        v["w"] = w
        v["lvl"] = level(v["z"])
    for k, r in roots.items():
        r["words"] = sorted(r["words"], key=lambda w: -words[w]["z"])
        r["lvl"] = min(words[w]["lvl"] for w in r["words"])
        r["top"] = r["words"][0]

    slugs, used = {}, set()
    for k in sorted(roots):
        s = "".join(c for c in k.lower() if c.isalpha()) or "x"
        base, i = s, 2
        while s in used:
            s, i = f"{base}{i}", i + 1
        used.add(s)
        slugs[k] = s
    label = lambda k: roots[k]["label"]
    maps.LABEL = label

    G = graph.analyse(list(words.values()))
    for h in G["neighbourhoods"]:
        h["name"] = graph.THEMES.get(h["hub"], f'{label(h["hub"])} neighbourhood')

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "r").mkdir(parents=True)
    (OUT / "n").mkdir()
    (OUT / "style.css").write_text(CSS + maps.MAP_CSS, "utf-8")
    (OUT / ".nojekyll").write_text("", "utf-8")

    def og(k):
        o = roots[k]["origin"]
        return f'<span class="og {o[0]}" title="{esc(o)}">{o[0]}</span>' if o else ""

    def word_li(v, key, prefix):
        bits = []
        for i, (p, k) in enumerate(v["parts"]):
            if i:
                bits.append('<span class="plus">+</span>')
            if k is None or k not in roots:
                bits.append(f'<span class="plain">{esc(p)}</span>')
            elif k == key:
                bits.append(f'<span class="self">{esc(p)}</span>')
            else:
                bits.append(f'<a href="{prefix}{slugs[k]}.html">{esc(p)}</a>')
        origins = {roots[k]["origin"] for k in v["roots"] if k in roots}
        hybrid = ' <span class="guess" title="mixes Greek and Latin roots">hybrid</span>' \
            if {"Greek", "Latin"} <= origins else ""
        guess = ' <span class="guess" title="split worked out automatically, not taken from Wiktionary">auto-split</span>' \
            if v["guessed"] else ""
        fam = f'<div class="fam"><b>also:</b> {esc(", ".join(v["family"]))}</div>' if v["family"] else ""
        gl = "; ".join(dict.fromkeys(v["gloss"]))[:180]
        return (f'<li class="lv{v["lvl"]}" data-lv="{v["lvl"]}"><span class="badge">{LEVELS[v["lvl"]][0]}</span>'
                f'<div class="w">{esc(v["w"])}</div><div class="parts">{"".join(bits)}{hybrid}{guess}</div>'
                f'<div class="g">{esc(gl)}</div>{fam}</li>')

    def tile(k, n, prefix):
        return (f'<a class="lv{roots[k]["lvl"]}" href="{prefix}{slugs[k]}.html" data-k="{esc(" ".join(roots[k]["forms"]).lower())}" '
                f'title="{esc(roots[k]["meaning"][:80])}"><span>{esc(label(k))}</span><small>{n} {og(k)}</small></a>')

    def graph_pills(k):
        node = G["nodes"].get(k)
        if not node:
            return '<a class="pill2" href="../neighbourhoods.html#islands">🏝 Island</a>'
        h = G["neighbourhoods"][node["hood"] - 1]
        out = f'<a class="pill2" href="../n/{h["id"]}.html">🏘 {esc(h["name"])}</a>'
        if node["core"]:
            out += '<a class="pill2" href="../core.html">★ Core root</a>'
        return out

    # ---- root pages
    for k, r in roots.items():
        by_form = defaultdict(list)
        shown = {}                       # "graphy" and "-graphy" are the same spelling
        for f in r["forms"]:
            shown.setdefault(f.strip("-"), f)
        for w in r["words"]:
            form = next((p for p, kk in words[w]["parts"] if kk == k), r["forms"][0])
            by_form[shown.get(form.strip("-"), form)].append(words[w])
        forms = sorted(by_form, key=lambda f: -len(by_form[f]))
        tags = "".join(f'<a class="form-tag" href="#f-{esc(f)}">{esc(f)}</a>' for f in forms)
        lv = r["lvl"]
        body = [f'<div class="hero"><div class="big">{esc(r["label"])}</div><div>'
                f'<h1 style="margin:0;font-size:22px">{esc(r["meaning"] or "—")}</h1>'
                f'<p class="muted" style="margin:4px 0 8px">{esc(r["origin"] or "origin unclear")} · '
                f'{len(r["words"])} words</p>'
                f'<div class="pills"><span class="lv{lv}"><span class="lvlpill">Level: {LEVELS[lv][0]}</span></span>'
                f'{graph_pills(k)}</div>'
                f'<dl class="meta"><dt>Spellings used here</dt><dd>{tags}</dd></dl></div></div>', legend(True)]
        for f in forms:
            body.append(f'<section class="form" id="f-{esc(f)}"><h2>{esc(f)}</h2><ul class="words">')
            body += [word_li(v, k, "") for v in by_form[f]]
            body.append("</ul></section>")
        body.append(FILTER_JS)
        (OUT / "r" / f"{slugs[k]}.html").write_text(page(f'{r["label"]} — Greek & Latin roots', "\n".join(body), 1), "utf-8")

    # ---- index A–Z
    letters = defaultdict(list)
    for k in sorted(roots, key=lambda k: label(k).lower()):
        letters[label(k)[0].upper()].append(k)
    nav = "".join(f'<a href="#row-{L}">{L}</a>' for L in sorted(letters))
    n_greek = sum(r["origin"] == "Greek" for r in roots.values())
    body = ["<h1 class='serif'>Roots: the Greek &amp; Latin inside English</h1>",
            f"<p class='muted'>{len(roots)} roots ({n_greek} Greek, {len(roots) - n_greek} Latin) · "
            f"{len(words)} words built from them. Pick a root to see every word it helps build. "
            "Every root inside a word is a link, so you can keep wandering.</p>",
            '<input id="q" placeholder="Filter roots: tele, graph, port…" autocomplete="off">',
            f'<nav class="rows">{nav}</nav>', legend(False)]
    for L in sorted(letters):
        tiles = "".join(tile(k, len(roots[k]["words"]), "r/") for k in letters[L])
        body.append(f'<div class="row" id="row-{L}"><h2 class="serif">{L}</h2><div class="kl">{tiles}</div></div>')
    body.append("""<script>
const q=document.getElementById('q');
q.addEventListener('input',()=>{const v=q.value.trim().toLowerCase().replace(/-/g,'');
document.querySelectorAll('.kl a').forEach(a=>a.classList.toggle('hidden',
 !!v&&!a.dataset.k.split(' ').some(f=>f.replace(/-/g,'').startsWith(v))));
document.querySelectorAll('.row').forEach(r=>r.classList.toggle('hidden',!r.querySelector('.kl a:not(.hidden)')));});
</script>""")
    (OUT / "index.html").write_text(page("Roots — Greek & Latin in English", "\n".join(body), 0), "utf-8")

    # ---- neighbourhoods
    S, hoods = G["summary"], G["neighbourhoods"]
    stats = [(S["giant"], f'of {S["nodes"]} roots in one connected web'),
             (S["avg_path"], "average steps between two roots"),
             (S["diameter"], "most steps between any two roots"),
             (S["neighbourhoods"], "neighbourhoods"),
             (S["core_size"], f'core roots (each linked to ≥{S["core_k"]} others in the core)'),
             (S["islands"], "islands, cut off from the rest")]
    body = ["<h1>Root neighbourhoods</h1>",
            "<p class='muted'>Think of every root as a town and every word as roads joining its roots. "
            "Nearly all roots end up in one big web, and the web falls into neighbourhoods: groups of roots "
            "that build far more words with each other than with the rest. The groups were found automatically "
            "(Louvain community detection); the names are hand-picked to fit. See them on the "
            "<a href='map.html' style='color:var(--accent)'>map</a>.</p>",
            '<div class="stats">' + "".join(f"<div><b>{v}</b><span>{esc(t)}</span></div>" for v, t in stats)
            + "</div>", '<div class="hoods">']
    for h in hoods:
        body.append(f'<a class="hood" href="n/{h["id"]}.html"><span class="hub">{esc(label(h["hub"]))}</span>'
                    f'<h3>{esc(h["name"])}</h3><span class="muted" style="font-size:13px">{len(h["members"])} roots</span>'
                    f'<div class="ks">{esc(" · ".join(label(k) for k in h["members"][:12]))}…</div></a>')
    body.append("</div>")
    body.append('<h2 id="islands" style="margin-top:40px">🏝 Islands</h2><p class="muted">Roots that only ever '
                "combine with each other, cut off from the rest of the web.</p><ul class='words'>")
    island_roots = {k for isl in G["islands"] for k in isl}
    for v in sorted(words.values(), key=lambda v: v["w"]):
        if v["roots"] and all(k in island_roots for k in v["roots"]):
            body.append(word_li(v, None, "r/"))
    body.append("</ul>")
    (OUT / "neighbourhoods.html").write_text(page("Root neighbourhoods", "\n".join(body), 0), "utf-8")

    for h in hoods:
        mem = set(h["members"])
        inner = sorted((v for v in words.values() if len(set(v["roots"])) >= 2 and set(v["roots"]) <= mem),
                       key=lambda v: (v["lvl"], -v["z"]))
        tiles = "".join(tile(k, G["nodes"][k]["inner_degree"], "../r/") for k in h["members"])
        near = " ".join(f'<a class="pill2" href="{o}.html">{esc(hoods[o - 1]["name"])}</a>' for o in h["neighbours"])
        body = [f'<div class="hero"><div class="big">{esc(label(h["hub"]))}</div><div>'
                f'<h1 style="margin:0">{esc(h["name"])}</h1>'
                f'<p class="muted">{len(h["members"])} roots · {len(inner)} words made entirely inside this '
                f'neighbourhood. Hub: <i>{esc(label(h["hub"]))}</i>, its best-connected root.</p>'
                f'<div class="pills"><span class="muted" style="font-size:13px">Next door:</span> {near}</div></div></div>',
                "<h3>Roots here (number = how many others in this neighbourhood it builds words with)</h3>",
                f'<div class="kl">{tiles}</div>',
                f"<h2 style='margin-top:32px'>Words inside {esc(h['name'])}</h2>", legend(True),
                "<ul class='words' style='margin-top:12px'>"]
        body += [word_li(v, None, "../r/") for v in inner]
        body.append("</ul>" + FILTER_JS)
        (OUT / "n" / f'{h["id"]}.html').write_text(page(h["name"], "\n".join(body), 1), "utf-8")

    # ---- core
    core = [k for k, v in G["nodes"].items() if v["core"]]
    body = [f"<h1>The core {len(core)}</h1>",
            f"<p class='muted'>The densest part of the web: each of these roots builds words with at least "
            f"{S['core_k']} others in this same group (the graph's maximum <i>k-core</i>). Grouped by "
            "neighbourhood; the number is how many words the root appears in.</p>", legend(False)]
    for h in hoods:
        cs = sorted((k for k in h["members"] if k in core), key=lambda k: -len(roots[k]["words"]))
        if cs:
            body.append(f'<h3><a href="n/{h["id"]}.html">{esc(h["name"])}</a></h3><div class="kl">'
                        + "".join(tile(k, len(roots[k]["words"]), "r/") for k in cs) + "</div>")
    (OUT / "core.html").write_text(page(f"The core {len(core)} roots", "\n".join(body), 0), "utf-8")

    # ---- map + data
    (OUT / "map.html").write_text(page("Map of the roots", maps.map_body(
        G, list(words.values()), None, legend(False),
        node_href=lambda k: f"r/{slugs[k]}.html", node_level=lambda k: roots[k]["lvl"],
        node_title=lambda k: roots[k]["meaning"][:60]), 0), "utf-8")
    (OUT / "graph.json").write_text(json.dumps(
        {"summary": S, "neighbourhoods": [{**h, "members": [label(k) for k in h["members"]]} for h in hoods],
         "roots": {label(k): {**v, "slug": slugs[k]} for k, v in G["nodes"].items()}},
        ensure_ascii=False, indent=1), "utf-8")
    print(f"built {len(roots)} root pages, {len(words)} words, {len(hoods)} neighbourhoods → {OUT}")


if __name__ == "__main__":
    build()
