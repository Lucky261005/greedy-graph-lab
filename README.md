# Greedy Graph Lab

An interactive, step-by-step simulator for three greedy graph algorithms from the DAA syllabus (Unit 3):

| Algorithm | Solves | Time | Space |
|---|---|---|---|
| Kruskal's | Minimum spanning tree | O(E log V) | O(V + E) |
| Prim's | Minimum spanning tree | O(E log V) | O(V + E) |
| Dijkstra's | Single-source shortest paths | O((V + E) log V) | O(V) |

Each step shows the greedy choice, the data structure in use (Union-Find sets or a priority queue), the line of code being executed, and a short explanation.

**Live demo:** https://lucky261005.github.io/greedy-graph-lab/  (runs in your browser; the first load takes a few seconds)

## Screenshots

![Kruskal](screenshots/kruskal.png)
![Prim](screenshots/prim.png)
![Dijkstra](screenshots/dijkstra.png)

## Run it on your computer

```bash
pip install -r requirements.txt
python greedy_graph_lab.py
```

## Controls

| Input | Action |
|---|---|
| `1` / `2` / `3` | Switch between Kruskal, Prim and Dijkstra |
| `Space` | Play / pause |
| `Left` / `Right` | Step back / forward |
| `Up` / `Down` | Change speed |
| `R`, `N`, `G` | Restart, random graph, sample graph |
| Drag a node | Move it |
| Click a node | Set it as the start vertex (Prim, Dijkstra) |
| Click an edge, type digits | Change its weight |
| Toolbar | Add or delete nodes and edges |

After Dijkstra finishes, click any node to trace its shortest path.

## How it works

1. The `kruskal_steps`, `prim_steps` and `dijkstra_steps` functions run the real algorithm once and record a snapshot after every action.
2. The pygame interface replays those snapshots with animation, so you can pause, step forward or backward, or drag the progress bar.

## Project structure

```
greedy_graph_lab.py   the simulator (runs on desktop and in the browser)
main.py               entry point for the browser build
fonts/                fonts used by the browser build
docs/                 the browser build, published with GitHub Pages
requirements.txt      dependencies
screenshots/          images used in this README
blog/                 the accompanying blog post (text and Blogger HTML)
```

## Rebuilding the web version

The web version is the same Python code, compiled for the browser with [pygbag](https://github.com/pygame-web/pygbag):

```bash
pip install pygbag
# put main.py, greedy_graph_lab.py and fonts/ in a folder, then:
python -m pygbag --build <folder>
```

Copy the files from `<folder>/build/web` into `docs/`.

## Limitations

- The web version needs a desktop browser (mouse and keyboard); the first load downloads the Python runtime.
- Up to 12 nodes and 24 edges.
- Edge weights are whole numbers from 1 to 99; Dijkstra does not support negative weights.

Author: Lucky
