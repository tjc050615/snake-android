# ARCH

> 版本：v1.0 ｜ 状态：待复核
> 数值一律引用 DECISIONS.md（本文件不重复定义常量，只定义"怎么用"）。

## 1. 架构图

```
┌──────────────────────────────────────────────────────────────┐
│                     app (Kivy App, 单进程单线程)              │
│   Window(横屏锁)  Clock 调度  SafeArea  WindowManager        │
├───────────────────────────┬──────────────────────────────────┤
│  view/  渲染与交互          │  ui/  屏幕与弹层                 │
│  GameCanvas（唯一 Widget）  │  Panel(右30%)  Settings  History │
│  Renderer（Canvas 指令池）  │  Onboarding  Dialogs  Achievements│
│  Joystick  PathOverlay      │  Theme  FontScale                │
├───────────────────────────┴──────────────────────────────────┤
│                core/  纯逻辑（零 Kivy 依赖，可无头测试）        │
│  tick  snake  camera  world  chunk  gen  rng  collision       │
├──────────────────────────────────────────────────────────────┤
│                ai/    纯逻辑（零 Kivy 依赖）                   │
│  planner  search  safety  policy  loopguard  overlay_data    │
├──────────────────────────────────────────────────────────────┤
│  data/  storage replay achievements   │  platform_layer/      │
│  （config.json / profile.json）        │  vibrate share insets │
│                                       │  keepawake backkey    │
└──────────────────────────────────────────────────────────────┘
```

**依赖方向只能向下**：`core` / `ai` 不 import kivy；`view` 只读世界状态，不写世界状态；`platform` 是唯一允许出现 pyjnius 的地方。

## 2. 模块职责

| 模块 | 职责 | 明确不做 |
|---|---|---|
| `app/app.py` | Kivy App 生命周期、横屏锁定、安全区注入、全局 Clock 调度 | 玩法逻辑 |
| `app/constants.py` | 常量集中定义（全部来自 DECISIONS） | 可调参数散落 |
| `core/tick.py` | 固定步长累加器、调速倍率、tick 序号 | 渲染插值计算 |
| `core/world.py` | 无限坐标 ↔ chunk 坐标、稀疏哈希容器；`is_passable` 是通行判定**唯一入口** | 生成规则 |
| `core/chunk.py` | 加载/卸载圈数、chunk 生命周期、缓存查询 | 具体地形内容 |
| `core/gen.py` | 纯函数生成：障碍/墙/食物；种子驱动、坐标驱动 | 维护运行时状态 |
| `core/snake.py` | 蛇身队列、移动、生长、碰撞判定 | 渲染 |
| `core/camera.py` | 死区/滞回/硬吸附/指数平滑 | 输入采样 |
| `core/collision.py` | 墙体/障碍/自身碰撞、穿墙模式分支 | AI 决策 |
| `ai/planner.py` | 决策流水线、超时控制、降级、结果双缓冲 | 渲染路径 |
| `ai/search.py` | BFS、A*（平局键）、增量复用、防循环 | 安全判定 |
| `ai/safety.py` | 一级可达性、二级洪水填充、跟尾兜底 | 路径绘制 |
| `view/renderer.py` | Canvas 指令批量绘制、视口裁剪、对象池 | 状态修改 |
| `view/joystick.py` | 15% 死区、归一化、游戏区命中测试 | 相机 |
| `ui/panel.py` | 右 30% 面板与触控隔离 | 蛇的转向 |
| `data/storage.py` | config/profile 读写、版本迁移、损坏降级 | UI |
| `data/replay.py` | 录制/回放、编解码、100KB 截断策略 | 游戏规则 |
| `platform_layer/android.py` | DisplayMetrics、安全区、震动、常亮、返回键、分享 | 业务判断 |

## 3. 数据结构

