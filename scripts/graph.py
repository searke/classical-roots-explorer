"""The root graph: Greek/Latin roots are nodes; roots that appear in the same word are linked.

Used by build.py for the neighbourhood and core pages. Run it directly
(python3 scripts/graph.py) to print summary statistics.
"""
from collections import Counter

import networkx as nx

# Louvain community detection. The resolution sets how fine-grained the
# neighbourhoods are: 1.5 gives roughly 27 groups of 30-150 roots.
RESOLUTION = 1.5
SEED = 42

# Hand-picked names, keyed by each neighbourhood's hub. The groups shift a little when
# the data changes, so re-check these after re-running analyse.py
# (python3 scripts/graph.py lists each hub and its members).
# Hand-picked names, keyed by each neighbourhood's hub (its best-connected
# root). A neighbourhood whose hub isn't listed is just named after the hub.
THEMES = {
    "itis": "Disease & anatomy",
    "mult": "Many & one",
    "electr": "Physics & light",
    "tri": "Numbers & chemistry",
    "hydr": "Chemical names",
    "osis": "Cells & tumours",
    "neur": "Nerves, heart & skin",
    "count": "Against & making",
    "immun": "Medicine & the mind",
    "pol": "Counting & shapes",
    "arch": "Rule, cutting & killing",
    "hyper": "Hormones, blood & excess",
    "bio": "Life sciences",
    "log": "The -ologies",
    "metr": "Measuring & form",
    "gen": "Birth & origins",
    "micr": "Big, small & seeing",
    "super": "Beyond: super, tele, ultra",
    "cyt": "Cells & tumours",
    "par": "Alongside",
    "bi": "Two, half & air",
    "counter": "Against & making",
    "atic": "Odds & ends",
    "intr": "Inside & outside the body",
    "graph": "Writing & society",
    "som": "Bodies & centres",
    "ped": "Feet, children & wheels",
    "post": "After & tiny",
    "syn": "Together & under",
    "aut": "Self & rule",
    "mal": "Bad & badly formed",
    "epi": "Upon & names",
    "circum": "Around & across",
    "typ": "Types & first forms",
}

# Small Latin/Greek prefixes that attach to almost anything (in-, de-, con-…). They link
# unrelated roots together and blur the neighbourhoods, so the graph leaves them out.
GENERIC = {"in", "im", "il", "ir", "de", "dis", "di", "con", "com", "co", "col", "cor", "ex", "e", "ef",
           "pre", "pro", "sub", "sup", "sur", "ad", "ab", "ac", "af", "ag", "al", "ap", "as", "at", "a",
           "an", "en", "em", "per", "ob", "op", "re", "inter", "trans", "tran", "des", "un", "anti", "ant"}


def build_graph(words):
    """words: list of dicts with a "roots" list. Every pair of roots in a word is linked."""
    G = nx.Graph()
    for w in words:
        rs = [r for r in dict.fromkeys(w["roots"]) if r not in GENERIC]
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                G.add_edge(a, b)
    return G


def analyse(words):
    """Return per-root stats, neighbourhoods, islands and summary numbers."""
    G = build_graph(words)
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    H = G.subgraph(comps[0]).copy()

    comms = nx.community.louvain_communities(H, resolution=RESOLUTION, seed=SEED)
    comms = sorted(comms, key=len, reverse=True)

    betw = nx.betweenness_centrality(H)
    eig = nx.eigenvector_centrality(H, max_iter=1000)
    close = nx.closeness_centrality(H)
    core = nx.core_number(H)
    kmax = max(core.values())

    hoods = []
    node = {}
    for i, members in enumerate(comms):
        sub = H.subgraph(members)
        ranked = sorted(members, key=lambda c: (-sub.degree(c), -H.degree(c), c))
        hub = ranked[0]
        hoods.append({"id": i + 1, "hub": hub, "name": THEMES.get(hub, f"{hub} neighbourhood"),
                      "members": ranked})
        for c in members:
            node[c] = {"hood": i + 1, "degree": H.degree(c), "inner_degree": sub.degree(c),
                       "betweenness": round(betw[c], 5), "eigenvector": round(eig[c], 5),
                       "closeness": round(close[c], 5), "core": core[c] == kmax}

    # links between neighbourhoods (how many words cross each border)
    cross = Counter()
    for a, b in H.edges():
        ha, hb = node[a]["hood"], node[b]["hood"]
        if ha != hb:
            cross[(ha, hb)] += 1
            cross[(hb, ha)] += 1
    for h in hoods:
        nbrs = [(o, n) for (s, o), n in cross.items() if s == h["id"]]
        h["neighbours"] = [o for o, _ in sorted(nbrs, key=lambda t: -t[1])[:5]]

    islands = [sorted(c) for c in comps[1:]]
    summary = {
        "nodes": G.number_of_nodes(), "links": G.number_of_edges(),
        "giant": H.number_of_nodes(), "islands": len(islands),
        "avg_path": round(nx.average_shortest_path_length(H), 2),
        "diameter": nx.diameter(H),
        "clustering": round(nx.average_clustering(H), 3),
        "core_k": kmax, "core_size": sum(v == kmax for v in core.values()),
        "neighbourhoods": len(hoods),
    }
    return {"summary": summary, "nodes": node, "neighbourhoods": hoods, "islands": islands}


if __name__ == "__main__":
    import json
    from pathlib import Path
    m = json.load(open(Path(__file__).resolve().parent.parent / "data" / "model.json"))
    g = analyse(list(m["words"].values()))
    for key, v in g["summary"].items():
        print(f"{key:>15}: {v}")
    for h in g["neighbourhoods"]:
        print(h["id"], h["hub"], len(h["members"]), " ".join(h["members"][:18]))
    print("islands:", g["islands"][:30])
