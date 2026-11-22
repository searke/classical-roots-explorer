# Roots — the Greek & Latin inside English

A static website for exploring English words through their Greek and Latin roots, one root at a time.
It's a sister project to the [Sino-Japanese word explorer](https://github.com/searke/sinojapanese-word-dictionary),
with the same design and graph tools.

- **A–Z** (`docs/index.html`): every root, coloured by how common its best-known word is.
- **Root pages** (`docs/r/<root>.html`): every word the root helps build, grouped by the spelling it takes
  (*tele- / telo-*, *-graph / -graphy*). Every other root in a word links to its own page.
- **Root words and families**: a word is listed when it's built from at least two roots
  (*telephone*, *photograph*, *independent*). Obvious derivations are folded under it
  (*photographer, photography* under *photograph*).
- **Neighbourhoods, Core and Map**: roots are nodes and words link their roots; Louvain community
  detection finds the neighbourhoods (names hand-picked in `scripts/graph.py`). Very common small
  prefixes (*in-, de-, con-*…) are left out of the graph because they attach to everything.

## How words are split

1. **Wiktionary breakdowns.** Most words come straight from Wiktionary's etymology templates
   ("from *tele-* + *-phone*").
2. **Automatic splits.** Latin/Greek borrowings that Wiktionary doesn't break down (*television*, *transport*)
   are split using pieces Wiktionary already knows. These are marked *auto-split* on the site.
3. **Origin.** A root is Greek or Latin according to its Wiktionary etymology; Latin words borrowed from
   Greek count as Greek.

Expect some mistakes: the splitting is automatic and Wiktionary isn't perfectly consistent.

## Build

```sh
pip install -r requirements.txt
scripts/fetch_data.sh          # downloads English Wiktionary from kaikki.org (~3.4 GB) and slims it
python3 scripts/analyse.py     # data/model.json: roots, root words, families
python3 scripts/build.py       # writes the site into docs/
```

## Data & license

- **Word data:** adapted from the [English Wiktionary](https://en.wiktionary.org/) (CC BY-SA 4.0), via
  [kaikki.org](https://kaikki.org/)'s Wiktextract dumps (Tatu Ylonen, LREC 2022).
- **Word frequencies:** [wordfreq](https://github.com/rspeer/wordfreq) by Robyn Speer (data CC BY-SA 4.0).
- **The generated site** (`docs/`) is shared under CC BY-SA 4.0: see `LICENSE-CONTENT.md` and `docs/about.html`.
- **The code** (`scripts/`) is under the MIT licence: see `LICENSE`.
- Every word and root links back to Wiktionary, including the "English words prefixed/suffixed with …"
  category lists.