```python
# 世界（稀疏哈希，只存有内容的格）
walls:     dict[tuple[int, int], int]     # (x,y) -> 墙段类型
obstacles: dict[tuple[int, int], int]     # (x,y) -> 障碍类型
foods:     dict[tuple[int, int], FoodRec] # (x,y) -> 食物记录（含 chunk 归属）
snake.body: deque[tuple[int, int]]        # [0] 为蛇头，长度即蛇长

class Chunk:
    cx: int; cy: int
    seed_hash: int
    walls: list[tuple[int,int]]        # 已生成墙格
    obstacles: list[tuple[int,int]]    # 已生成障碍格
    food_slots: int                     # 3~5
    generated: bool

class Camera:
    pos: tuple[float, float]            # 世界像素坐标（视口中心）
    armed: list[bool, bool]             # x/y 各自滞回状态
    target_cell: tuple[int, int]

class AiState:
    mode: str            # 'alive' | 'score'（安全存活 / 高效吃分）
    strategy: str        # 'bfs' | 'astar'
    last_dir: tuple[int,int]
    planned_path: list[tuple[int,int]]
    pending: tuple[int,int] | None      # 下一 Tick 生效的决策
    stale_count: int                    # 陈旧决策计数
    last_tick: int

class ReplayHeader:
    version: int; seed: int; mode: str; wrap: bool; strategy: str
    tick_count: int; created_at: int
# 人类：[(tick, dir_code, event_code)]   event = 模式切换/调速
# AI  ：bytes 每 tick 1 字节决策方向 + 事件表
```

**坐标约定**：世界用整数格；渲染时乘 `grid_size` 得像素；相机用浮点像素但吸附与判定都在格上做。

## 4. 状态机

```
BOOT ──► PLAYING ──(返回键/切后台/面板暂停)──► PAUSED ──(继续, 3-2-1 倒计时)──► PLAYING
  │         │                                                                     
  │         ├──(碰撞/自撞)──► GAMEOVER ──(重开, 二次确认)──► PLAYING
  │         │                     └─────(返回)─────► HISTORY/MENU
  │         └──(首次启动)──► ONBOARDING(3 步) ──► PLAYING
  └──(加载失败/存档损坏)──► 默认配置 + PLAYING

REPLAY ──(来自 HISTORY)──► PLAYING(回放态：只读、可暂停/倍速、不可转向)
```

| 迁移 | 触发 | 副作用 |
|---|---|---|
| BOOT→PLAYING | 资源与平台层就绪 | 读 profile、恢复最高分、按种子初始化世界 |
| PLAYING→PAUSED | 返回键 / 切后台 / 面板按钮 | 冻结 tick 累加器、AI 停止、常亮保持 |
| PAUSED→PLAYING | 继续 | 3-2-1 倒计时结束后恢复；**不补帧** |
| PLAYING→GAMEOVER | 撞墙/障碍（非穿墙模式）或自撞 | 落库本局、更新最高分与成就、停 AI |
| GAMEOVER→PLAYING | 重开（二次确认） | 重置世界/蛇/AI/相机，种子可选沿用或新建 |
| PLAYING⇄REPLAY | 历史回放 | 进入只读态，禁输入转向 |
| 任意→后台 | 失焦 | 自动暂停 + 保存未完成的局内状态 |

**人类/AI 切换**：可在 PLAYING 中随时切换。切换时：清空 AI 路径、重置插值基准、保留蛇状态与 tick 相位、面板标签与按钮状态同步。

## 5. AI 设计

### 5.1 三层安全口径（与需求一一对应）

| 层 | 含义 | 落地方式 |
|---|---|---|
| L0 可证明安全 | 不因自身决策进入"无逃生"状态 | 一级可达性 + 二级空间余量 + 跟尾兜底 |
| L1 启发式最优 | 有界预算内尽量最优 | BFS/A* + 局部半径 + 增量复用 + 平局键 |
| L2 无解最优存活 | 明确边界、不死撑 | 跟尾 → 最大化可活动面积方向 → 无解即承认死亡 |

