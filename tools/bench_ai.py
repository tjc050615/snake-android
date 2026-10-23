import sys, time
sys.path.insert(0, "src")

from ai.session import AISession
from core.game import Game

SPEED = 16.0
MAX_TICKS = 6000

g = Game(20261022)
g.clock.set_speed(SPEED)
s = AISession()
dt = 1.0 / (10.0 * SPEED)   # 16x => 每帧推进 1 个 tick
t0 = time.perf_counter()
frames = 0
while g.ticks < MAX_TICKS and g.state == "running":
    d = s.tick(g.world, g.snake, g.wrap_mode, speed=SPEED)
    if d is not None:
        g.set_direction(d)
    g.update(dt)
    frames += 1

wall = time.perf_counter() - t0
print(f"speed={SPEED}x ticks={g.ticks} score={g.score} state={g.state} "
      f"wall={wall:.1f}s per_tick={wall / max(1, g.ticks) * 1000:.2f}ms")
print("stats:", {k: s.stats[k] for k in ("eaten", "blocked_l1", "blocked_l2", "follow_tail", "timeouts", "cost_avg_ms", "cost_peak_ms")})
