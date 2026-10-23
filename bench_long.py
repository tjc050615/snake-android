import sys, time
sys.path.insert(0, "src")

from ai.session import AISession
from core.chunk_manager import ChunkManager
from core.game import Game

SEED = 20261022
VIEW = 28


def run(speed, target_score, max_ticks):
    g = Game(SEED, deterministic_food=True, obstacles=False)
    g.clock.set_speed(speed)
    cm = ChunkManager(g.world, preload_rings=3, unload_rings=4, max_generate_per_update=16)
    s = AISession(deterministic=True)
    dt = 1.0 / (10.0 * speed)
    t0 = time.perf_counter()
    while g.ticks < max_ticks and g.state == "running" and g.score < target_score:
        hx, hy = g.snake.head
        cm.update((hx - VIEW, hy - VIEW, hx + VIEW, hy + VIEW))
        d = s.tick(g.world, g.snake, g.wrap_mode, speed=speed)
        if d is not None:
            g.set_direction(d)
        g.update(dt)
    return (speed, g.ticks, g.score, len(g.snake), g.state,
            time.perf_counter() - t0, s.stats["cost_peak_ms"], g.world.food_count())


print(run(1.0, 500, 30000))
print(run(2.0, 300, 30000))
