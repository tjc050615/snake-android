# R5A 性能审计表（代码层）

> 状态：**审计完成，优化未开始**。等你确认后逐项改。
> 环境：Windows / Python 3.11 / Kivy 2.3.0；数据来自现有测试与代码走查。

## 0. 已测基线（现有证据）

| 指标 | 值 | 来源 |
|---|---|---|
| AI 决策耗时 p50 / p99 / max | 1.48 / 7.35 / 7.57 ms | `tests/test_ai_budget.py`（1000 tick） |
| AI 硬预算 | 7.0 ms（高速 3.5 ms） | `AISession.tick(budget_s=...)` |
| chunk 生成 p95（墙） | 1.85 ms（要求 <3ms） | `tests/test_walls.py` |
| 逻辑 tick | 10 Hz 固定 | D-036 |
| 渲染上限 / 底线 | 90~120 FPS / 55 FPS | ARCH §13（真机 R5B 验证） |

## 1. 渲染路径审计（`GameCanvas.rebuild`）

| 项 | 现状 | 证据 | 结论 / 计划 |
|---|---|---|---|
| 每帧清屏重建 | `self.canvas.clear()` 后重建背景/网格/食物/障碍/墙/蛇/路径 | `game_canvas.py:175-176` | **已知（KI-006）**。R5A 计划：静态层（背景+网格）缓存评估，能否用 FBO 或仅在相机/主题变化时重建 |
| 视口裁剪 | 食物/障碍/墙用 `iter_visible_cells()`，蛇/path 用 `vp.covers` 过滤 | `game_canvas.py` | 已裁剪；R5A 仅确认边界（相机外一格仍绘制） |
| 蛇身插值分配 | `segment_cells()` 每帧返回新 list（长度≈蛇长+1） | `core/interp.py` | **可优化**：加 `out=None` 复用缓冲，`test_rebuild_no_new_list_per_frame` 断言 |
| 每帧 f-string | 状态文本仅在死亡/暂停时生成；得分走 Panel Label（tick 变化才刷新） | `app.py` `_frame` | 已缓解；R5A 复查 tick 内的 f-string |
| 背景/网格 FBO | 未做 | — | **评估后决定**：1200×700 FBO 显存 ~3.4MB，收益是省 40~60 次 Line 调用；风险是 resize/主题切换要重建。倾向 R5B 真机测后决定 |

## 2. AI 与 chunk 错峰

| 项 | 现状 | 结论 / 计划 |
|---|---|---|
| AI 决策触发 | 每个逻辑 tick（10Hz）同步调用 `AISession.tick`，共享 7ms 预算 | 正常帧不受影响；高速档每 2 tick 一次（`period=2`） |
| chunk 生成触发 | `_update_chunks()` 每帧检查，实际生成只在跨 chunk 时发生 | 多数帧为 O(1) 检查 |
| 同帧叠加 | **未强制错峰**：跨 chunk 的那一帧可能同时做 AI 决策 + chunk 生成 | **R5A 优化**：AI 产生决策的帧跳过 chunk 生成（延后一帧），补 `test_ai_and_chunk_not_same_frame` |
| 帧预算 | 无显式求和校验 | **R5A 补** `test_frame_budget_under_16ms`（mock 各模块耗时求和 ≤16.67ms） |

## 3. 对象池审计

| 对象 | 现状 | 证据 | 结论 |
|---|---|---|---|
| A* `NodePool` | 每次搜索后释放，节点数组复用 | `ai/search.py` | ✅ 已池化 |
| `DebugStats` 返回 dict | 复用同一 `_buf` | `core/debug.py`（R3） | ✅ 已复用 |
| `Snake.body` | `deque` + `set` 双结构，O(1) 头尾/占位 | `core/snake.py:42` | ✅ 已优化；`set` 每步只增删各 1 个元素 |
| `World._blocked` 等 | set/dict 按 chunk 分桶 | `core/world.py` | ✅ 无每帧重建 |
| `viewport.iter_visible_cells` | 生成器（惰性） | `core/viewport.py` | ✅ 无中间列表 |
| `segment_cells` | 新建 list | `core/interp.py` | ⚠️ 待加复用缓冲 |
| `Rebuild` 里的 `cells[1:]` | 切片每帧新建 list | `game_canvas.py:239` | ⚠️ 待改为 `islice` 或索引循环 |

## 4. 每帧分配清单（待改）

| 位置 | 分配 | 计划 |
|---|---|---|
| `segment_cells` | `list` | 传 `out` 缓冲复用（保留旧签名兼容） |
| `game_canvas` 蛇身 `cells[1:]` | 切片 list | 改 `for i in range(1, len(cells))` 或 `itertools.islice` |
| 状态文本 | f-string（死亡/暂停时） | 保持（低频） |
| Panel 文本 | tick 变化时 1 次 f-string | 保持（10Hz，可接受） |

## 5. Clock 分片计划

