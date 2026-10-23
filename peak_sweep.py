import sys, time
sys.path.insert(0, "src")

from ai.session import AISession
from core.chunk_manager import ChunkManager
from core.game import Game

SPEED = 16.0
MAX_TICKS = 6000
VIEW = 28
SEED = 20261022


def run(small, large, flood):
    g = Game(SEED, deterministic_food=True, obstacles=False)
    g.clock.set_speed(SPEED)
    cm = ChunkManager(g.world, preload_rings=3, unload_rings=4, max_generate_per_update=16)
    s = AISession(deterministic=True)
    s.max_nodes_small, s.max_nodes_large = small, large
    s.controller.flood_limit = flood
    s.controller.margin_small, s.controller.margin_large = 2, 8
    dt = 1.0 / (10.0 * SPEED)
    while g.ticks < MAX_TICKS and g.state == "running":
        hx, hy = g.snake.head
        cm.update((hx - VIEW, hy - VIEW, hx + VIEW, hy + VIEW))
        d = s.tick(g.world, g.snake, g.wrap_mode, speed=SPEED)
        if d is not None:
            g.set_direction(d)
        g.update(dt)
    return g.ticks, g.score, g.state, s.stats["cost_peak_ms"], s.stats["cost_avg_ms"]


for small, large in ((120, 200), (200, 300), (300, 400)):
    for flood in (40, 60, 80):
        t, sc, st, peak, avg = run(small, large, flood)
        print(f"nodes={small}/{large} flood={flood} -> ticks={t} score={sc} {st} peak={peak:.2f} avg={avg:.2f}")
