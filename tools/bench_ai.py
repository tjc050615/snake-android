import sys, time
sys.path.insert(0, "src")

from ai.session import AISession
from core.chunk_manager import ChunkManager
from core.game import Game

SPEED = 16.0
MAX_TICKS = 6000
VIEW = 26   # 模拟视口半径（格）

g = Game(20261022)
g.clock.set_speed(SPEED)
cm = ChunkManager(g.world, max_generate_per_update=16)
s = AISession()
dt = 1.0 / (10.0 * SPEED)

t0 = time.perf_counter()
while g.ticks < MAX_TICKS and g.state == "running":
    hx, hy = g.snake.head
    cm.update((hx - VIEW, hy - VIEW, hx + VIEW, hy + VIEW))   # 模拟真实 chunk 加载
    d = s.tick(g.world, g.snake, g.wrap_mode, speed=SPEED)
    if d is not None:
        g.set_direction(d)
    g.update(dt)

wall = time.perf_counter() - t0
print(f"speed={SPEED}x ticks={g.ticks} score={g.score} state={g.state} "
      f"wall={wall:.1f}s per_tick={wall / max(1, g.ticks) * 1000:.2f}ms")
print("stats:", {k: s.stats[k] for k in ("eaten", "blocked_l1", "blocked_l2", "follow_tail", "timeouts", "cost_avg_ms", "cost_peak_ms")})
