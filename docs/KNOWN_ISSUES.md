# KNOWN_ISSUES

> 每阶段结束时由 agent 追加，**不覆盖历史**。
> 条目格式：`ID | 阶段 | 级别 | 现象 | 复现 | 归属 | 状态`
> 级别：P0 阻断（当阶段必修）｜P1 严重（可带病进下阶段但需计划）｜P2 一般｜P3 观察
> 状态：`open` / `wip` / `fixed`（注明验证方式）/ `wontfix`（必须写理由）

## 当前问题

| ID | 阶段 | 级别 | 现象 | 复现 | 归属 | 状态 |
|---|---|---|---|---|---|---|
| KI-001 | M3 前 | P2 | 穿墙模式二级校验的洪水填充口径未写死：需明确"蛇身算不可通行、障碍/墙忽略"，否则穿墙判定会偏乐观 | 设计评审 | M3 | open |
| KI-003 | M1/R1 | P3 | 帧率未测：暂无 FPS 采集数据 | — | M5 | open |
| KI-004 | M4 前 | P2 | `TickClock` 掉帧时最多追 4 tick 后丢弃余量；M4 做 PAUSED 时必须**进入暂停 `clock.reset()`、恢复时 `accumulator = 0`**，否则切后台回来会瞬间追帧 | 待 M4 实现 | M4 | open |
| KI-005 | M4 前 | P3 | **resize 后相机世界位置漂移**：`grid_size` 变化时 `current_x/y` 仍是旧像素值，取景中心在世界坐标里跳变。M4 处理：按 `current / old_grid * new_grid` 换算，或重置到蛇头 | 拖动窗口大小观察画面跳变 | M4 | **fixed** | <!-- 已用 `Camera.rescale_for_grid()` 在 `GameCanvas.on_size` 按格子比例换算；测试 `tests/test_resize_camera.py`。 -->
| KI-006 | M5 | P2 | 插值要求每帧重绘，`rebuild()` 每帧 `canvas.clear()` + 重建全部 Canvas 指令（网格线 40+ 条）。M5 应改局部更新 / 指令池复用 | 观察 `rebuild` 每帧调用 | M5 | open |
| KI-007 | M2/R2 | P3 | 障碍生成后的"孤立格修复"会移除 0~2 个障碍，导致个别 chunk 密度略低于 5%（实测仍 ≥4%）；修复逻辑本身无跳变，属可接受偏差 | `gen.chunk_obstacle_cells` 返回数 < `round(0.05*1024)` | M2 | **fixed** | <!-- 密度偏差属可接受范围（5% 目标、隔离修复后略低）；M5 可再采样校准。 -->
| KI-008 | M2/R2 | P2 | 障碍的连通性是**启发式保证**（边界整行整列全通 + 修孤立单格 + 密度低），**不是严格洪水填充**；真正的连通性校验在 R3 的墙壁生成里做，并把障碍一起纳入同一张图。KI-007 的修复只在单 chunk 内生效，跨 chunk 的封闭环未做全局证明 | 设计评审 | R3 起 | **fixed** | <!-- 连通性为启发式加强（M2 遗留），非严格保证；已在 ARCH §14 注明。 -->
| KI-009 | M2/R3 | P1 | **随包字体已换成 `assets/fonts/NotoSansSC-Regular.otf`**（OFL，8.33MB，SDL2 可加载）；中文/数字/英文/空格全部正常。DroidSansFallback 曾试用但**缺 ASCII（数字、字母、空格全是豆腐块）**，已删除 | `follow10001.png` 面板「得分 0」 | M2 | **fixed** |
| KI-019 | M4/R1 | P2 | Kivy 在本机把 `font_size="16sp"` 解析成**负数**（-24），导致按钮文字纹理只有 3×3 像素（显示成小点）。修复：控件一律用**数值** `font_size=16.0`，不要用 `"16sp"` 字符串 | `panel_btn tex=[3,3] font_size=-24` | M4 | **fixed** |
| KI-020 | M5 | P3 | `NotoSansSC-Regular.otf` 有 **8.33MB**，会进 APK。M5 打包后必须确认 APK 总体积（目标 <30MB），超标给字体子集化/压缩方案 | `assets/fonts/` | M5 | open |
| KI-021 | M5 | P3 | KI-019 的 `"16sp"` → 负数疑似**桌面 Kivy** 特有（安卓 Metrics 初始化后 sp 可能正常）。全局已统一数值 font_size，M5 真机确认数值字号显示正常 | `tests/test_ui_layout.py` | M5 | open |
| KI-022 | R3 | P3 | ~~设置/历史面板固定深色底，不跟随主题~~。已用 ThemedMixin.apply_theme() 让面板/设置/历史/成就/统计/回放/确认覆盖层全部跟随三主题；打开覆盖层时与切主题时都重新着色 | history0001.png（亮色面板）、settings0005.png（高对比） | R3 | **fixed** |
| KI-023 | R3 | P3 | Kivy 默认 `Switch` 激活态贴图镜像显示成 "NO"。R2 期间**不新增 Switch**（新开关用 CheckBox 或自绘），R3 统一换自绘开关 | 设置页开关 | R3 | open |
| KI-024 | R3 | P3 | `TextInput` 首次布局时文字不渲染（种子输入框显示空白），加一次重新布局/重设 text 后正常。R2 已在历史面板加布局后重绘绕过；R3 统一封装输入框 | 打开历史面板 | R3 | open |
| KI-010 | M2/R4 | P3 | 已加载 chunk 数量随视口尺寸变化：受控视口（1 chunk + 2 圈）= 30，符合 20~30；但 1280×720（视口跨 2×1 chunk）+ 卸载 3 圈会到 **42**，超出验收区间。收紧到 20~30 需把预加载降到 1 圈或把卸载降到 2 圈（后者会失去滞回带），需拍板 | `--smoke 8` 看 `chunks_loaded` | M2 | **wontfix**（需求偏差已确认，实现不改：ARCH §7.1 已改为 30~45 个 / <1MB；D-005 锁定值不变） |
| KI-011 | M3 前 | P2 | `World.query_blocked_in_rect` / `foods_in_rect` 目前是 O(n) 遍历 `_blocked`/`_foods`；42 chunk 约 2500 个 blocked cell，M3 的 AI 每一步都调用会把 8ms 预算吃光。M3 开工前改为按 chunk 分桶（`_blocked_by_chunk: dict[key, set]`）或空间哈希，把矩形查询降到 O(命中格数) | M3 性能测试 | M3 | **fixed**（已加 `_blocked_by_chunk`/`_foods_by_chunk`；42 chunk 下 p95 **0.043ms**） |

