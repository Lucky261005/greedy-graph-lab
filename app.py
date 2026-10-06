"""
Greedy Graph Lab - Streamlit web app.

Step-by-step visualiser for Kruskal's MST, Prim's MST and Dijkstra's shortest paths.
Run locally:   streamlit run app.py
"""
import html
import math
import os
import re
import time

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from algorithms import BUILDERS, CODE, INF, ORDER, TITLES, Graph, ename, name

st.set_page_config(page_title="Greedy Graph Lab", page_icon="🌿", layout="wide")

# drag-and-drop graph canvas (plain HTML/JS, see canvas_component/index.html)
canvas = components.declare_component(
    "graph_canvas", path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "canvas_component"))

# ----------------------------------------------------------------------------
# look & feel
# ----------------------------------------------------------------------------
COMP = ["#6370f5", "#e85ca0", "#19beec", "#f49e2c", "#34d66c", "#aa78fa",
        "#f0d250", "#fa785a", "#5adcc8", "#c85af0", "#82c850", "#f082be"]
CYAN, GREEN, ORANGE, PINK, GOLD = "#19beec", "#34d66c", "#f49e2c", "#e85ca0", "#ffd65a"
EDGE = {  # colour, width
    "idle": ("#404e74", 2.2), "cand": ("#228cbe", 3.2), "cmp": (CYAN, 5), "accept": (GREEN, 6),
    "reject": ("#963864", 2), "relax": (ORANGE, 5), "skip": ("#26304a", 1.6), "path": (GOLD, 7)}
NODE = {"idle": "#3a486c", "seen": "#2f8fa6", "tree": GREEN, "current": ORANGE, "done": GREEN}
KIND = {"cmp": CYAN, "take": GREEN, "done": GREEN, "reject": PINK, "info": "#e8ecf5"}

st.html("""
<style>
.block-container{padding-top:3.4rem;max-width:1400px}
.stButton button{white-space:nowrap}
h1{padding-top:0!important;line-height:1.2!important}
.card{background:#090d1a;border:1px solid #1e2944;border-radius:14px;padding:14px 18px;margin-bottom:12px}
.card h4{margin:0 0 8px;font:600 11px/1 sans-serif;letter-spacing:.08em;color:#5c6882;text-transform:uppercase}
.chip{display:inline-block;margin:0 6px 6px 0;padding:3px 10px;border-radius:8px;border:1px solid;
      font:600 12px/1.6 monospace;color:#e8ecf5}
.code{font:13px/1.55 'Consolas','DejaVu Sans Mono',monospace;color:#cdd4e4;white-space:pre}
.code .ln{display:inline-block;width:24px;color:#5c6882;text-align:right;margin-right:12px}
.code .hl{background:rgba(52,214,108,.16);border-left:3px solid #34d66c;display:block;margin-left:-18px;
          padding-left:15px;margin-right:-18px}
.code .k{color:#9682ff}.code .b{color:#5fc8eb}.code .c{color:#5c6882}.code .n{color:#f49e2c}
.status{font:700 20px/1.3 sans-serif}
.why{color:#96a2b8;font:14px/1.5 sans-serif;margin-top:6px}
.flow{stroke-dasharray:10 8;animation:dash 0.9s linear infinite}
@keyframes dash{to{stroke-dashoffset:-18}}
.pulse{animation:pulse 1.1s ease-in-out infinite}
@keyframes pulse{50%{opacity:.45}}
</style>
""")


# ----------------------------------------------------------------------------
# graph state
# ----------------------------------------------------------------------------
def new_graph(kind):
    g = Graph()
    if kind == "Random graph":
        g.random()
    st.session_state.pos = [tuple(p) for p in g.pos]
    st.session_state.edges = [tuple(e) for e in g.edges]
    st.session_state.start = 0
    st.session_state.gver = st.session_state.get("gver", 0) + 1
    st.session_state.step = 0
    st.session_state.playing = False


if "pos" not in st.session_state:
    new_graph("Sample graph")


@st.cache_data(show_spinner=False)
def build(algo, pos, edges, start):
    g = Graph()
    g.pos, g.edges, g.start = [list(p) for p in pos], [list(e) for e in edges], start
    return BUILDERS[algo](g)


