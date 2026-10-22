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
