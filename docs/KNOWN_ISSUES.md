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
| KI-005 | M4 前 | P3 | **resize 后相机世界位置漂移**：`grid_size` 变化时 `current_x/y` 仍是旧像素值，取景中心在世界坐标里跳变。M4 处理：按 `current / old_grid * new_grid` 换算，或重置到蛇头 | 拖动窗口大小观察画面跳变 | M4 | open |
| KI-006 | M5 | P2 | 插值要求每帧重绘，`rebuild()` 每帧 `canvas.clear()` + 重建全部 Canvas 指令（网格线 40+ 条）。M5 应改局部更新 / 指令池复用 | 观察 `rebuild` 每帧调用 | M5 | open |
| KI-007 | M2/R2 | P3 | 障碍生成后的"孤立格修复"会移除 0~2 个障碍，导致个别 chunk 密度略低于 5%（实测仍 ≥4%）；修复逻辑本身无跳变，属可接受偏差 | `gen.chunk_obstacle_cells` 返回数 < `round(0.05*1024)` | M2 | open |
| KI-008 | M2/R2 | P2 | 障碍的连通性是**启发式保证**（边界整行整列全通 + 修孤立单格 + 密度低），**不是严格洪水填充**；真正的连通性校验在 R3 的墙壁生成里做，并把障碍一起纳入同一张图。KI-007 的修复只在单 chunk 内生效，跨 chunk 的封闭环未做全局证明 | 设计评审 | R3 起 | open |
| KI-009 | M2/R3 | P1 | **随包字体是 Windows 自带 SimHei 的副本**（`assets/fonts/ChineseFallback.ttf`），仅可用于本地开发；NotoSansSC 下载的 OTF 被 SDL2 文本后端拒绝加载（`Couldn't load font file`）。**发布前必须替换为 OFL 授权的 NotoSansSC/DroidSansFallback TTF**，否则有版权与打包风险 | 检查 `assets/fonts/` | M5 打包前 | open |
| KI-010 | M2/R4 | P3 | 已加载 chunk 数量随视口尺寸变化：受控视口（1 chunk + 2 圈）= 30，符合 20~30；但 1280×720（视口跨 2×1 chunk）+ 卸载 3 圈会到 **42**，超出验收区间。收紧到 20~30 需把预加载降到 1 圈或把卸载降到 2 圈（后者会失去滞回带），需拍板 | `--smoke 8` 看 `chunks_loaded` | M2 | **wontfix**（需求偏差已确认，实现不改：ARCH §7.1 已改为 30~45 个 / <1MB；D-005 锁定值不变） |
| KI-011 | M3 前 | P2 | `World.query_blocked_in_rect` / `foods_in_rect` 目前是 O(n) 遍历 `_blocked`/`_foods`；42 chunk 约 2500 个 blocked cell，M3 的 AI 每一步都调用会把 8ms 预算吃光。M3 开工前改为按 chunk 分桶（`_blocked_by_chunk: dict[key, set]`）或空间哈希，把矩形查询降到 O(命中格数) | M3 性能测试 | M3 | open |

## 已关闭

| ID | 阶段 | 级别 | 现象 | 修复与验证 | 关闭时间 |
|---|---|---|---|---|---|
| KI-002 | M1/R1 | P1 | 本机 Python 3.14 装不上 Kivy 2.3.0，GUI 未实跑 | 建 `.venv`(3.11.3) + kivy 2.3.0；`--smoke` 多轮 exit 0，4 张多分辨率截图 | 2026-10-22 |

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
