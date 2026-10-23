import sys, time
sys.path.insert(0, "src")

from ai.session import AISession
from core.chunk_manager import ChunkManager
from core.game import Game

SPEED = 16.0
MAX_TICKS = 6000
VIEW = 28
SEED = 20261022


def run(small, large, flood, m_small, m_large):
    g = Game(SEED, deterministic_food=True, obstacles=False)
    g.clock.set_speed(SPEED)
    cm = ChunkManager(g.world, preload_rings=3, unload_rings=4, max_generate_per_update=16)
    s = AISession(deterministic=True)
    s.max_nodes_small, s.max_nodes_large = small, large
    s.controller.flood_limit = flood
    s.controller.margin_small, s.controller.margin_large = m_small, m_large
    dt = 1.0 / (10.0 * SPEED)
    t0 = time.perf_counter()
    while g.ticks < MAX_TICKS and g.state == "running":
        hx, hy = g.snake.head
        cm.update((hx - VIEW, hy - VIEW, hx + VIEW, hy + VIEW))
        d = s.tick(g.world, g.snake, g.wrap_mode, speed=SPEED)
        if d is not None:
            g.set_direction(d)
        g.update(dt)
    return g.ticks, g.score, g.state, s.stats["cost_peak_ms"], time.perf_counter() - t0


rows = []
for small, large in ((300, 500), (500, 800), (800, 1500)):
    for flood in (80, 120):
        for margins in ((2, 8), (2, 2)):
            ticks, score, state, peak, wall = run(small, large, flood, *margins)
            rows.append((small, large, flood, margins, ticks, score, state, peak))
            print(f"nodes={small}/{large} flood={flood} margin={margins} "
                  f"-> ticks={ticks} score={score} state={state} peak={peak:.2f}ms")

best = max(rows, key=lambda r: (r[4], -r[7]))
print("\nBEST:", best)
print("3x determinism check:")
for _ in range(3):
    print(run(best[0], best[1], best[2], *best[3])[:4])
