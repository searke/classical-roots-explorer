# Roots — the Greek & Latin inside English

A static website for exploring English words through their Greek and Latin roots, one root at a time.
It's a sister project to the [Sino-Japanese word explorer](https://github.com/searke/sinojapanese-word-dictionary),
with the same design and graph tools.

- **A–Z** (`docs/index.html`): every root, coloured by how common its best-known word is.
- **Root pages** (`docs/r/<root>.html`): every word the root helps build, grouped by the spelling it takes
  (*tele- / telo-*, *-graph / -graphy*). Every other root in a word links to its own page.
- **Words and families**: every word containing a root is listed under it, including single-root words
  (*generate*, *gene* and *hydrogen* all appear under *gen*). Obvious derivations are folded under
  their word (*generation, generator* under *generate*).
- **Neighbourhoods, Core and Map**: roots are nodes and words link their roots; Louvain community
  detection finds the neighbourhoods (names hand-picked in `scripts/graph.py`). Very common small
  prefixes (*in-, de-, con-*…) are left out of the graph because they attach to everything.

## How words get their roots

1. **Roots** are Greek/Latin prefixes, suffixes and combining forms found in Wiktionary's word
   breakdowns (*tele-*, *-graph*, *bio-*), plus about 150 well-known Latin/Greek stems listed by hand in
   `scripts/roots_list.py` (*dict*, *duc*, *ject*, *port*, *struct*…). Spellings of one root are grouped:
   *-gen, -genic, geno-, -genesis*; *ad-, ac-, af-, ap-…*
2. **Wiktionary breakdowns** ("from *tele-* + *-phone*") are followed first, through English words.
3. **Otherwise** a Latin/Greek borrowing is matched against the roots (optional prefixes + stems), and the
   match only counts if the word's own etymology confirms it: *predict* ← Latin *praedīcō* contains *dic*;
   *agenda* ← Latin *agō* does not contain *gen*. These are marked *auto-split* on the site.
4. **Origin**: a root is Greek or Latin according to Wiktionary; Latin words borrowed from Greek count as Greek.

Expect some mistakes: the matching is automatic and Wiktionary isn't perfectly consistent.

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