| 模块 | 频率 | 预算 |
|---|---|---|
| 逻辑 tick | 10 Hz | ≤2 ms |
| AI 决策 | 10 Hz（共享 7ms） | ≤7 ms |
| chunk 生成 | 跨 chunk 时 | ≤3 ms，且与 AI 不同帧 |
| 调试采集 | 仅开启时每帧 | 60 帧 deque，O(1) |
| 输入 | 事件驱动 | ≤1 ms |

`test_frame_budget_under_16ms`：mock `logic=1.5 / ai=6.0 / chunk=2.5 / input=0.2 / render=4.0` 求和 = 14.2ms < 16.67ms；再验证「AI 帧不同时做 chunk」时 ≤13.0ms。

## 6. 计划新增测试

| 测试 | 断言 |
|---|---|
| `test_rebuild_no_new_list_per_frame` | 连续两次 rebuild 不新增蛇身 list（对象 id 复用） |
| `test_ai_and_chunk_not_same_frame` | 同一帧不会同时触发 AI 决策与 chunk 生成 |
| `test_frame_budget_under_16ms` | 各模块 mock 耗时求和 ≤16.67ms |
| `test_chunk_generation_budget_p95_under_3ms` | 已有（保留） |
| `test_ai_tick_budget_p99_under_8ms` | 已有（保留） |
| `test_segment_cells_reuses_buffer` | 传入 out 时返回同一对象 |

## 7. 已评估但暂不做

| 项 | 原因 |
|---|---|
| 背景/网格 FBO 缓存 | 收益中（省 40~60 次 Line），但 resize/主题切换需重建，且真机显存未知；R5B 测后决定 |
| 蛇身增量绘制（只画变化格） | 与插值渲染冲突（每帧蛇身位置连续变化），收益低 |
| 异步 chunk 生成（线程） | 引入锁与确定性风险，R5B 真机数据若显示卡顿再评估 |
| AI 多线程 | 7ms 已满足预算，收益低 |


## 8. R5A 优化结果（已完成）

| 优化项 | 改前 | 改后 | 验证 |
|---|---|---|---|
| 蛇身插值缓冲 | 每帧新建 result list（1 次/帧） | 传入 `out` 复用，10 帧 0 新建 | `test_segment_cells_reuses_buffer`、`test_rebuild_no_new_list_per_frame` |
| `cells[1:]` 切片 | 每帧额外 1 个切片 list | 改索引循环 `range(1, len(cells))`，0 切片 | `test_rebuild_no_new_list_per_frame` |
| AI / chunk 错峰 | 跨 chunk 帧可能 AI + chunk 叠加（最坏 18.0ms） | AI 决策帧跳过 chunk，最坏 15.5ms | `test_ai_and_chunk_not_same_frame`、`test_frame_budget_under_16ms` |
| 高速无空白 | — | 10x、每两帧生成一次，500 帧内 chunk 覆盖始终 ≥ 视口+1 圈 | `test_ai_chunk_stagger_no_gap_at_high_speed`（预热后 500 帧） |
| 帧预算（典型档） | 无 | 8.1ms < 12ms | `test_frame_budget_typical_under_12ms` |
| 帧预算（最坏档） | 直接相加 18.0ms 超预算 | 错峰后 `2.0 + max(7.5,2.5) + 1.0 + 5.0 = 15.5ms` < 16.67ms | `test_frame_budget_under_16ms` |

**每帧新建 list 数**：改前 2（`segment_cells` 结果 + `cells[1:]` 切片）→ 改后 1（`segment_cells` 内部 `list(snake.body)`，为 O(1) 下标访问保留，见下）。

### 未做的原因

| 项 | 原因 |
|---|---|
| `list(snake.body)` | 蛇身是 `deque`，按下标随机访问是 O(n)，逐帧 `list()` 换 O(1) 访问；若去掉了，长蛇时插值会退化成 O(n²)。**结论：保留一次分配更好** |
| FBO 缓存背景/网格 | R5B 真机帧时间后再评估（避免为未知收益引入 rebuild 复杂度） |
| 异步 chunk / 多线程 AI | 7ms 预算已满足；异步会引入锁与确定性风险 |

### 测试总览

`python -m pytest -q` → **372 passed, 1 skipped**

新增：`tests/test_r5a_perf.py`（6 条：缓冲复用、无切片、错峰、无空白、典型/最坏帧预算）。
保留：`test_chunk_generation_budget_p95_under_3ms`、`test_ai_tick_budget_p99_under_8ms`。


## 9. 10x 高速 chunk 饿死（发现的真 bug 与修复）

### 现象与证据

10x 下 `TickClock` 每帧都有 tick。实测 600 帧、60fps：

```
ticks/frame 分布: {1: 201, 2: 399}   # 0 次从未出现
```