**明确边界（写进 README 与 UI 提示）**：当四个方向均导致自撞，或所在格被完全封死时，本局必然结束；AI 不承诺此情况下存活，只保证死亡前每一步都是当时最优存活步。

### 5.2 决策流水线（每 Tick 一次）

```
1. 快照：蛇头、蛇身、视口+2 圈缓存内的食物/障碍/墙
2. 裁剪：搜索半径 = min(蛇长+20, 80) 格
3. 选目标：
   - 策略=安全存活：优先保持最大可活动面积，食物为次要目标
   - 策略=高效吃分：A* 到最近可达食物（代价=步数），仍受两级校验约束
4. 搜索：BFS（存活）/ A*（吃分），平局键 (f, h, x, y)
5. 安全校验（吃食物候选必过）：
   一级：模拟吃完后的新蛇头 → 能到达蛇尾？
   二级：从新蛇头洪水填充，可活动面积 > 蛇长 + 10？（启发式加强，非证明）
6. 兜底：无安全食物路径 → 跟随蛇尾（沿尾部第二格方向逼近）
7. 防循环：状态指纹（蛇身哈希+目标+方向）重复计数超阈值 → 换目标/丢弃该分支
8. 输出：方向写入 pending，**下一 Tick 生效**
9. 超时：累计 ≥8ms 立即中止 → 按 上→右→下→左 取首个安全方向
10. 可视化：planned_path 交给 overlay 绘制（可开关）
```

### 5.3 超时与降级

- 计时以单调时钟为准，**单步硬上限 8ms**，不允许"跑完但超时"。
- 降级顺序固定 `上、右、下、左`（与当前方向相同者优先保留，避免原地抖动）。
- 降级结果同样要过 L0 兜底：若四向均不安全，选可活动面积最大的方向。

### 5.4 决策时序（关键）

- AI 计算与渲染**错峰**：tick 帧只读取 `pending`，计算发生在非 tick 帧的分片里。
- `pending` 双缓冲：新决策覆盖旧值；若本 Tick 没算出新决策，**沿用上一次**并 `stale_count += 1`（调试面板可见）。
- 陈旧超过 2 Tick 时记录告警指标，不改变规则。

### 5.5 穿墙模式

- 墙与障碍视为同类可穿越（同一碰撞分支）。
- **自撞仍死亡**：碰撞检测不因穿墙模式而跳过蛇身。
- AI 在穿墙模式下仍按"不穿墙"的保守假设搜索（避免评估过于乐观）；仅当同时满足 §7.4 的三条件时才允许穿墙一步，否则一律跟随蛇尾。

### 5.6 高速档（Tick 间隔 < 20ms，即 ≥5x）

| 约束 | 规则 | 依据 |
|---|---|---|
| 决策频率 | AI 每 2 Tick 决策一次，异步预算压到 ≤4ms | D-040 |
| 沿用前一方向前 | **必须先做 O(1) 单步安全校验**：前方格不属于蛇身、不是墙/障碍（非穿墙模式）、且该格四邻中可通行邻居数 ≥2（保证除来路外至少一个出口） | D-040(a) |
| 校验失败 | 按 上→右→下→左 确定性降级，**不得**沿用旧方向 | D-040(a) |
| 搜索半径 | `min(蛇长+20, 40)`；其余档位仍为 `min(蛇长+20, 80)` | D-048 |
| 四向全不安全 | 直接判定死亡，不假装能救（L2 边界） | D-024 |

> O(1) 校验的"可通行"口径：非墙、非障碍、非蛇身；穿墙模式下墙/障碍视为可通行。
>
> **边界（D-056，待 M3 前细化）**：若蛇头当前所在格本身可通行邻居 ≤1（即已在走廊尽头/死路里），则直接选唯一可通行方向，**不再套用"邻居 ≥2"条件**——否则会把唯一出路也判成死胡同。

## 6. 相机：死区、滞回、硬吸附

```
DEADZONE = 10 格     HYST = 2 格      SNAP = 3 格
push(x)  = max(0, DEADZONE - d(x))   # d = 蛇头到该侧视口边缘的格数
```