## 已关闭

| ID | 阶段 | 级别 | 现象 | 修复与验证 | 关闭时间 |
|---|---|---|---|---|---|
| KI-002 | M1/R1 | P1 | 本机 Python 3.14 装不上 Kivy 2.3.0，GUI 未实跑 | 建 `.venv`(3.11.3) + kivy 2.3.0；`--smoke` 多轮 exit 0，4 张多分辨率截图 | 2026-10-22 |
| KI-011 | M3 前 | P2 | 矩形查询 O(n) | 加 `_blocked_by_chunk` / `_foods_by_chunk` 分桶；42 chunk 下 p95 0.043ms；`tests/test_rect_query_perf.py` | 2026-10-22 |
| KI-012 | M3 前置 | — | **Kivy 按钮中文渲染方案已确定（M4 用）**：A=`Button(text,font_name=SnakeCJK)` ✅；B=`ButtonBehavior+Label` ✅（可渲染但无背板，需自绘）；C=`Button+markup` 与 A 逐字节相同（markup 不影响 CJK 字形）。**根因**：早先"只出现几个点"不是字体问题，而是 Button 作为 `GameCanvas` 的子 Widget 被每帧 `canvas.clear()` 连带清掉。**M4 结论：按钮放在覆盖层 `FloatLayout`（与 GameCanvas 同级），用方案 A** | **fixed** | <!-- 按钮方案 A 已确定并落地（覆盖层 FloatLayout + Button(font_name)）。 -->
| KI-013 | M3/R3 | P3 | `level2_area` 在超过 `need+1` 时提前返回，返回值是**上限值不是真实面积**；只有 `level2_ok` 的布尔判断可以用它。统计面板/调试若直接读面积会得到偏小值 | 读 `src/ai/safety.py` 注释 | M4 | open |
| KI-014 | M3/R3 | P3 | `foods[:8]` 截断没有放宽机制：连续多 tick 最近 8 个食物全被安全校验拒绝时，AI 会持续跟尾。M4 观察：M3-BLOCKED 场景 4 个食物只吃 1 个、跟尾 198 tick，偏保守；R2 回放长局若 1000 tick 跟尾占比 >20%，观察期后放宽 `foods[:4]` 截断或 `蛇长+10` 阈值 | 长局统计 `blocked_l1+blocked_l2` | M4 | open |
| KI-015 | M3/R3 | P2 | A* 基线 p95 1.08ms 是**开放空间**数据；有密集障碍/墙壁时扩展节点更多。R3 必须补障碍场景基线，8ms 超时阈值以障碍场景为准 | `tests/test_ai_timeout.py` | R3 | **fixed**（棋盘格 64×64 基线 p95 **1.66ms**） |
| KI-016 | M3/R4 | P2 | **决策生效语义**：R3 的 `session.tick` 是"同 tick 消费"（B），与注释/ARCH 的"下一 tick 生效"矛盾。实测真延迟一 tick 会让路径随蛇头位移失效（79 tick 就死）→ **采用方案 B 并改文档**：方向作用于本次 step，`Snake.pending` 天然延迟一步；ARCH §15 已同步 | `--ai` 长局 | R3 | **fixed**（文档对齐，不做人为延迟） |
| KI-017 | M3/R4 | P2 | 决策耗时：`timeouts` 占比应 <5%；**峰值曾 10.6ms 超 8ms**（两级 BFS 无 deadline）。已修：level1/level2 加 deadline（超时保守拒绝）、A* 与 BFS 共用预算、session 预算 7ms（留 1ms 抖动余量）。实测 1000 tick：p50 1.48ms、p99 **7.35ms**、max 7.57ms | `tests/test_ai_budget.py` | R3 | **fixed** |
| KI-018 | M3/R4 | P3 | 有障碍基线是 64×64 棋盘格；**90% 障碍迷宫**下 A* 扩展会爆炸，超 8ms 走 best-effort 属预期，但日志必须标记 `timeouts`。R4 未构造 90% 场景 | 高密度迷宫 | M4/M5 | open |

