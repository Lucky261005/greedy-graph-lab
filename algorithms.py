"""
Greedy graph algorithms with step recording (no GUI code in this file).

Each *_steps(graph) function runs the real algorithm once and returns a list of
"snapshots": the state of every node and edge, the data-structure contents, the
code line being executed and a short explanation.  Both front ends replay them:
    app.py                 Streamlit web app
    greedy_graph_lab.py    pygame desktop app
"""
import heapq
import math
import random

INF = float("inf")

# colours used for the stat read-outs
CYAN = (25, 190, 236)
ORANGE = (244, 158, 44)
GREEN = (52, 214, 108)

ORDER = ["kruskal", "prim", "dijkstra"]

TITLES = {
    "kruskal": ("Kruskal's Algorithm", "Sort the edges, then keep every edge that does not close a cycle.",
                "O(E log V)", "O(V + E)"),
    "prim": ("Prim's Algorithm", "Grow one tree from the start node, always adding the cheapest crossing edge.",
             "O(E log V)", "O(V + E)"),
    "dijkstra": ("Dijkstra's Algorithm", "Shortest paths from one source: always settle the closest unsettled node.",
                 "O((V + E) log V)", "O(V)"),
}

CODE = {
    'kruskal': ['def kruskal(V, E):', '    MST, dsu = [], DSU(V)', '    for (u, v, w) in sorted(E, key=weight):', '        if dsu.find(u) != dsu.find(v):', '            dsu.union(u, v)', '            MST.append((u, v, w))', '        # else: the edge would close a cycle', '        if len(MST) == len(V) - 1:', '            break', '    return MST'], 'prim': ['def prim(G, s):', '    seen, MST = {s}, []', '    pq = [(w, s, v) for v, w in G[s]]; heapify(pq)', '    while pq:', '        w, u, v = heappop(pq)', '        if v in seen: continue', '        seen.add(v); MST.append((u, v, w))', '        for x, wx in G[v]:', '            if x not in seen:', '                heappush(pq, (wx, v, x))', '    return MST'], 'dijkstra': ['def dijkstra(G, s):', '    dist = {v: INF for v in G}; dist[s] = 0', '    pq = [(0, s)]', '    while pq:', '        d, u = heappop(pq)', '        if d > dist[u]: continue', '        for v, w in G[u]:', '            if d + w < dist[v]:', '                dist[v] = d + w; prev[v] = u', '                heappush(pq, (dist[v], v))', '    return dist, prev']}


def name(i):
    return chr(65 + i)


def ename(e):
    return f"{name(e[0])}-{name(e[1])}"


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
        inner_left, inner_top, inner_right, inner_bottom = 76, 161, 700, 589
        pts = []
        tries = 0
        while len(pts) < n and tries < 4000:
            tries += 1
            p = (random.randint(inner_left, inner_right),
                 random.randint(inner_top + 20, inner_bottom))
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