# ----------------------------------------------------------------------------
# sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🌿 Greedy Graph Lab")
    algo = st.radio("Algorithm", ORDER, format_func=lambda k: TITLES[k][0].replace("'s Algorithm", ""),
                    key="algo")
    c1, c2 = st.columns(2)
    if c1.button("Sample graph", width="stretch"):
        new_graph("Sample graph")
        st.rerun()
    if c2.button("Random graph", width="stretch"):
        new_graph("Random graph")
        st.rerun()

    n = len(st.session_state.pos)
    letters = [name(i) for i in range(n)]
    if algo != "kruskal":
        st.session_state.start = st.selectbox("Start node", range(n), format_func=name,
                                              index=min(st.session_state.start, n - 1))
    st.markdown("**Edges** (edit weights, add or delete rows)")
    df = pd.DataFrame([(name(u), name(v), w) for u, v, w in st.session_state.edges],
                      columns=["From", "To", "Weight"])
    edited = st.data_editor(
        df, num_rows="dynamic", hide_index=True, width="stretch",
        key=f"editor{st.session_state.gver}",
        column_config={"From": st.column_config.SelectboxColumn(options=letters, required=True),
                       "To": st.column_config.SelectboxColumn(options=letters, required=True),
                       "Weight": st.column_config.NumberColumn(min_value=1, max_value=99, step=1,
                                                               required=True)})
    seen, clean = set(), []
    for _, r in edited.dropna().iterrows():
        u, v = letters.index(r["From"]), letters.index(r["To"])
        key = (min(u, v), max(u, v))
        if u != v and key not in seen:
            seen.add(key)
            clean.append((key[0], key[1], int(r["Weight"])))
    delay = st.slider("Seconds per step (autoplay)", 0.2, 2.5, 0.9, 0.1)
    st.caption("Drag nodes in the graph to move them; edit the table to change edges and weights.")

# an edit to the edges or the start node restarts the run
sig = (algo, tuple(clean), st.session_state.get("start", 0))
if st.session_state.get("sig") != sig:
    st.session_state.sig = sig
    st.session_state.edges = clean
    st.session_state.step = 0
    st.session_state.playing = False

snaps = build(algo, tuple(st.session_state.pos), tuple(clean), st.session_state.get("start", 0))
last = len(snaps) - 1
st.session_state.step = max(0, min(last, st.session_state.step))


# ----------------------------------------------------------------------------
# rendering helpers
# ----------------------------------------------------------------------------
def chip(text, color, filled=False, dim=False):
    bg = f"{color}33" if filled else f"{color}14"
    op = "opacity:.45;" if dim else ""
    return (f'<span class="chip" style="border-color:{color};background:{bg};{op}">'
            f'{html.escape(text)}</span>')


def trace_path(snap, target):
    p = snap["panel"]
    if p["dist"][target] == INF:
        return [], set()
    path = [target]
    while p["prev"][path[-1]] is not None:
        path.append(p["prev"][path[-1]])
    path.reverse()
    pairs = {frozenset(x) for x in zip(path, path[1:])}
    return path, pairs


