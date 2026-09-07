# M. S. Santhanam

A static, multipage academic website preserving the original cream, serif, and coral design.

## Preview

Run `python3 -m http.server 8080`, then open http://localhost:8080.
No build or JavaScript framework is required to serve the committed site. Deploy the root HTML files, `styles.css`, `script.js`, `search-engine.js`, `search-index.js`, and `vendor/` to any static host, including a subdirectory.

## Content and rebuilding

The IISER source snapshots in `content/source/` were retrieved on 7 September 2026 from https://sites.iiserpune.ac.in/~santh/. They contain the main pages, QML tutorial, and 13 available course archives. Source navigation, scripts, trackers, and old presentation styles are not included in the generated pages. Each generated content page links back to its source.

To rebuild after editing the snapshots or templates:

```sh
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/build.py
.venv/bin/python tools/check.py
node --check script.js
node tools/check-search.cjs
```

`tools/build.py` generates 22 pages and the search index together. Edit templates there rather than editing generated HTML. The archive has 81 journal/research entries (including the homepage's new preprint), 33 general articles, and 38 people. Course titles are normalized where legacy HTML titles were incorrect. Expired opportunity announcements are labeled closed. Affiliations and publication metadata follow the source; they are not independently inferred.

The original `lec_notes.html`, `course/phy342/phy342_nld.html`, `course/phy361/phy361.html`, and `course/phy313/phy313.html` returned 404. Teaching lists these as unavailable. PDFs, notebooks, videos, and other linked resources remain at their original hosts; their link labels and surrounding website text are searchable, not their external file contents.

## Search

Vendored Fuse.js 7.1.0 (Apache-2.0) provides typo-tolerant, multi-word search over titles, authors, years, people, topics, and course text. The index is local, and no query is sent to a service. All pages have a search dialog (Cmd/Ctrl+K) and a dedicated `search.html?q=…` page with category filters, keyboard navigation, and direct section links. Content and navigation work without JavaScript; fuzzy search requires JavaScript.

Research topic assignments and three selected publications per research section are maintained in `content/research-topics.json`. These are editorial topic groupings; a paper can belong to multiple topics. Publication filters combine topic, article type, year, and fuzzy title/author search, and preserve filter selections in shareable URL parameters. Clearing filters restores the full archive.

The subtle Top control appears after scrolling, fades after 2.5 seconds without interaction, and reappears on pointer, touch, keyboard, or scroll activity. It remains available while keyboard-focused and respects reduced-motion preferences.