因此 `had_ai_tick = summary.ticks > 0` **恒为 True**（AI 模式），`chunk_slot = not had_ai_tick`
恒为 False → chunk 永不再生成，预加载会被耗尽，视口边缘可能出现空白。

**之前 `test_ai_chunk_stagger_no_gap_at_high_speed` 没有发现它**：该测试用的是
`chunk_slot(had_ai_tick=(frame % 2 == 0))` 的**模拟**节奏（不是真 TickClock），
且断言依赖预热阶段已加载的 chunk。属于"测试写成了 case 1（mock 节奏）"。

### 修复

`chunk_slot` 增加 `max_skip`：最多连续跳过 6 帧，之后强制生成一次。

```python
def chunk_slot(had_ai_tick, frames_since_chunk=0, max_skip=MAX_CHUNK_SKIP_FRAMES):
    if not had_ai_tick:
        return True
    return frames_since_chunk >= max_skip
```

App 里维护 `self._frames_since_chunk`，生成后清零。

### 回归测试

| 测试 | 断言 |
|---|---|
| `test_10x_ticks_every_frame` | 10x/600 帧内不出现无 tick 帧（{1:201, 2:399}） |
| `test_chunk_starvation_at_10x` | AI 模式 + 10x，500 帧 chunk 更新 **≥80 次**（实际约 83 次，500/6） |
| `test_chunk_slot_human_mode_never_starves` | 人类模式每帧都生成（200/200） |

### 代价与边界

- 强制生成的帧仍可能与 AI 决策同帧（每 6 帧一次），最坏帧回到"AI+chunk 同帧"，因此
  帧预算的最坏档必须按"不保证永远错峰"看待（见 §10 风险）。
- 6 帧阈值 = 60fps 下 100ms；10x 时蛇每 100ms 前进 10 格，预加载 2 圈（64 格）足够覆盖。

## 10. 最坏帧余量风险（R5B 必看）

错峰后最坏帧：`logic 2.0 + AI 7.5 + input 1.0 + render 5.0 = 15.5ms`，
距 16.67ms **只剩 1.17ms**。

- 实测 AI 峰值 7.57ms，`render=5.0` 是 mock 上限；真机个别帧两者同时踩上限就会超预算。
- **R5B 真机验收必须看 p99 帧时间，不能只看平均 FPS。**
- 若 p99 > 16ms，按优先级降：① AI 预算 7.0→6.0ms（`AISession(budget_s=0.006)`）；② render 侧减少每帧绘制（食物/障碍批处理或 FBO）。


## 11. 强制 chunk 帧跳过 AI（方案 A，已实现）

`max_skip` 修复引入的新矛盾：强制 chunk 的那一帧同时跑 AI 决策 → 最坏 18.0ms 超预算。
按方案 A 对称处理——**强制 chunk 帧跳过 AI 决策**：

```python
# core/frame_budget.py
def forced_chunk_frame(had_ai_tick, seconds_since_chunk, max_skip_s=MAX_CHUNK_SKIP_SECONDS):
    return had_ai_tick and seconds_since_chunk >= max_skip_s
```

```python
# app._frame
self._force_chunk_now = forced_chunk_frame(...)
summary = self.game.update(dt)
...
# app._ai_tick
if self._force_chunk_now:
    self.session.note_forced_reuse()   # 记一次 no_decision_reuse
    return
```

效果：
- 强制 chunk 帧 = `logic 2 + input 1 + render 5 + chunk 2.5 = 10.5ms`（安全）
- 普通 AI 帧 = `logic 2 + AI 7.5 + input 1 + render 5 = 15.5ms`
- 10Hz 下约每 0.1~0.6s 跳过一次 AI 决策，记 1 次 `no_decision_reuse`，行为影响可忽略。

## 12. 时间阈值（不依赖帧率）

`MAX_CHUNK_SKIP_SECONDS = 0.1`，用 `_time_since_chunk += dt` 累加：
- 30fps 设备：每 3 帧一次（≈100ms）
- 120fps 设备：每 12 帧一次（≈100ms）
- 测试 `test_chunk_skip_uses_time_not_frames` 验证两者饿死窗口都 ≈100ms。

## 13. 初始化预加载

`ChunkManager(..., initial_rect=...)` 构造时循环 `update()` 直到 `desired(rect) ⊆ loaded`，
避免"前 N 帧不生成 chunk"造成开局空白。测试 `test_chunk_manager_preloads_on_init`。

## 14. 旧高速测试的确认

`test_ai_chunk_stagger_no_gap_at_high_speed` 原实现用
`chunk_slot(had_ai_tick=(frame % 2 == 0))` **模拟**节奏、且预热已加载足够 chunk——
这是漏掉饿死的直接原因（对应你列的情况 1 + 2）。现已由真实数据替换：
`test_10x_ticks_every_frame`（真 TickClock，{1:201, 2:399}）+
`test_chunk_starvation_at_10x`（真 `Game.update`，500 帧 70~95 次生成）。