def graph_svg(snap, path_pairs=None):
    """SVG of the graph. Edges, weight tags and nodes carry data-* attributes so the
    drag-and-drop component (canvas_component/index.html) can move them in the browser."""
    pos = [(x - 16, y - 96) for x, y in st.session_state.pos]
    edges = st.session_state.edges
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 744 558" width="744" height="558">'
         '<style>.flow{stroke-dasharray:10 8;animation:dash .9s linear infinite}'
         '@keyframes dash{to{stroke-dashoffset:-18}}.pulse{animation:pulse 1.1s ease-in-out infinite}'
         '@keyframes pulse{50%{opacity:.45}}</style>'
         '<rect width="744" height="558" rx="14" fill="#090d1a"/>']
    states = []
    for i, e in enumerate(edges):
        st_ = snap["est"][i]
        if path_pairs is not None:
            st_ = "path" if frozenset(e[:2]) in path_pairs else "idle"
        states.append(st_)
    for i in sorted(range(len(edges)), key=lambda i: states[i] in ("accept", "path", "cmp", "relax")):
        u, v, w = edges[i]
        (x1, y1), (x2, y2) = pos[u], pos[v]
        col, wd = EDGE[states[i]]
        if states[i] in ("accept", "path", "relax", "cmp"):
            o.append(f'<line data-u="{u}" data-v="{v}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" '
                     f'stroke-opacity=".25" stroke-width="{wd + 8}" stroke-linecap="round"/>')
        dash = ' stroke-dasharray="6 6"' if states[i] in ("reject", "skip") else ""
        cls = ' class="flow"' if states[i] in ("accept", "path") else (
            ' class="pulse"' if states[i] == "cmp" else "")
        o.append(f'<line{cls} data-u="{u}" data-v="{v}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" '
                 f'stroke-width="{wd}" stroke-linecap="round"{dash}/>')
    for i, (u, v, w) in enumerate(edges):
        (x1, y1), (x2, y2) = pos[u], pos[v]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        o.append(f'<g class="tag" data-u="{u}" data-v="{v}" transform="translate({mx},{my})">'
                 f'<rect x="-14" y="-10" width="28" height="20" rx="6" fill="#3c2c0e" stroke="#6e5018"/>'
                 f'<text x="0" y="5" text-anchor="middle" fill="{ORANGE}" font-family="sans-serif" '
                 f'font-size="13" font-weight="700">{w}</text></g>')
    comp = snap["comp"]
    for i, (x, y) in enumerate(pos):
        col = COMP[comp[i] % len(COMP)] if comp is not None else NODE[snap["nst"][i]]
        glow = comp is not None and comp.count(comp[i]) > 1 or snap["nst"][i] in ("current", "tree", "done")
        g = [f'<g class="node" data-i="{i}" transform="translate({x},{y})">']
        if glow:
            g.append(f'<circle r="30" fill="{col}" fill-opacity=".18"/>')
        cls = ' class="pulse"' if snap["nst"][i] == "current" else ""
        g.append(f'<circle{cls} r="21" fill="{col}" stroke="#ffffff55" stroke-width="2"/>'
                 f'<text y="6" text-anchor="middle" fill="#fff" font-family="sans-serif" font-size="18" '
                 f'font-weight="700" style="pointer-events:none">{name(i)}</text>')
        if algo != "kruskal" and i == st.session_state.start:
            g.append(f'<circle r="27" fill="none" stroke="{GOLD}" stroke-width="2"/>'
                     f'<text y="42" text-anchor="middle" fill="{GOLD}" font-family="sans-serif" '
                     f'font-size="10" font-weight="700" style="pointer-events:none">START</text>')
        lab = snap["nlab"][i]
        if lab is not None and algo == "dijkstra":
            c = "#5c6882" if lab == "inf" else CYAN
            g.append(f'<rect x="-17" y="-49" width="34" height="20" rx="6" fill="{c}22" stroke="{c}"/>'
                     f'<text y="-35" text-anchor="middle" fill="{c}" font-family="sans-serif" '
                     f'font-size="13" font-weight="700" style="pointer-events:none">{"∞" if lab == "inf" else lab}</text>')
        g.append("</g>")
        o.append("".join(g))
    o.append("</svg>")
    return "".join(o)


def data_panel(snap):
    p = snap["panel"]
    if p["kind"] == "kruskal":
        cmap = {"wait": "#3a486c", "cmp": CYAN, "accept": GREEN, "reject": PINK, "skip": "#3a486c"}
        edges = st.session_state.edges
        h = "<h4>Sorted edges (waiting → checked)</h4>" + "".join(
            chip(f"{ename(edges[i])} {edges[i][2]}", cmap[s], s in ("cmp", "accept"), s == "skip")
            for i, s in p["sorted"])
        h += "<h4 style='margin-top:10px'>Disjoint sets (Union-Find)</h4>" + "".join(
            chip("{" + ",".join(name(m) for m in mem) + "}", COMP[root % len(COMP)], True)
            for root, mem in p["sets"])
    elif p["kind"] == "prim":
        h = "<h4>Priority queue (cheapest first)</h4>"
        if p["popped"]:
            w, e, u, v = p["popped"]
            h += chip(f"popped {name(u)}-{name(v)} {w}", ORANGE, True)
        h += "".join(chip(f"{name(u)}-{name(v)} {w}", "#5c6882" if stale else CYAN, False, stale)
                     for w, e, u, v, stale in p["pq"]) or ("" if p["popped"] else "<i>(empty)</i>")
        h += "<h4 style='margin-top:10px'>Nodes in tree</h4>" + "".join(
            chip(name(v), GREEN, True) for v in p["tree"])
    else:
        col = {"idle": "#3a486c", "seen": CYAN, "current": ORANGE, "done": GREEN}
        h = "<h4>Distance table (node · distance · parent)</h4>" + "".join(
            chip(f"{name(v)}  {'∞' if p['dist'][v] == INF else p['dist'][v]}  ←"
                 f"{name(p['prev'][v]) if p['prev'][v] is not None else '-'}",
                 col[p["state"][v]], p["state"][v] == "current") for v in range(len(p["dist"])))
        h += "<h4 style='margin-top:10px'>Priority queue (dist, node)</h4>" + "".join(
            chip(f"{d},{name(v)}", "#5c6882" if stale else CYAN, False, stale)
            for d, v, stale in p["pq"][:12]) or "<i>(empty)</i>"
    return f'<div class="card">{h}</div>'


