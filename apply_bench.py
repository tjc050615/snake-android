import sys, time
sys.path.insert(0, "src")

from ai.session import AISession
from core.chunk_manager import ChunkManager
from core.game import Game

SPEED = 16.0
MAX_TICKS = 7000
VIEW = 28
SEED = 20261022


def run():
    g = Game(SEED, deterministic_food=True, obstacles=False)
    g.clock.set_speed(SPEED)
    cm = ChunkManager(g.world, preload_rings=3, unload_rings=4, max_generate_per_update=16)
    s = AISession(deterministic=True)
    dt = 1.0 / (10.0 * SPEED)
    t0 = time.perf_counter()
    while g.ticks < MAX_TICKS and g.state == "running":
        hx, hy = g.snake.head
        cm.update((hx - VIEW, hy - VIEW, hx + VIEW, hy + VIEW))
        d = s.tick(g.world, g.snake, g.wrap_mode, speed=SPEED)
        if d is not None:
            g.set_direction(d)
        g.update(dt)
    wall = time.perf_counter() - t0
    return g.ticks, g.score, g.state, len(g.snake), wall, s.stats


results = [run() for _ in range(3)]
for i, (ticks, score, state, length, wall, st) in enumerate(results, 1):
    print(f"run{i}: ticks={ticks} score={score} state={state} len={length} "
          f"peak={st['cost_peak_ms']:.2f}ms avg={st['cost_avg_ms']:.2f}ms wall={wall:.1f}s")
same = len({(r[0], r[1], r[2], r[3]) for r in results}) == 1
print("DETERMINISTIC:", same)
