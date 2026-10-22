# Snake（安卓横屏贪吃蛇 / Kivy）

**版本：v1.0-m1（tag `m1-done`）** ｜ Python + Kivy 2.3.0 ｜ 当前进度：**M1 已冻结，待 M2**

M1 验收结果见 [docs/M1-ACCEPTANCE.md](docs/M1-ACCEPTANCE.md)（14 条全绿）。

## 目录

```
main.py              入口（--smoke <秒> [--demo]）
src/app/             constants.py（常量唯一来源）  app.py（App、键盘、主循环、smoke）
src/core/            rng gen chunk world scale viewport snake tick game camera
src/platform_layer/  desktop.py（density / 窗口尺寸；M5 加 android.py）
src/view/            game_canvas.py（网格 + 食物 + 蛇 + 死亡叠层 + 相机）
tests/               pytest：坐标 / 缩放 / chunk / 蛇 / tick / 对局 / 相机
docs/                CONTEXT / ARCH / ACCEPTANCE / DECISIONS / KNOWN_ISSUES
docs/evidence/       GUI 实跑日志与截图
```

## 环境（必须 Python 3.8~3.12）

本机默认 Python 3.14 装不了 Kivy 2.3.0，仓库已用 3.11 建好 `.venv`：

```bash
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 运行

```bash
.\.venv\Scripts\python.exe main.py                        # 正常游玩
.\.venv\Scripts\python.exe main.py --smoke 12             # 12 秒后退出并打印诊断
.\.venv\Scripts\python.exe main.py --smoke 12 --speed 10  # 10x 高速档（验证蛇头不出屏）
.\.venv\Scripts\python.exe main.py --smoke 3 --interp     # 连续 3 帧插值截图
.\.venv\Scripts\python.exe main.py --smoke 4 --demo       # 吃食物 + 死亡叠层截图
python -m pytest -q                                       # 103 项单测（不需要 Kivy）
```

操作：方向键 / WASD 转向；`R` 重开；禁止 180° 反向。

## `--smoke` 语义（明确）

- `--smoke N` 中的 **N 是秒**，不是 tick。10Hz 逻辑下大约 **N×10 个 tick**。
- 行为：启动窗口 → 0.3s 打印一次诊断 → 在 25%/50%/75% 处各截一帧（`follow1..3`）→ 结束前打印 final 段（`ticks` / `state` / `eaten` / `camera`）→ 自动退出。
- `--smoke N --demo`：额外在 0.6s 注入一个"身前食物"、1.4s 截 `eat.png`、2.0s 构造自撞、2.6s 截 `dead.png`；此时不再截 follow 帧。
- 截图写到 `docs/evidence/`，Kivy 会自动在文件名后加 `0001` 序号。

## 当前范围（R4）

- 相机：死区 10 格、偏移 `max(0, 10-距边缘格数)`、x/y 独立、滞回 2 格、`<3` 格硬吸附、`alpha = 1-exp(-dt*8)`
- 插值：`t` 取自 `TickClock.progress`（死亡冻结 1.0）；头 `body[1]→body[0]`、中间节 `body[i+1]→body[i]`、尾 `prev_tail→body[-1]`（吃到食物时尾不动）
- 蛇身矩形以**格中心**为锚点绘制，支持非整格偏移
- 走出单 chunk 不死亡（D-054）

**尚未做**：多 chunk（M2）、障碍/墙壁（M2）、AI（M3）、UI 面板（M4）、打包（M5）。

## 关键约束

- `docs/DECISIONS.md` 是唯一真相源，A 区条目未经确认不得修改
- 通行判定只走 `World.is_passable`（M2 单点接入）
- 同种子只保证**初始生成**一致；运行时补充位置取决于吃完顺序，靠回放事件复现（D-057）