KW = {"def", "if", "else", "while", "return", "for", "in", "not", "continue", "break"}
BI = {"len", "sorted", "heappop", "heappush", "heapify"}


def code_panel(snap):
    rows = []
    for i, text in enumerate(CODE[algo]):
        toks = []
        for t in re.findall(r"\w+|\s+|#.*|.", text):
            e = html.escape(t)
            if t.startswith("#"):
                toks.append(f'<span class="c">{e}</span>')
            elif t in KW:
                toks.append(f'<span class="k">{e}</span>')
            elif t in BI or t == "INF":
                toks.append(f'<span class="b">{e}</span>')
            elif t.isdigit():
                toks.append(f'<span class="n">{e}</span>')
            else:
                toks.append(e)
        line = f'<span class="ln">{i + 1}</span>' + "".join(toks)
        rows.append(f'<span class="hl">{line}</span>' if snap["line"] == i + 1 else line + "\n")
    return f'<div class="card"><h4>{algo}.py</h4><div class="code">{"".join(rows)}</div></div>'


# ----------------------------------------------------------------------------
# page
# ----------------------------------------------------------------------------
title, sub, t_c, s_c = TITLES[algo]
st.markdown(f"# {title}")
st.caption(f"{sub}   ·   **Time** {t_c}   ·   **Space** {s_c}")

b1, b2, b3, b4, b5 = st.columns([1.5, 1.2, 1.5, 1.2, 5])
if b1.button("⏮ Restart", width="stretch"):
    st.session_state.step, st.session_state.playing = 0, False
if b2.button("◀ Prev", width="stretch"):
    st.session_state.step, st.session_state.playing = max(0, st.session_state.step - 1), False
play_label = "⏸ Pause" if st.session_state.get("playing") else ("↻ Replay" if st.session_state.step >= last else "▶ Play")
if b3.button(play_label, type="primary", width="stretch"):
    if st.session_state.step >= last:
        st.session_state.step = 0
    st.session_state.playing = not st.session_state.get("playing", False)
if b4.button("Next ▶", width="stretch"):
    st.session_state.step, st.session_state.playing = min(last, st.session_state.step + 1), False
st.session_state.step = b5.slider("Step", 0, last, st.session_state.step, label_visibility="collapsed")

snap = snaps[st.session_state.step]
left, right = st.columns([3, 2], gap="medium")

with left:
    path_pairs = None
    if algo == "dijkstra" and st.session_state.step == last:
        n = len(st.session_state.pos)
        tgt = st.selectbox("Trace the shortest path to…", ["(none)"] + [name(i) for i in range(n)])
        if tgt != "(none)":
            path, path_pairs = trace_path(snap, ord(tgt) - 65)
            st.success(("Shortest path: " + "  ›  ".join(name(x) for x in path) +
                        f"   (cost {snap['panel']['dist'][ord(tgt) - 65]})") if path
                       else f"{tgt} is unreachable from the start node.")
    moved = canvas(svg=graph_svg(snap, path_pairs), pos=[[x - 16, y - 96] for x, y in st.session_state.pos],
                   key=f"canvas{st.session_state.gver}", default=None)
    if moved:
        new_pos = [(round(x + 16), round(y + 96)) for x, y in moved]
        if len(new_pos) == len(st.session_state.pos) and new_pos != list(st.session_state.pos):
            st.session_state.pos = new_pos
            st.rerun()
    st.caption("Drag the nodes to rearrange the graph.")

with right:
    st.html(f'<div class="card"><div class="status" style="color:{KIND[snap["kind"]]}">'
            f'{html.escape(snap["text"])}</div><div class="why">{html.escape(snap["why"])}</div></div>')
    st.html(data_panel(snap))
    st.html(code_panel(snap))

m = st.columns(4)
m[0].markdown(f"**{snap['info']}**")
for col, (label, val, _) in zip(m[1:], snap["stats"]):
    col.metric(label.title().replace("Mst", "MST"), val)
m[3].metric("Step", f"{st.session_state.step + 1} / {len(snaps)}")

# autoplay: wait, advance one step, rerun
if st.session_state.get("playing"):
    if st.session_state.step >= last:
        st.session_state.playing = False
    else:
        time.sleep(delay * snap["hold"] ** 0.5)
        st.session_state.step += 1
        st.rerun()
