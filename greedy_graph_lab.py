"""
Greedy Graph Lab  -  DAA CIA 3(b)   (Unit 3: Greedy Algorithms)
================================================================
An interactive, step-by-step visual lab for three greedy graph algorithms:

    1  Kruskal's MST     (sorted edges + Union-Find / disjoint sets)
    2  Prim's MST        (min-heap priority queue, lazy deletion)
    3  Dijkstra's SSSP   (single-source shortest paths, relaxation)

Run:      python greedy_graph_lab.py
Needs:    pip install pygame-ce        (or: pip install pygame)

Mouse  (graph editor)
    Move mode   drag a node | click a node = set START | click an edge then type
                a number = change its weight | double-click empty space = add node
    + Node      click empty space to add a node
    + Edge      click one node, then another, to connect them
    Delete      click a node or an edge to remove it         (right-click works too)
Keys   SPACE play/pause   LEFT/RIGHT step   UP/DOWN speed   R restart
       1/2/3 switch algorithm   N random graph   G sample graph   ESC quit

How it works
------------
build_*_steps() run the REAL algorithm once and record a snapshot (state of every
node/edge, data-structure contents, the code line being executed, an explanation)
after each meaningful action.  The App then plays the snapshots back with smooth
animation, so you can pause, step forward/backward or drag the progress bar.
"""
import heapq
import math
import os
import random
import re
import sys

import pygame

W, H = 1280, 800
INF = float("inf")

INK = (232, 236, 245)
SOFT = (150, 162, 184)
FAINT = (92, 104, 130)
PANEL = (9, 13, 26)
PANEL_EDGE = (30, 41, 68)
SLATE = (58, 72, 108)
INDIGO = (99, 112, 245)
PINK = (232, 86, 160)
CYAN = (25, 190, 236)
ORANGE = (244, 158, 44)
GREEN = (52, 214, 108)
GOLD = (255, 214, 90)
AMBER_SOFT = (60, 44, 14)

COMP_COLORS = [(99, 112, 245), (232, 86, 160), (25, 190, 236), (244, 158, 44),
               (52, 214, 108), (170, 120, 250), (240, 210, 80), (250, 120, 90),
               (90, 220, 200), (200, 90, 240), (130, 200, 80), (240, 130, 190)]

STAGE = pygame.Rect(16, 96, 744, 558)
STATUS_R = pygame.Rect(776, 96, 488, 112)
DATA_R = pygame.Rect(776, 216, 488, 210)
CODE_R = pygame.Rect(776, 434, 488, 222)
STATS_R = pygame.Rect(776, 666, 488, 118)
CTRL_R = pygame.Rect(16, 666, 744, 118)

ALGOS = {
    "kruskal": dict(
        title="KRUSKAL'S ALGORITHM",
        sub="Sort the edges, then keep every edge that does not close a cycle.",
        badges=(("TIME  O(E log V)", CYAN), ("SPACE  O(V + E)", GREEN),
                ("GREEDY: LIGHTEST EDGE", INDIGO)),
        file="kruskal.py",
        code=["def kruskal(V, E):",
              "    MST, dsu = [], DSU(V)",
              "    for (u, v, w) in sorted(E, key=weight):",
              "        if dsu.find(u) != dsu.find(v):",
              "            dsu.union(u, v)",
              "            MST.append((u, v, w))",
              "        # else: the edge would close a cycle",
              "        if len(MST) == len(V) - 1:",
              "            break",
              "    return MST"]),
    "prim": dict(
        title="PRIM'S ALGORITHM",
        sub="Grow one tree from the start node, always adding the cheapest crossing edge.",
        badges=(("TIME  O(E log V)", CYAN), ("SPACE  O(V + E)", GREEN),
                ("GREEDY: CHEAPEST CUT EDGE", INDIGO)),
        file="prim.py",
        code=["def prim(G, s):",
              "    seen, MST = {s}, []",
              "    pq = [(w, s, v) for v, w in G[s]]; heapify(pq)",
              "    while pq:",
              "        w, u, v = heappop(pq)",
              "        if v in seen: continue",
              "        seen.add(v); MST.append((u, v, w))",
              "        for x, wx in G[v]:",
              "            if x not in seen:",
              "                heappush(pq, (wx, v, x))",
              "    return MST"]),
    "dijkstra": dict(
        title="DIJKSTRA'S ALGORITHM",
        sub="Shortest paths from one source: always settle the closest unsettled node.",
        badges=(("TIME  O((V+E) log V)", CYAN), ("SPACE  O(V)", GREEN),
                ("GREEDY: CLOSEST NODE", INDIGO)),
        file="dijkstra.py",
        code=["def dijkstra(G, s):",
              "    dist = {v: INF for v in G}; dist[s] = 0",
              "    pq = [(0, s)]",
              "    while pq:",
              "        d, u = heappop(pq)",
              "        if d > dist[u]: continue",
              "        for v, w in G[u]:",
              "            if d + w < dist[v]:",
              "                dist[v] = d + w; prev[v] = u",
              "                heappush(pq, (dist[v], v))",
              "    return dist, prev"]),
}
ORDER = ["kruskal", "prim", "dijkstra"]

EDGE_STYLE = {            # colour, width, glow
    "idle": ((64, 78, 116), 2.2, 0.0),
    "cand": ((34, 140, 190), 3.2, 0.2),
    "cmp": (CYAN, 5.0, 1.0),
    "accept": (GREEN, 6.0, 0.6),
    "reject": ((150, 56, 100), 2.0, 0.0),
    "relax": (ORANGE, 5.0, 0.8),
    "skip": ((38, 48, 74), 1.6, 0.0),
    "path": (GOLD, 7.0, 1.0),
}
GROW_STATES = ("accept", "relax", "path")
DASH_STATES = ("reject", "skip")
KEYWORDS = {"def", "if", "else", "while", "return", "for", "in", "not", "continue",
            "break"}
BUILTINS = {"len", "sorted", "heappop", "heappush", "heapify"}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


def lighten(c, f):
    return tuple(min(255, int(v + (255 - v) * f)) for v in c)


def darken(c, f):
    return tuple(max(0, int(v * (1 - f))) for v in c)


_fonts = {}


def font(size, bold=False, mono=False):
    key = (size, bold, mono)
    if key not in _fonts:
        names = "consolas,couriernew,dejavusansmono,monospace" if mono else \
                "segoeui,helveticaneue,arial,dejavusans"
        _fonts[key] = pygame.font.SysFont(names, size, bold=bold)
    return _fonts[key]