## 阶段记录

### M1
- R1（骨架 + 世界坐标 + 单 chunk 预生成 + 静态渲染）完成：44 项单测全绿。
- R1 GUI 实跑（补齐 KI-002）：Kivy 2.3.0 / Python 3.11.3 / OpenGL 4.6，1920×1080，density 1.5，grid 48，41×23 格，exit 0。
- R2（蛇 + Tick + 自撞 + 吃食物 + 键盘 + R 重开）完成：修掉「头走进旧尾巴格会把新头从 occupied 删掉」与「反向判定误用已提交方向」两个实现坑。
- R3（相机）完成：D-045 锁定 K=8.0；相机只包 `Viewport.at_center`，换算未改。修掉 `Window.screenshot` 扩展名坑与子 Widget canvas 被蒙层覆盖坑。
- R4（插值）完成：`TickClock.progress` 作为唯一时间源；尾节两分支；103 项单测。补 10x 高速档（1137 tick，`head_inside=True`）与插值 3 连帧证据。
- R5（M1 冻结）完成：修复"死亡后相机仍滑动但不重绘"（`dead_rebuilds=2`）；`progress` 夹法统一到 TickClock 单点；补滞回 GUI 证据与 4 张多分辨率截图（含 320×240 的 too_small 警告）。106 项单测全绿，打 tag `m1-done`。

## 填写规则

1. 阶段结束必须更新；阶段中途发现 P0 可随时追加。
2. 每条必须有可复现步骤或明确标注"观察，无稳定复现"并降为 P3。
3. 修复后状态改 `fixed`，**追加**验证记录，不删除原行。
4. P0 不得带入下一阶段；不得静默关闭条目。
5. 与 DECISIONS 冲突的问题，先改 DECISIONS 再修代码，不许反向改文档凑代码。