**逐轴独立**计算，避免斜向联动：

```
for axis in (x, y):
    d = 蛇头到该轴两侧边缘的较小格数
    if camera.armed[axis] and d > DEADZONE + HYST:   # >12 才解除
        camera.armed[axis] = False
    if d <= DEADZONE or (camera.armed[axis] and d <= DEADZONE + HYST):
        camera.armed[axis] = True
        goal[axis] = 使蛇头恰好距该侧 10 格 的相机位置
    if d < SNAP:                       # <3 格：硬吸附，跳过平滑
        camera.pos[axis] = goal[axis]
    else:
        camera.pos[axis] = lerp(camera.pos[axis], goal[axis], 1 - exp(-K*dt))
```

- 判定用 **target（蛇头格）**，不是平滑后的相机位置——否则滞回会失效。
- `K` 为平滑系数（默认值见 DECISIONS D-045 待确认区，先取 8）。
- 硬吸附必须**先于**平滑判断，保证蛇头永不出屏。
- **R3 实现方式**：相机只包一层 `Viewport`（只改 `origin`），**不改 `Viewport` 内部的坐标换算**；因此 R1 的 `world_coords` 测试不受影响，也不允许为了相机去改换算语义。

## 7. chunk 与受控随机墙壁

### 7.1 chunk 生命周期（滞回，防抖）

```
加载：视口覆盖的 chunk + 2 圈
卸载：超出 视口 + 3 圈
```

中间一圈是滞回带，避免玩家在边界来回移动时反复加载/卸载。

**缓存规模（已确认口径）**：单局同时缓存 **30~45 个 chunk**（视口跨 1~2 个 chunk 时），
内存 **<1MB**（实测 tracemalloc peak 0.37MB / 30 chunk）。原"20~30 个"是按单 chunk
视口估算的；1280×720 视口跨 2×1 chunk，稳态必然在 30~42，属于需求内部口径差异，
实现保持预加载 2 圈 / 卸载 3 圈不变（D-005）。

### 7.2 生成规则（全部纯函数：同 seed + 同坐标 = 同结果）

| # | 内容 | 生效里程碑 | 规则 |
|---|---|---|---|
| 1 | 空网格 | **M1** | 单 chunk 只预生成 32×32 全可通行网格，**无墙、无障碍** |
| 2 | 食物 | **M1** | 每 chunk 3~5 个，只落在可通行格；被吃后同 chunk 补充 |
| 3 | 障碍 | M2 | 密度约 5%，仅 chunk 内部；chunk 边界整行/整列禁止 |
| 4 | 受控随机墙 | M2 | 每 chunk 0~2 条、长 3~8 格、不贴边界、墙/障碍间留 ≥1 格、局部洪水填充校验 |
| 5 | 出生保护 | M2 | 出生点周边 3×3 chunk 无墙无障（M1 本就无墙无障，天然满足） |
| 6 | 随机源 | M1 起 | `hash(seed, x, y)` 派生的确定性 PRNG，禁止使用全局 `random` 状态 |

> **M1 边界（重要）**：单 chunk 是**预生成与渲染范围，不是物理边界**。世界逻辑无限，蛇走出单 chunk 后，该区域按"无障碍、无食物、可通行"处理，**不触发任何死亡**。M2 引入 ChunkManager 后才按圈数加载。M1 禁止写"撞 chunk 边界死亡"这类临时逻辑。
>
> **确定性边界（D-057）**：同种子只保证**初始生成**一致；运行时补充食物的位置取决于**吃完顺序**，因此复现必须依赖回放事件（种子 + 逐 Tick 输入/决策），而不是只给一个种子。验收时不得用"同种子 + 不同操作序列"来要求一致。
>
> **通行判定唯一入口**：`World.is_passable(cell)`。`Snake` 及后续 AI **禁止**直接调用 `gen.is_passable`；M2 接地形时只改 `World` 一处。