def wrap(text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if fnt.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_text(surf, text, pos, size=16, color=INK, bold=False, mono=False,
              center=False, right=False):
    img = font(size, bold, mono).render(text, True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.topright = pos
    else:
        r.topleft = pos
    surf.blit(img, r)
    return r


def glow(surf, center, color, radius, strength):
    if strength <= 0.02 or radius < 4:
        return
    size = int(radius * 2)
    tmp = pygame.Surface((size, size))
    steps = 9
    for i in range(steps):
        r = int(radius * (1 - i / steps))
        k = (i + 1) / steps
        c = tuple(int(v * k * k * strength * 0.55) for v in color)
        pygame.draw.circle(tmp, c, (size // 2, size // 2), r)
    surf.blit(tmp, (center[0] - radius, center[1] - radius),
              special_flags=pygame.BLEND_RGB_ADD)


def name(i):
    return chr(65 + i)


def ename(e):
    return f"{name(e[0])}-{name(e[1])}"


def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


# ----------------------------------------------------------------------------
# graph model
# ----------------------------------------------------------------------------
SAMPLE_POS = [(110, 375), (260, 225), (260, 525), (470, 215), (470, 535), (650, 375)]
SAMPLE_EDGES = [(0, 1, 4), (0, 2, 2), (1, 2, 1), (1, 3, 5), (2, 3, 8), (2, 4, 10),
                (3, 4, 2), (3, 5, 6), (4, 5, 3)]          # same graph as the blog post


class Graph:
    MAX_NODES, MAX_EDGES = 12, 24

    def __init__(self):
        self.pos, self.edges, self.start = [], [], 0
        self.sample()

    def sample(self):
        self.pos = [list(p) for p in SAMPLE_POS]
        self.edges = [list(e) for e in SAMPLE_EDGES]
        self.start = 0

    def random(self, n=None):
        n = n or random.randint(7, 9)
        inner = STAGE.inflate(-120, -130)
        pts = []
        tries = 0
        while len(pts) < n and tries < 4000:
            tries += 1
            p = (random.randint(inner.left, inner.right),
                 random.randint(inner.top + 20, inner.bottom))
            if all(math.dist(p, q) > 105 for q in pts):
                pts.append(p)
        n = len(pts)
        pairs = set()
        for i in range(n):
            near = sorted(range(n), key=lambda j: math.dist(pts[i], pts[j]))[1:3]
            for j in near:
                pairs.add((min(i, j), max(i, j)))
        # make sure the graph is connected
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for i, j in pairs:
            parent[find(i)] = find(j)
        while len({find(i) for i in range(n)}) > 1:
            best = min(((math.dist(pts[i], pts[j]), i, j) for i in range(n)
                        for j in range(i + 1, n) if find(i) != find(j)))
            pairs.add((best[1], best[2]))
            parent[find(best[1])] = find(best[2])
        used = set()
        self.edges = []
        for i, j in sorted(pairs):
            w = max(1, round(math.dist(pts[i], pts[j]) / 16))
            while w in used and w < 99:        # mostly-distinct weights look clearer
                w += 1
            used.add(w)
            self.edges.append([i, j, w])
        self.pos = [list(p) for p in pts]
        self.start = 0

    @property
    def n(self):
        return len(self.pos)

    def has_edge(self, u, v):
        return any({e[0], e[1]} == {u, v} for e in self.edges)

    def add_node(self, x, y):
        if self.n < self.MAX_NODES:
            self.pos.append([x, y])
            return True
        return False

    def add_edge(self, u, v):
        if u == v or self.has_edge(u, v) or len(self.edges) >= self.MAX_EDGES:
            return False
        w = max(1, min(99, round(math.dist(self.pos[u], self.pos[v]) / 16)))
        self.edges.append([min(u, v), max(u, v), w])
        return True

    def del_node(self, i):
        if self.n <= 2:
            return False
        del self.pos[i]
        self.edges = [[u - (u > i), v - (v > i), w] for u, v, w in self.edges
                      if u != i and v != i]
        self.start = min(self.start - (self.start > i), self.n - 1)
        return True


# ----------------------------------------------------------------------------
# the algorithms  ->  snapshots
# ----------------------------------------------------------------------------
class Rec:
    """Records a snapshot of the whole visual state after every action."""

    def __init__(self, n, edges):
        self.n, self.edges = n, edges
        self.nst = ["idle"] * n
        self.est = ["idle"] * len(edges)
        self.edir = [None] * len(edges)
        self.nlab = [None] * n
        self.comp = None
        self.stats = []
        self.info = ""
        self.snaps = []

    def push(self, text, why, line, kind, panel, hold=1.0, burst=()):
        self.snaps.append(dict(
            nst=self.nst[:], est=self.est[:], edir=self.edir[:], nlab=self.nlab[:],
            comp=self.comp[:] if self.comp else None, text=text, why=why,
            line=line, kind=kind, panel=panel, hold=hold, burst=tuple(burst),
            stats=list(self.stats), info=self.info))


def kruskal_steps(g):
    n, E = g.n, g.edges
    r = Rec(n, E)
    order = sorted(range(len(E)), key=lambda i: (E[i][2], i))
    parent, size = list(range(n)), [1] * n
    status = {i: "wait" for i in order}
    r.comp = list(range(n))
    chosen, total = [], 0

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def panel():
        groups = {}
        for v in range(n):
            groups.setdefault(find(v), []).append(v)
        return dict(kind="kruskal", sorted=[(i, status[i]) for i in order],
                    sets=list(groups.items()))

    def stats():
        r.stats = [("MST WEIGHT", total, GREEN), ("EDGES", f"{len(chosen)}/{n - 1}", CYAN)]
        r.info = "MST so far:  " + (",  ".join(ename(E[i]) for i in chosen) or "(none yet)")

    stats()
    r.push("Step 1: sort all edges by weight",
           "Greedy rule: always look at the cheapest remaining edge. Each vertex "
           "starts in its own set (Union-Find).", 3, "info", panel(), hold=1.6)
    for i in order:
        if len(chosen) == n - 1:
            for j in order:
                if status[j] == "wait":
                    status[j] = "skip"
                    r.est[j] = "skip"
            r.push(f"Stop: {n - 1} edges chosen",
                   "A spanning tree has exactly V - 1 edges, so the remaining "
                   "edges can never help.", 8, "info", panel(), hold=1.3)
            break
        u, v, w = E[i]
        ru, rv = find(u), find(v)
        r.est[i] = "cmp"
        status[i] = "cmp"
        r.push(f"Next lightest edge {ename(E[i])}  (weight {w})",
               f"find({name(u)}) = {name(ru)},  find({name(v)}) = {name(rv)}.  "
               + ("Different sets -> safe to add." if ru != rv else
                  "Same set -> adding it would form a cycle."),
               4, "cmp", panel(), hold=1.2)
        if ru != rv:
            if size[ru] < size[rv]:
                ru, rv = rv, ru
            parent[rv] = ru
            size[ru] += size[rv]
            r.comp = [find(x) for x in range(n)]
            r.est[i] = "accept"
            r.edir[i] = u
            status[i] = "accept"
            chosen.append(i)
            total += w
            stats()
            r.push(f"Accept {ename(E[i])}  ->  union the two sets",
                   "The edge joins two different components, so the two sets "
                   "merge into one (union by size).", 5, "take", panel(),
                   hold=1.3, burst=(u, v))
        else:
            r.est[i] = "reject"
            status[i] = "reject"
            stats()
            r.push(f"Reject {ename(E[i])}  ->  cycle",
                   "Both endpoints are already connected through other chosen "
                   "edges, so this edge is skipped.", 7, "reject", panel(), hold=1.1)
    ok = len(chosen) == n - 1
    r.push(f"Done: total weight {total}" + ("" if ok else "  (graph is disconnected "
                                              "- this is a spanning FOREST)"),
           "Kruskal's result is a minimum spanning tree. Time O(E log V), "
           "dominated by sorting the edges.", 10, "done", panel(), hold=2.0,
           burst=range(n))
    return r.snaps


def prim_steps(g):
    n, E, s = g.n, g.edges, g.start
    r = Rec(n, E)
    adj = [[] for _ in range(n)]
    for i, (u, v, w) in enumerate(E):
        adj[u].append((v, w, i))
        adj[v].append((u, w, i))
    seen = {s}
    heap = []
    chosen, total = [], 0

    def panel(popped=None):
        items = sorted(heap)
        return dict(kind="prim", pq=[(w, e, u, v, v in seen) for w, e, u, v in items],
                    popped=popped, tree=sorted(seen))

    def stats():
        r.stats = [("MST WEIGHT", total, GREEN), ("TREE NODES", f"{len(seen)}/{n}", CYAN)]
        r.info = "Tree edges:  " + (",  ".join(ename(E[i]) for i in chosen) or "(none yet)")

    for v, w, e in adj[s]:
        heapq.heappush(heap, (w, e, s, v))
        r.est[e] = "cand"
    r.nst[s] = "tree"
    stats()
    r.push(f"Start at {name(s)}: put its edges in the priority queue",
           "The queue always holds the edges that leave the tree. The cheapest "
           "one is on top.", 3, "info", panel(), hold=1.6, burst=(s,))
    while heap:
        w, e, u, v = heapq.heappop(heap)
        r.est[e] = "cmp"
        r.push(f"Extract-min: edge {name(u)}-{name(v)}  (weight {w})",
               "heappop returns the lightest entry in the queue.", 5, "cmp",
               panel(popped=(w, e, u, v)), hold=1.1)
        if v in seen:
            r.est[e] = "reject"
            r.push(f"{name(v)} is already in the tree  ->  skip",
                   "This is a stale entry (lazy deletion): the edge was pushed "
                   "before its far end joined the tree.", 6, "reject",
                   panel(), hold=1.0)
            continue
        seen.add(v)
        r.est[e] = "accept"
        r.edir[e] = u
        r.nst[v] = "tree"
        chosen.append(e)
        total += w
        stats()
        r.push(f"Add {name(v)} to the tree via {name(u)}-{name(v)}",
               "Cut property: the lightest edge leaving the tree is always safe.",
               7, "take", panel(), hold=1.3, burst=(v,))
        pushed = 0
        for x, wx, e2 in adj[v]:
            if x not in seen:
                heapq.heappush(heap, (wx, e2, v, x))
                if r.est[e2] == "idle":
                    r.est[e2] = "cand"
                pushed += 1
        if pushed:
            r.push(f"Push the {pushed} new edge(s) leaving {name(v)}",
                   "Only edges that lead outside the tree are added to the queue.",
                   10, "info", panel(), hold=1.0)
    ok = len(seen) == n
    r.push(f"Done: total weight {total}" + ("" if ok else "  (graph is disconnected - "
                                              "only the start component was reached)"),
           "Queue is empty. Binary heap: O(E log V). With an adjacency matrix and "
           "no heap it is O(V^2).", 11, "done", panel(), hold=2.0, burst=range(n))
    return r.snaps


def dijkstra_steps(g):
    n, E, s = g.n, g.edges, g.start
    r = Rec(n, E)
    adj = [[] for _ in range(n)]
    for i, (u, v, w) in enumerate(E):
        adj[u].append((v, w, i))
        adj[v].append((u, w, i))
    dist = [INF] * n
    prev = [None] * n          # (node, edge)
    done = []
    heap = [(0, s)]
    dist[s] = 0
    relax_count = 0

    def lab(v):
        return "inf" if dist[v] == INF else str(dist[v])

    def panel():
        return dict(kind="dijkstra", dist=dist[:], prev=[p[0] if p else None for p in prev],
                    state=r.nst[:], pq=[(d, v, d > dist[v]) for d, v in sorted(heap)],
                    start=s)

    def stats():
        r.stats = [("SETTLED", f"{len(done)}/{n}", GREEN), ("RELAXATIONS", relax_count, CYAN)]
        r.info = "Settled order:  " + (" > ".join(name(v) for v in done) or "(none yet)")

    for v in range(n):
        r.nlab[v] = lab(v)
    r.nst[s] = "seen"
    stats()
    r.push(f"Source = {name(s)}:  dist[{name(s)}] = 0,  all others = infinity",
           "dist[v] is the best known distance so far. The priority queue picks "
           "the closest node that is not yet settled.", 2, "info", panel(),
           hold=1.6, burst=(s,))
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            r.push(f"Skip stale entry ({d}, {name(u)})",
                   f"A shorter path to {name(u)} ({dist[u]}) was found after this "
                   "entry was pushed (lazy deletion).", 6, "reject", panel(), hold=0.9)
            continue
        r.nst[u] = "current"
        r.push(f"Extract-min: settle {name(u)}  (dist = {d})",
               "No unsettled node is closer, and weights are non-negative, so "
               f"{d} is the final shortest distance to {name(u)}.", 5, "cmp",
               panel(), hold=1.2)
        for v, w, e in adj[u]:
            if v in done:
                continue
            relax_count += 1
            r.est[e] = "cmp"
            old = prev[v]
            better = d + w < dist[v]
            stats()
            r.push(f"Relax {name(u)} -> {name(v)}:  {d} + {w} = {d + w}   "
                   f"(current dist[{name(v)}] = {lab(v)})",
                   f"Is going through {name(u)} shorter?  "
                   + ("Yes, update." if better else "No, keep the old distance."),
                   8, "cmp", panel(), hold=1.1)
            if better:
                dist[v] = d + w
                prev[v] = (u, e)
                r.nlab[v] = lab(v)
                if r.nst[v] == "idle":
                    r.nst[v] = "seen"
                if old:
                    r.est[old[1]] = "reject"
                r.est[e] = "relax"
                r.edir[e] = u
                heapq.heappush(heap, (dist[v], v))
                r.push(f"dist[{name(v)}] = {dist[v]}   (via {name(u)})",
                       "Distance improved: remember the parent and push the new "
                       "distance into the queue.", 9, "take", panel(), hold=1.0,
                       burst=(v,))
            else:
                r.est[e] = "reject"
                r.push(f"No improvement for {name(v)}",
                       "The old path is at least as short, so nothing changes.",
                       8, "reject", panel(), hold=0.8)
        done.append(u)
        r.nst[u] = "done"
        if prev[u]:
            r.est[prev[u][1]] = "accept"
        stats()
        r.push(f"{name(u)} is settled  (final distance {lab(u)})",
               "All edges out of the node are relaxed; its distance never changes again.",
               6, "done", panel(), hold=1.0, burst=(u,))
    r.push("Done: shortest-path tree complete",
           "Click any node to trace its shortest path from the source. "
           "O((V + E) log V) with a binary heap; edge weights must not be negative.",
           11, "done", panel(), hold=2.0, burst=range(n))
    return r.snaps


BUILDERS = {"kruskal": kruskal_steps, "prim": prim_steps, "dijkstra": dijkstra_steps}


# ----------------------------------------------------------------------------
# the visual app
# ----------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label, action, mode=None):
        self.rect = pygame.Rect(rect)
        self.label, self.action, self.mode = label, action, mode
        self.hover = 0.0


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Greedy Graph Lab - DAA CIA 3(b)")
        try:
            self.screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.speeds = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
        self.speed_i = 2
        self.g = Graph()
        self.algo = "kruskal"
        self.mode = "move"
        self.t = 0.0
        self.playing = False
        self.drag = None            # (node, moved)
        self.edge_from = None
        self.sel_edge = None
        self.wbuf = ""
        self.trace = None
        self.last_click = (0, (0, 0))
        self.scrubbing = False
        self.particles = []
        self.scrub_rect = pygame.Rect(36, 674, 676, 28)
        self.tab_rects = {}
        self.make_background()
        self.make_buttons()
        self.make_code()
        self.rebuild()

    # ---------- build ----------
    def rebuild(self):
        self.snaps = BUILDERS[self.algo](self.g)
        self.step = 0
        self.hold_t = 0.0
        self.playing = False
        self.trace = None
        self.particles = []
        self.init_display()
        self.make_code()

    def init_display(self):
        n, m = self.g.n, len(self.g.edges)
        snap = self.snaps[0]
        self.nc = [list(self.node_target(i, snap)[0]) for i in range(n)]
        self.ng = [self.node_target(i, snap)[1] for i in range(n)]
        self.ec = [list(EDGE_STYLE[snap["est"][i]][0]) for i in range(m)]
        self.ew = [EDGE_STYLE[snap["est"][i]][1] for i in range(m)]
        self.eg = [EDGE_STYLE[snap["est"][i]][2] for i in range(m)]
        self.ep = [0.0] * m

    def make_background(self):
        bg = pygame.Surface((W, H))
        for y in range(H):
            pygame.draw.line(bg, mix((4, 6, 13), (9, 14, 30), y / H), (0, y), (W, y))
        for gx in range(0, W, 32):
            for gy in range(0, H, 32):
                bg.set_at((gx, gy), (22, 30, 52))
        glow(bg, STAGE.center, (22, 50, 110), 360, 0.8)
        for rect in (STAGE, STATUS_R, DATA_R, CODE_R, STATS_R, CTRL_R):
            pygame.draw.rect(bg, PANEL, rect, border_radius=14)
            pygame.draw.rect(bg, PANEL_EDGE, rect, 1, border_radius=14)
        # stage grid
        inner = STAGE.inflate(-2, -2)
        for gx in range(inner.left + 20, inner.right, 40):
            for gy in range(inner.top + 20, inner.bottom, 40):
                bg.set_at((gx, gy), (26, 36, 62))
        self.bg = bg

    def make_code(self):
        f = font(13, mono=True)
        self.code_lines = []
        for text in ALGOS[self.algo]["code"]:
            surf = pygame.Surface((440, 20), pygame.SRCALPHA)
            x = 0
            for tok in re.findall(r"\w+|\s+|#.*|.", text):
                if tok.startswith("#"):
                    col = FAINT
                elif tok in KEYWORDS:
                    col = (150, 130, 255)
                elif tok in BUILTINS or tok == "INF":
                    col = (95, 200, 235)
                elif tok.isdigit():
                    col = ORANGE
                elif text.startswith("def") and tok in ("kruskal", "prim", "dijkstra"):
                    col = (110, 215, 160)
                else:
                    col = (205, 212, 228)
                img = f.render(tok, True, col)
                surf.blit(img, (x, 1))
                x += img.get_width()
            self.code_lines.append(surf)

    def make_buttons(self):
        B = self.buttons = []

        def add(x, y, w, h, label, action, mode=None):
            B.append(Button((x, y, w, h), label, action, mode))
        add(36, 702, 96, 32, "Prev", lambda: self.go(-1))
        add(140, 702, 116, 32, "Play", self.toggle)
        add(264, 702, 96, 32, "Next", lambda: self.go(1))
        add(368, 702, 100, 32, "Restart", self.restart)
        add(530, 706, 28, 26, "-", lambda: self.change_speed(-1))
        add(626, 706, 28, 26, "+", lambda: self.change_speed(1))
        add(36, 744, 84, 30, "Move", lambda: self.set_mode("move"), "move")
        add(126, 744, 92, 30, "+ Node", lambda: self.set_mode("node"), "node")
        add(224, 744, 92, 30, "+ Edge", lambda: self.set_mode("edge"), "edge")
        add(322, 744, 88, 30, "Delete", lambda: self.set_mode("delete"), "delete")
        add(448, 744, 130, 30, "Sample graph", self.load_sample)
        add(586, 744, 136, 30, "Random graph", self.load_random)

    # ---------- actions ----------
    def toggle(self):
        if self.step >= len(self.snaps) - 1:
            self.restart()
        self.playing = not self.playing
        self.hold_t = 0.0

    def restart(self):
        self.step, self.hold_t, self.playing, self.trace = 0, 0.0, False, None

    def go(self, d):
        self.playing = False
        self.set_step(self.step + d)

    def set_step(self, i):
        i = max(0, min(len(self.snaps) - 1, i))
        forward = i > self.step
        self.step, self.hold_t = i, 0.0
        if i < len(self.snaps) - 1:
            self.trace = None
        if forward:
            self.spawn_burst(self.snaps[i])

    def change_speed(self, d):
        self.speed_i = max(0, min(len(self.speeds) - 1, self.speed_i + d))

    def set_mode(self, m):
        self.mode, self.edge_from, self.sel_edge, self.wbuf = m, None, None, ""

    def set_algo(self, a):
        if a != self.algo:
            self.algo = a
            self.rebuild()

    def load_sample(self):
        self.g.sample()
        self.rebuild()

    def load_random(self):
        self.g.random()
        self.rebuild()

    def edited(self):
        self.rebuild()

    # ---------- visual targets ----------
    def node_target(self, i, snap):
        st = snap["nst"][i]
        comp = snap["comp"]
        if comp is not None:
            col = COMP_COLORS[comp[i] % len(COMP_COLORS)]
            return col, 0.5 if comp.count(comp[i]) > 1 else 0.0
        return {"idle": (SLATE, 0.0), "seen": (mix(SLATE, CYAN, 0.55), 0.35),
                "tree": (GREEN, 0.6), "current": (ORANGE, 1.0),
                "done": (GREEN, 0.5)}[st]

    def spawn_burst(self, snap):
        for i in snap["burst"]:
            if i >= self.g.n:
                continue
            x, y = self.g.pos[i]
            for _ in range(9):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(40, 150)
                self.particles.append([x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                                       random.uniform(0.4, 0.8)])

    # ---------- update ----------
    def update(self, dt):
        self.t += dt
        snap = self.snaps[self.step]
        speed = self.speeds[self.speed_i]
        if self.playing:
            self.hold_t += dt
            if self.hold_t >= 0.7 * snap["hold"] / speed:
                if self.step >= len(self.snaps) - 1:
                    self.playing = False
                else:
                    self.set_step(self.step + 1)
        k = 1 - math.exp(-dt * 9 * max(1.0, speed ** 0.7))
        for i in range(self.g.n):
            col, gl = self.node_target(i, snap)
            for c in range(3):
                self.nc[i][c] += (col[c] - self.nc[i][c]) * k
            self.ng[i] += (gl - self.ng[i]) * k
        for i in range(len(self.g.edges)):
            st = self.effective_edge_state(i, snap)
            col, w, gl = EDGE_STYLE[st]
            for c in range(3):
                self.ec[i][c] += (col[c] - self.ec[i][c]) * k
            self.ew[i] += (w - self.ew[i]) * k
            self.eg[i] += (gl - self.eg[i]) * k
            tgt = 1.0 if st in GROW_STATES else 0.0
            self.ep[i] += (tgt - self.ep[i]) * (1 - math.exp(-dt * 6 * max(1.0, speed ** 0.6)))
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 240 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        mp = pygame.mouse.get_pos()
        for b in self.buttons:
            b.hover += ((1.0 if b.rect.collidepoint(mp) else 0.0) - b.hover) * min(1, dt * 14)

    # ---------- drawing: stage ----------
    def effective_edge_state(self, i, snap):
        if self.trace is not None and snap is self.snaps[-1] and self.algo == "dijkstra":
            return "path" if i in self.trace_edges else "idle"
        return snap["est"][i]

    def draw(self):
        s = self.screen
        s.blit(self.bg, (0, 0))
        snap = self.snaps[self.step]
        self.draw_header(s)
        self.draw_stage(s, snap)
        self.draw_status(s, snap)
        self.draw_data(s, snap)
        self.draw_code(s, snap)
        self.draw_controls(s)
        self.draw_stats(s, snap)
        pygame.display.flip()

    def draw_header(self, s):
        a = ALGOS[self.algo]
        draw_text(s, a["title"], (22, 12), 38, INK, bold=True)
        draw_text(s, a["sub"], (26, 62), 15, SOFT)
        x = 740
        self.tab_rects = {}
        for k, key in enumerate(ORDER):
            lab = f"{k + 1}  {key.upper()}"
            w = font(13, True).size(lab)[0] + 28
            r = pygame.Rect(x, 22, w, 28)
            on = key == self.algo
            col = CYAN if on else FAINT
            pygame.draw.rect(s, mix(PANEL, col, 0.22 if on else 0.05), r, border_radius=14)
            pygame.draw.rect(s, col, r, 1, border_radius=14)
            draw_text(s, lab, r.center, 13, INK if on else SOFT, bold=True, center=True)
            self.tab_rects[key] = r
            x += w + 8
        x = 740
        for label, col in a["badges"]:
            w = font(12, True).size(label)[0] + 22
            r = pygame.Rect(x, 58, w, 22)
            pygame.draw.rect(s, mix(PANEL, col, 0.14), r, border_radius=11)
            pygame.draw.rect(s, col, r, 1, border_radius=11)
            draw_text(s, label, r.center, 12, col, bold=True, center=True)
            x += w + 8

    def edge_pts(self, i):
        u, v, w = self.g.edges[i]
        return self.g.pos[u], self.g.pos[v]

    def draw_stage(self, s, snap):
        g = self.g
        clip = s.get_clip()
        s.set_clip(STAGE.inflate(-2, -2))
        n = g.n
        # edges
        order = sorted(range(len(g.edges)),
                       key=lambda i: snap["est"][i] in ("accept", "path", "cmp", "relax"))
        for i in order:
            a, b = self.edge_pts(i)
            st = self.effective_edge_state(i, snap)
            col = tuple(int(c) for c in self.ec[i])
            width = max(1, int(round(self.ew[i])))
            gl = self.eg[i]
            if st in DASH_STATES:
                self.dashed(s, col, a, b, 2)
            else:
                if gl > 0.05:
                    pygame.draw.line(s, mix(PANEL, col, 0.28 * gl), a, b, width + 9)
                p = self.ep[i]
                if st in GROW_STATES and p < 0.97:
                    pygame.draw.line(s, EDGE_STYLE["idle"][0], a, b, 2)
                    d = snap["edir"][i]
                    start = a if d == g.edges[i][0] else b
                    end = b if start is a else a
                    q = (start[0] + (end[0] - start[0]) * p, start[1] + (end[1] - start[1]) * p)
                    pygame.draw.line(s, col, start, q, width)
                    pygame.draw.circle(s, (255, 255, 255), (int(q[0]), int(q[1])), 4)
                else:
                    pygame.draw.line(s, col, a, b, width)
                if st in ("accept", "path") and p > 0.9:
                    d = snap["edir"][i]
                    start = a if d == g.edges[i][0] else b
                    end = b if start is a else a
                    for k in range(2):
                        t = (self.t * 0.55 + k * 0.5 + i * 0.13) % 1
                        q = (start[0] + (end[0] - start[0]) * t,
                             start[1] + (end[1] - start[1]) * t)
                        pygame.draw.circle(s, lighten(col, 0.7), (int(q[0]), int(q[1])), 3)
            if st == "cmp":
                pulse = 0.5 + 0.5 * math.sin(self.t * 8)
                pygame.draw.line(s, mix(col, (255, 255, 255), 0.4 * pulse), a, b, 2)
        # weight tags
        for i, (u, v, w) in enumerate(g.edges):
            a, b = self.edge_pts(i)
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            txt = str(w)
            editing = self.sel_edge == i and self.wbuf
            if editing:
                txt = self.wbuf + "_"
            tw = max(26, font(13, True).size(txt)[0] + 14)
            r = pygame.Rect(0, 0, tw, 20)
            r.center = (mx, my)
            sel = self.sel_edge == i
            pygame.draw.rect(s, (28, 52, 80) if sel else AMBER_SOFT, r, border_radius=6)
            pygame.draw.rect(s, CYAN if sel else (110, 80, 24), r, 1, border_radius=6)
            draw_text(s, txt, r.center, 13, CYAN if sel else ORANGE, bold=True, center=True)
        # nodes
        for i in range(n):
            self.draw_node(s, i, snap)
        # edge-in-progress line
        if self.mode == "edge" and self.edge_from is not None:
            pygame.draw.line(s, CYAN, g.pos[self.edge_from], pygame.mouse.get_pos(), 2)
        for p in self.particles:
            c = tuple(int(v * max(0, min(1, p[4] / 0.5))) for v in GREEN)
            pygame.draw.circle(s, c, (int(p[0]), int(p[1])), 2)
        s.set_clip(clip)
        hints = {"move": "drag nodes  |  click node = START  |  click edge + type = weight  |  "
                         "double-click empty = add node  |  right-click = delete",
                 "node": "click empty space to add a node  (max 12)",
                 "edge": "click a node, then another node, to connect them  (max 24 edges)",
                 "delete": "click a node or an edge to delete it"}[self.mode]
        draw_text(s, hints, (STAGE.x + 16, STAGE.bottom - 22), 12, FAINT)
        if self.algo == "dijkstra" and self.step == len(self.snaps) - 1 and self.trace is None:
            draw_text(s, "click a node to trace its shortest path", (STAGE.right - 16,
                      STAGE.y + 14), 13, GOLD, right=True)

    def dashed(self, s, col, a, b, w):
        L = math.dist(a, b)
        if L < 1:
            return
        n = int(L // 12)
        for k in range(n + 1):
            t0, t1 = k * 12 / L, min(1, (k * 12 + 6) / L)
            if t0 >= 1:
                break
            p0 = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            p1 = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            pygame.draw.line(s, col, p0, p1, w)

def _draw_node(self, s, i, snap):
    g = self.g
    x, y = g.pos[i]
    col = tuple(int(c) for c in self.nc[i])
    gl = self.ng[i]
    if gl > 0.03:
        glow(s, (x, y), col, 52, gl)
    r = 21
    pygame.draw.circle(s, darken(col, 0.5), (x + 2, y + 3), r)
    pygame.draw.circle(s, col, (x, y), r)
    pygame.draw.circle(s, lighten(col, 0.45), (x, y), r, 2)
    pygame.draw.circle(s, lighten(col, 0.25), (x - 6, y - 7), 5)
    draw_text(s, name(i), (x, y + 1), 18, (255, 255, 255), bold=True, center=True)
    if i == g.start and self.algo != "kruskal":
        pulse = 0.5 + 0.5 * math.sin(self.t * 4)
        pygame.draw.circle(s, mix(GOLD, (255, 255, 255), 0.3 * pulse), (x, y), r + 6, 2)
        draw_text(s, "START", (x, y + r + 12), 10, GOLD, bold=True, center=True)
    if self.mode == "edge" and self.edge_from == i:
        pygame.draw.circle(s, CYAN, (x, y), r + 6, 2)
    lab = snap["nlab"][i]
    if lab is not None and self.algo == "dijkstra":
        txt = "inf" if lab == "inf" else lab
        w = max(30, font(13, True).size(txt)[0] + 14)
        rr = pygame.Rect(0, 0, w, 20)
        rr.center = (x, y - r - 16)
        c = CYAN if lab != "inf" else FAINT
        pygame.draw.rect(s, mix(PANEL, c, 0.16), rr, border_radius=6)
        pygame.draw.rect(s, c, rr, 1, border_radius=6)
        draw_text(s, txt if txt != "inf" else "∞", rr.center, 13, c, bold=True, center=True)


App.draw_node = lambda self, s, i, snap: _draw_node(self, s, i, snap)


# ---------------------------------------------------------------------------
# panels
# ---------------------------------------------------------------------------
def chip(s, rect, text, col, filled=False, size=12, fcol=None):
    pygame.draw.rect(s, mix(PANEL, col, 0.32 if filled else 0.12), rect, border_radius=7)
    pygame.draw.rect(s, col, rect, 1, border_radius=7)
    draw_text(s, text, rect.center, size, fcol or INK, bold=True, center=True)


def _draw_status(self, s, snap):
    r = STATUS_R
    kc = {"cmp": CYAN, "take": GREEN, "done": GREEN, "reject": PINK,
          "info": INK}[snap["kind"]]
    pygame.draw.rect(s, kc, (r.x, r.y + 14, 3, 56))
    y = r.y + 12
    for line in wrap(snap["text"], font(19, True), r.width - 44)[:2]:
        draw_text(s, line, (r.x + 22, y), 19, kc, bold=True)
        y += 25
    why = snap["why"]
    if self.trace is not None and self.step == len(self.snaps) - 1 and self.algo == "dijkstra":
        why = self.trace_text
    y = r.y + 66 if len(wrap(snap["text"], font(19, True), r.width - 44)) > 1 else r.y + 48
    for line in wrap(why, font(14), r.width - 44)[:3]:
        draw_text(s, line, (r.x + 22, y), 14, SOFT if self.trace is None else GOLD)
        y += 19


def _draw_data(self, s, snap):
    r = DATA_R
    p = snap["panel"]
    if p["kind"] == "kruskal":
        draw_text(s, "SORTED EDGES   (waiting > checked)", (r.x + 18, r.y + 10), 11, FAINT, bold=True)
        cols, cw, ch = 7, 62, 24
        colmap = {"wait": SLATE, "cmp": CYAN, "accept": GREEN, "reject": PINK, "skip": (50, 60, 88)}
        for k, (i, st) in enumerate(p["sorted"]):
            e = self.g.edges[i]
            rr = pygame.Rect(r.x + 18 + (k % cols) * (cw + 6), r.y + 30 + (k // cols) * (ch + 6), cw, ch)
            chip(s, rr, f"{ename(e)} {e[2]}", colmap[st], st in ("cmp", "accept"), 11,
                 FAINT if st == "skip" else None)
        rows = (len(p["sorted"]) + cols - 1) // cols
        y = r.y + 30 + rows * (ch + 6) + 10
        draw_text(s, "DISJOINT SETS  (Union-Find)", (r.x + 18, y), 11, FAINT, bold=True)
        y += 20
        x = r.x + 18
        for root, members in p["sets"]:
            col = COMP_COLORS[root % len(COMP_COLORS)]
            txt = "{" + ",".join(name(m) for m in members) + "}"
            w = font(13, True, True).size(txt)[0] + 18
            if x + w > r.right - 14:
                x, y = r.x + 18, y + 30
            rr = pygame.Rect(x, y, w, 24)
            chip(s, rr, txt, col, True, 13)
            x += w + 8
    elif p["kind"] == "prim":
        draw_text(s, "PRIORITY QUEUE   (min at the left)", (r.x + 18, r.y + 10), 11, FAINT, bold=True)
        x, y = r.x + 18, r.y + 30
        if p["popped"]:
            w, e, u, v = p["popped"]
            rr = pygame.Rect(x, y, 80, 26)
            chip(s, rr, f"{name(u)}-{name(v)}  {w}", ORANGE, True, 12)
            draw_text(s, "popped", (x + 40, y + 36), 10, ORANGE, bold=True, center=True)
            x += 96
        for w, e, u, v, stale in p["pq"]:
            if x + 80 > r.right - 14:
                x, y = r.x + 18, y + 32
                if y > r.y + 96:
                    draw_text(s, "...", (x, y), 14, FAINT)
                    break
            rr = pygame.Rect(x, y, 80, 26)
            chip(s, rr, f"{name(u)}-{name(v)}  {w}", FAINT if stale else CYAN, False, 12,
                 FAINT if stale else None)
            x += 88
        if not p["pq"] and not p["popped"]:
            draw_text(s, "(empty)", (r.x + 18, r.y + 34), 13, FAINT)
        draw_text(s, "greyed entries are stale (far end already in the tree)",
                  (r.x + 18, r.y + 118), 11, FAINT)
        draw_text(s, "NODES IN TREE", (r.x + 18, r.y + 144), 11, FAINT, bold=True)
        x = r.x + 18
        for v in p["tree"]:
            rr = pygame.Rect(x, r.y + 164, 30, 26)
            chip(s, rr, name(v), GREEN, True, 13)
            x += 36
    else:
        draw_text(s, "DISTANCE TABLE   (node, dist, parent)", (r.x + 18, r.y + 10), 11, FAINT, bold=True)
        cols, cw, ch = 6, 71, 50
        for v in range(self.g.n):
            st = p["state"][v]
            col = {"idle": SLATE, "seen": CYAN, "current": ORANGE, "done": GREEN}[st]
            rr = pygame.Rect(r.x + 18 + (v % cols) * (cw + 6), r.y + 30 + (v // cols) * (ch + 6), cw, ch)
            pygame.draw.rect(s, mix(PANEL, col, 0.28 if st == "current" else 0.12), rr, border_radius=8)
            pygame.draw.rect(s, col, rr, 1, border_radius=8)
            d = p["dist"][v]
            draw_text(s, name(v), (rr.x + 9, rr.y + 5), 13, INK, bold=True)
            draw_text(s, "∞" if d == INF else str(d), (rr.right - 8, rr.y + 3), 17, col, bold=True, right=True)
            pv = p["prev"][v]
            draw_text(s, "from " + (name(pv) if pv is not None else "-"), (rr.x + 9, rr.y + 30), 11, SOFT)
        y = r.y + 30 + ((self.g.n + cols - 1) // cols) * (ch + 6) + 8
        draw_text(s, "PRIORITY QUEUE  (dist, node)", (r.x + 18, y), 11, FAINT, bold=True)
        y += 18
        x = r.x + 18
        for d, v, stale in p["pq"][:10]:
            rr = pygame.Rect(x, y, 56, 24)
            chip(s, rr, f"{d},{name(v)}", FAINT if stale else CYAN, False, 12,
                 FAINT if stale else None)
            x += 62
        if not p["pq"]:
            draw_text(s, "(empty)", (r.x + 18, y + 3), 13, FAINT)


def _draw_code(self, s, snap):
    r = CODE_R
    a = ALGOS[self.algo]
    draw_text(s, a["file"], (r.x + 18, r.y + 9), 13, SOFT, mono=True)
    for k, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        pygame.draw.circle(s, c, (r.right - 70 + k * 18, r.y + 18), 5)
    pygame.draw.line(s, PANEL_EDGE, (r.x, r.y + 34), (r.right, r.y + 34))
    lh = 15.6
    top = r.y + 42
    for i, surf in enumerate(self.code_lines):
        y = top + i * lh
        if snap["line"] == i + 1:
            hl = pygame.Rect(r.x + 6, y - 2, r.width - 12, lh + 1)
            pulse = 0.75 + 0.25 * math.sin(self.t * 5)
            pygame.draw.rect(s, mix(PANEL, GREEN, 0.22 * pulse), hl, border_radius=3)
            pygame.draw.rect(s, GREEN, (hl.x, hl.y, 3, hl.height))
        draw_text(s, str(i + 1), (r.x + 30, y), 11, FAINT, mono=True, right=True)
        s.blit(surf, (r.x + 44, y - 1))


def _draw_controls(self, s):
    bar = pygame.Rect(36, 684, 676, 8)
    pygame.draw.rect(s, (24, 32, 56), bar, border_radius=4)
    frac = self.step / max(1, len(self.snaps) - 1)
    fill = pygame.Rect(bar.x, bar.y, int(bar.width * frac), bar.height)
    pygame.draw.rect(s, CYAN, fill, border_radius=4)
    pygame.draw.circle(s, (255, 255, 255), (fill.right, bar.centery), 7)
    glow(s, (fill.right, bar.centery), CYAN, 18, 0.9)
    for b in self.buttons:
        label = b.label
        if label == "Play":
            label = "Pause" if self.playing else ("Replay" if self.step >= len(self.snaps) - 1 else "Play")
        primary = b.label == "Play"
        active = b.mode is not None and b.mode == self.mode
        tint = CYAN if (primary or active) else INDIGO
        base = mix(PANEL, tint, 0.26 if (primary or active) else 0.1)
        col = mix(base, lighten(base, 0.12), b.hover)
        pygame.draw.rect(s, col, b.rect, border_radius=8)
        pygame.draw.rect(s, CYAN if (primary or active) else mix(PANEL_EDGE, CYAN, b.hover),
                         b.rect, 1, border_radius=8)
        draw_text(s, label, b.rect.center, 14, INK, bold=True, center=True)
    draw_text(s, "Speed", (480, 711), 13, SOFT)
    draw_text(s, f"{self.speeds[self.speed_i]:g}x", (590, 719), 14, INK, bold=True, center=True)


def _draw_stats(self, s, snap):
    r = STATS_R
    draw_text(s, snap["info"], (r.x + 20, r.y + 12), 14, SOFT)
    stats = list(snap["stats"]) + [("STEP", f"{self.step + 1}/{len(self.snaps)}", ORANGE)]
    for k, (label, val, col) in enumerate(stats):
        cx = r.x + 20 + k * 160
        draw_text(s, label, (cx, r.y + 50), 11, FAINT, bold=True)
        draw_text(s, str(val), (cx, r.y + 68), 28, col, bold=True, mono=True)


App.draw_status = _draw_status
App.draw_data = _draw_data
App.draw_code = _draw_code
App.draw_controls = _draw_controls
App.draw_stats = _draw_stats


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------
def _node_at(self, p):
    for i in range(self.g.n - 1, -1, -1):
        if math.dist(p, self.g.pos[i]) <= 25:
            return i
    return None


def _edge_at(self, p):
    best, bi = 9, None
    for i in range(len(self.g.edges)):
        a, b = self.edge_pts(i)
        d = seg_dist(p, a, b)
        if d < best:
            best, bi = d, i
    return bi


def _compute_trace(self, v):
    snap = self.snaps[-1]
    prev = snap["panel"]["prev"]
    dist = snap["panel"]["dist"]
    if dist[v] == INF:
        self.trace, self.trace_edges = v, set()
        self.trace_text = f"{name(v)} is unreachable from {name(self.g.start)}: distance = infinity."
        return
    path, edges = [v], set()
    while prev[path[-1]] is not None:
        u = path[-1]
        p = prev[u]
        for i, e in enumerate(self.g.edges):
            if {e[0], e[1]} == {u, p}:
                edges.add(i)
        path.append(p)
    path.reverse()
    self.trace, self.trace_edges = v, edges
    self.trace_text = (f"Shortest path {name(self.g.start)} -> {name(v)}:  "
                       + "  >  ".join(name(x) for x in path) + f"     (total cost {dist[v]})")


def _handle(self, ev):
    if ev.type == pygame.QUIT:
        return False
    if ev.type == pygame.KEYDOWN:
        if self.sel_edge is not None:
            if ev.key == pygame.K_ESCAPE:
                self.sel_edge, self.wbuf = None, ""
                return True
            if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.wbuf:
                    self.g.edges[self.sel_edge][2] = max(1, min(99, int(self.wbuf)))
                    self.sel_edge, self.wbuf = None, ""
                    self.edited()
                else:
                    self.sel_edge = None
                return True
            if ev.key == pygame.K_BACKSPACE:
                self.wbuf = self.wbuf[:-1]
                return True
            if ev.unicode and ev.unicode.isdigit() and len(self.wbuf) < 2:
                self.wbuf += ev.unicode
                return True
        k = ev.key
        if k == pygame.K_ESCAPE:
            return False
        if k == pygame.K_SPACE:
            self.toggle()
        elif k == pygame.K_RIGHT:
            self.go(1)
        elif k == pygame.K_LEFT:
            self.go(-1)
        elif k == pygame.K_UP:
            self.change_speed(1)
        elif k == pygame.K_DOWN:
            self.change_speed(-1)
        elif k == pygame.K_r:
            self.restart()
        elif k == pygame.K_n:
            self.load_random()
        elif k == pygame.K_g:
            self.load_sample()
        elif k in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.set_algo(ORDER[k - pygame.K_1])
    elif ev.type == pygame.MOUSEBUTTONDOWN:
        p = ev.pos
        if ev.button == 1:
            for key, rr in self.tab_rects.items():
                if rr.collidepoint(p):
                    self.set_algo(key)
                    return True
            for b in self.buttons:
                if b.rect.collidepoint(p):
                    b.action()
                    return True
            if self.scrub_rect.collidepoint(p):
                self.scrubbing = True
                self.scrub(p[0])
                return True
            if STAGE.collidepoint(p):
                self.stage_click(p)
        elif ev.button == 3 and STAGE.collidepoint(p):
            n = self.node_at(p)
            if n is not None:
                if self.g.del_node(n):
                    self.edited()
            else:
                e = self.edge_at(p)
                if e is not None:
                    del self.g.edges[e]
                    self.edited()
    elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
        self.scrubbing = False
        if self.drag is not None:
            node, moved = self.drag
            self.drag = None
            if not moved and self.mode == "move" and self.algo != "kruskal":
                self.g.start = node
                self.edited()
            elif moved:
                self.trace = None
    elif ev.type == pygame.MOUSEMOTION:
        if self.scrubbing:
            self.scrub(ev.pos[0])
        elif self.drag is not None:
            node, _ = self.drag
            x = max(STAGE.left + 30, min(STAGE.right - 30, ev.pos[0]))
            y = max(STAGE.top + 50, min(STAGE.bottom - 40, ev.pos[1]))
            self.g.pos[node] = [x, y]
            self.drag = (node, True)
    return True


def _stage_click(self, p):
    n = self.node_at(p)
    now = pygame.time.get_ticks()
    if self.mode == "move":
        if n is not None:
            self.drag = (n, False)
            self.sel_edge, self.wbuf = None, ""
            return
        e = self.edge_at(p)
        if e is not None:
            self.sel_edge, self.wbuf = e, ""
            return
        self.sel_edge, self.wbuf = None, ""
        last_t, last_p = self.last_click
        if now - last_t < 380 and math.dist(p, last_p) < 12:
            if self.g.add_node(*p):
                self.edited()
        self.last_click = (now, p)
    elif self.mode == "node":
        if n is None and self.g.add_node(*p):
            self.edited()
    elif self.mode == "edge":
        if n is None:
            self.edge_from = None
        elif self.edge_from is None:
            self.edge_from = n
        else:
            if self.g.add_edge(self.edge_from, n):
                self.edited()
            self.edge_from = None
    elif self.mode == "delete":
        if n is not None:
            if self.g.del_node(n):
                self.edited()
        else:
            e = self.edge_at(p)
            if e is not None:
                del self.g.edges[e]
                self.edited()
    # Dijkstra: trace a path after the run finished
    if (self.algo == "dijkstra" and self.mode == "move" and n is not None
            and self.step == len(self.snaps) - 1):
        self.drag = None
        self.compute_trace(n)


def _scrub(self, x):
    frac = (x - 36) / 676
    self.playing = False
    self.set_step(round(max(0, min(1, frac)) * (len(self.snaps) - 1)))


def _run(self):
    running = True
    while running:
        dt = min(self.clock.tick(60) / 1000.0, 0.05)
        for ev in pygame.event.get():
            running = self.handle(ev) and running
        self.update(dt)
        self.draw()
    pygame.quit()


App.node_at, App.edge_at, App.compute_trace = _node_at, _edge_at, _compute_trace
App.handle, App.stage_click, App.scrub, App.run = _handle, _stage_click, _scrub, _run


if __name__ == "__main__":
    App().run()
