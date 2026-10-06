"""Entry point used by the browser build (pygbag looks for main.py)."""
import asyncio
import pygame  # noqa: F401  (pygbag scans main.py to know which packages to load)
from greedy_graph_lab import App

asyncio.run(App().run_async())