### 7.3 边界与卸载

- 卸载前把该 chunk 内的食物记录归并到相邻 chunk 或丢弃（不产生"幽灵食物"）。
- 蛇身跨 chunk 时只更新坐标，不做对象迁移（蛇身是全局队列，不属于任何 chunk）。

### 7.4 穿墙模式下 AI 放宽的判据（三条件 AND，缺一不可）

默认行为：AI 在穿墙模式**仍按不穿墙搜索**。仅当以下三条**同时**成立，才允许"穿墙一步"：

| # | 条件 | 判定口径 |
|---|---|---|
| ① | 不穿墙路径搜索失败 | BFS/A* 在局部半径内找不到任何合法路径 |
| ② | 穿墙后落点满足二级校验 | 连通面积 > 蛇长 + 10；连通统计**忽略障碍与墙**（视为可通行），**蛇身仍为不可通行** |
| ③ | 落点不在蛇身集合内 | 以本 Tick 移动后的蛇身为准，含蛇头即将占用的格 |

任一条不满足 → **一律跟随蛇尾**，不得穿墙。

## 8. 像素缩放与平台适配

```
density   = Android: DisplayMetrics.density；桌面: Metrics.density
grid_size = max(16, round(32 * density))       # 整数，保证像素对齐
视口格数   = floor(可用宽 / grid_size), floor(可用高 / grid_size)
```

- **整数缩放 + Nearest 过滤**：禁用线性插值，否则像素糊边。
- 可用区域 = 屏幕 − 安全区（刘海/挖孔/圆角/手势条）。
- 若视口宽或高 < 21 格：先提示"屏幕过小"，再允许降一档 `grid_size`（不低于 16），仍不满足则拒绝进入对局并给出说明。
- 桌面调试用 `Window.size` + `Metrics.dpi` 模拟不同密度档（1.0 / 1.5 / 2.0 / 3.0）。

## 9. 渲染与插值

- 逻辑 Tick 默认 10Hz，渲染跟随屏幕上限（目标 60FPS 起，逐步验收 90~120 能力）。
- 蛇身插值（`t = 本 tick 已过时间 / tick 间隔`）：

| 段 | 插值 | 说明 |
|---|---|---|
| 头与中间节 `i` | `lerp(curr[i+1], curr[i], t)` | 即上一 Tick 位置 → 本 Tick 位置 |
| 尾（未吃食物） | `lerp(curr[-1], curr[-2], t)` | 尾巴整体前移一格 |
| 尾（吃到食物） | `curr[-1]` 不动 | 记录 `ate_food`，长度 +1 在本 Tick 生效 |

- 绘制顺序：背景 → 网格线（可关）→ 障碍 → 墙 → 食物 → 蛇 → AI 路径 → UI 叠加。
- **不要**每个格建 Widget；用 Canvas 指令 + 对象池，仅重建变化部分。

## 10. 性能预算与降级

### 10.1 单帧预算（16.67ms）

| 项 | 预算 | 约束 |
|---|---|---|
| 渲染 | ≤5ms | Canvas 批量、视口裁剪、对象池 |
| 逻辑 | ≤2ms | 单 Tick；10x 调速时可能一帧 2 次 → ≤4ms |
| AI | ≤8ms | 硬超时，与 chunk 错峰 |
| chunk | ≤3ms | 预加载分摊到非 tick 帧 |
| 输入 | ≤1ms | 事件驱动，不轮询 |

**算术自洽**：AI 与 chunk 错峰 → 同帧最多跑其一，单帧异步合计 ≤8ms。
- 非 tick 帧：渲染 5 + 输入 1 + 异步 8 = 14ms
- tick 帧：渲染 5 + 逻辑 2 + 输入 1 + 异步 8 = 16ms
- 10x 档双 tick 帧：5 + 4 + 1 + 异步 → 必须把异步压到 ≤4ms（D-040，已锁定）

> **已确认（v1.1 复核）**：tick 帧 16ms / 非 tick 帧 14ms 为本项目架构基线。

### 10.2 55+FPS 底线

帧时间 ≤18ms 视为达标；连续 3 秒 p95 >18ms 触发降载。

### 10.3 分级降载（严格 5 级，按顺序，不跳级）

| 级 | 动作 | 说明 |
|---|---|---|
| 1 | 关路径可视化 + 关调试面板 | 纯绘制裁剪，不影响任何规则 |
| 2 | 蛇身插值：逐节 → 整体 | 只对蛇头插值，其余节直接吸附到当前格；减少每帧计算与绘制指令 |
| 3 | AI 思考频率：每 2 Tick → 每 3 Tick | 仍受 8ms 硬超时约束 |
| 4 | 视口外 chunk 预加载：2 圈 → 1 圈 | 削生成尖峰，可能带来短暂边界空白 |
| 5 | 渲染帧率：60 → 55 | **仅当 1~4 用尽且仍超预算**；**55 为硬底线，不得再降** |

第 5 级之后仍不达标 → 出**瓶颈报告**（profiler 数据、热点函数、真机型号与温升），**不降帧率、不改架构**。

> 第 3 级与 D-040 高速档规则可能叠加；叠加时取更保守的思考频率。

### 10.4 M5 真机口径

测量：某中端安卓机（型号在性能记录中写明）连续 10 分钟，记录帧时间 p50/p95/max、掉帧率、温升与降频时刻。**90~120FPS 只作为渲染上限能力报告，不作为通过与否的唯一标准。**

## 11. 调度与线程模型

- **单进程单线程**：Kivy 主循环。不引入 threading 做 AI（GIL 下纯 Python 搜索无法真正并行，徒增锁复杂度）。
- AI 与 chunk 用**分片**方式挂在 `Clock` 的 idle 回调上，单片 ≤2ms，累计不超过各自预算。
- 原因：10Hz tick 间隔 100ms，AI 8ms 不在关键路径上，只要不塞进渲染帧即可。
- **硬约束（D-047）**：禁止 `threading`、`concurrent.futures`、`multiprocessing`；所有并发只允许 Kivy `Clock` 分片调度。理由：GIL 下纯 Python 搜索拿不到并行收益，反而引入锁与竞态。

## 12. 风险清单

| 编号 | 风险 | 触发信号 | 缓解（不含换框架、不含 C 扩展前置） |
|---|---|---|---|
| RK1 | Kivy Canvas 渲染 ≤5ms 守不住（蛇身节数增长 + 网格线 + 路径叠加） | M1/M5 帧时间 p95 >16.67ms | 单 Widget + 指令池 + 视口裁剪 + 路径节点上限 + 分级降载 |
| RK2 | Android 平台层（沉浸式/安全区/返回键/常亮/分享）全靠 pyjnius，厂商差异大 | 桌面正常、真机异常 | `platform_layer/` 隔离 + 桌面降级实现；M1 打通最小 pyjnius 链路 |
| RK3 | 时序打架：10Hz Tick × 8ms × 0.5~10x 调速 × 下一 Tick 生效 | 高速档 AI 超时率飙升、决策陈旧 | 决策双缓冲 + 陈旧计数 + 高速档降频（D-040 待确认） |
| RK4 | 两级校验是启发式，构造不出反例不代表不存在 | 构造场景测试出现"校验通过后 1~2 Tick 内死亡" | 场景集持续回归 + UI 明示"启发式" + 跟尾兜底 |
| RK5 | 回放漂移（浮点/时间/随机混入） | 同回放两次结果不同 | 全整数决策 + 种子驱动 + 只依赖 Tick 序列 |
| RK6 | 存档 schema 演进导致旧档读不出 | 升级后启动崩溃 | 版本号 + 不识别字段忽略 + 损坏降级默认 + 导入导出即备份 |
| RK7 | 打包链（SDK/NDK/ABI/target 33）失败成本高 | `buildozer android debug` 报错 | M5 之前先在 M1 做一次空包构建验证；锁 buildozer.spec 版本 |

## 13. 目录结构
```
snake_android/
├── main.py                # 入口（把 src/ 加进 sys.path）
├── buildozer.spec
├── requirements.txt
├── README.md
├── docs/                  # 只放文档：CONTEXT / ARCH / ACCEPTANCE / DECISIONS / KNOWN_ISSUES
├── src/
│   ├── app/               app.py  constants.py
│   ├── core/              tick.py snake.py game.py camera.py world.py chunk.py gen.py
│   │                      collision.py rng.py scale.py viewport.py
│   ├── ai/                planner.py search.py safety.py policy.py loopguard.py   (M3 起)
│   ├── view/              game_canvas.py renderer.py joystick.py path_overlay.py theme.py
│   ├── ui/                panel.py screens/ dialogs.py onboarding.py font_scale.py (M4 起)
│   ├── data/              storage.py replay.py achievements.py history.py         (M4 起)
│   └── platform_layer/   android.py desktop.py
├── tools/                 perf_record.py seed_check.py replay_verify.py
└── tests/                 test_ai_safety.py test_seed.py test_camera.py
                           test_grid_scale.py test_replay.py test_chunk.py
```

约定：`docs/` 只放文档，`src/` 只放代码，`tests/` 平铺对应 `core/ai` 的纯逻辑测试（不依赖 Kivy）。

## 14. M3 AI 只读接口（已定稿，M3 开工不再改）

AI 只能通过下列接口访问世界，**禁止直接碰 `_blocked` / `_foods` / `_chunks`**：

| 接口 | 签名 | 语义 |
|---|---|---|
| 阻挡查询 | `World.query_blocked_in_rect(x0, y0, x1, y1) -> set[cell]` | 矩形内障碍∪墙壁；含端点，坐标可反序 |
| 食物查询 | `World.foods_in_rect(x0, y0, x1, y1) -> set[cell]` | 矩形内食物；含端点，坐标可反序 |
| 通行判定 | `World.is_passable(cell, ignore_blocked=False) -> bool` | 唯一入口；ignore_blocked 只让地形让路 |
| 蛇身 | `Snake.occupied` / `Snake.head` / `Snake.tail` / `Snake.body` | 只读 |
| 模式 | `Game.wrap_mode` | 穿墙模式开关 |

约束：
- 所有查询必须 O(视口规模) 或 O(1)，不允许 AI 遍历全量 `_blocked`。
- AI 的搜索半径 `min(蛇长+20, 80)` 由调用方保证，接口不做裁剪。
- 这些签名一旦 M3 开工即冻结；变更需走 DECISIONS 新编号。

## 15. AI 调度节奏（M3，已定稿）

- **AI tick 与逻辑 tick 独立调度**，AI tick 频率 **≤** 逻辑 tick 频率；AI 结果只写入待生效方向。
- **生效语义（KI-016，方案 B）**：本 tick 计算的方向作用于**本次 step**；真正的"下一步生效"由 `Snake.pending` 保证（`set_direction` 只写 pending，`step()` 才消费）。`reuse` 只发生在"本 tick 没算出方向"（超时/无路）时。
- 10x 档（D-040）：每 **2 个逻辑 tick 决策 1 次**，异步预算 **≤4ms**，搜索半径 `min(蛇长+20, 40)`；其余档位每 tick 决策 1 次、8ms、`min(蛇长+20, 80)`。
- 决策未完成时：**沿用上一有效方向 + O(1) 单步安全校验**（前方格不在蛇身、不是地形阻挡、四邻除来路外至少 1 个可通行）；校验失败按 上→右→下→左 降级。
- 硬超时 8ms（高速档 4ms）：每扩展 100 节点检查一次时间，超时中断并走降级。
- 优先级：安全校验 > 吃食物 > 跟尾 > 兜底；任一阶段超时都不得让蛇走进必然死亡的方向。
