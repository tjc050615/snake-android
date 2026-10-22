# R5B 真机数据回填指南

> 目标：一次跑完就能验收，避免缺数据重跑。采集环境：Android 真机 + `adb`。
> 产出：`docs/evidence/r4-device.md`（本指南末节模板）+ 截图 + 原始日志。

## 0. 前置

```bash
adb devices                     # 确认设备已授权
adb install -r bin/snake-*-debug.apk
adb shell am start -n org.example.snake/org.kivy.android.PythonActivity
adb logcat -c                   # 清空旧日志
adb logcat -s python:* SDL:* > docs/evidence/r4-logcat.txt &
```

## 1. 必采数据（缺一不可）

| # | 数据 | 命令 | 填到 |
|---|---|---|---|
| 1 | 启动日志（含字体加载） | `adb logcat -d -s python:* \| tail -100` | `r4-device.md` §A |
| 2 | 屏幕信息（分辨率/密度/刘海） | `adb shell wm size`、`adb shell wm density` | §A |
| 3 | FPS（粗测） | `adb shell dumpsys gfxinfo org.example.snake \| head -40` | §B |
| 4 | 帧时间 p50/p95/p99 | `adb shell dumpsys gfxinfo org.example.snake framestats` | §B 表 |
| 5 | 内存 | `adb shell dumpsys meminfo org.example.snake \| grep -E "TOTAL\|Native"` | §C 表 |
| 6 | 温度 | `adb shell cat /sys/class/thermal/thermal_zone*/temp` | §C 表 |
| 7 | APK 体积 | `ls -lh bin/*.apk` | §A |

**10 分钟热稳定**：从 t=0 起每 2 分钟采一次（FPS/内存/温度），共 5 组，填 §C 表。

## 2. 必截的 5 张图

| 图 | 内容 | 文件名 |
|---|---|---|
| 1 | 首页/开局 | `docs/evidence/r4-home.png` |
| 2 | 游戏进行中（分栏 + 摇杆） | `r4-game.png` |
| 3 | AI 模式 + 统计面板 | `r4-ai-stats.png` |
| 4 | 设置页（中文 + 主题） | `r4-settings.png` |
| 5 | 回放播放中 | `r4-replay.png` |

截图命令：`adb exec-out screencap -p > docs/evidence/r4-home.png`

## 3. 功能清单（对照 `docs/R4-DEVICE-CHECKLIST.md` 打勾）

20 项逐项打勾，失败项必须附 `adb logcat` 片段与截图。

## 4. 关键判定线（R5B 分级判定）

> 注意：平均 55fps = 平均帧时间 18.18ms，与 p99<16ms 不可能同时成立。因此按**四级**判定。

**判定规则（写死，避免扯皮）**：FPS 与 p99 **必须同时满足**某一级才算该级；
两者落在不同级时**取更严（更差）的一级**。

| 等级 | 平均 FPS | p99 帧时间 | 结论 |
|---|---|---|---|
| **目标** | ≥ 90 | ≤ 11.1ms | 达标，打 `m5-done` |
| **及格** | ≥ 60 | ≤ 16.67ms | 通过，记录为可优化 |
| **底线** | ≥ 55 | ≤ 20ms | 通过但记录瓶颈（M5 收尾） |
| **不及格** | < 55 或 > 20ms | — | 出降载方案再验证 |

示例：
- `62fps + p99 18ms` → FPS 及格、p99 底线 → **底线**
- `92fps + p99 15ms` → FPS 目标、p99 及格 → **及格**
- `95fps + p99 10ms` → **目标**
- `50fps + p99 10ms` → FPS 不及格 → **不及格**

**自动判定**（回填后跑）：

```bash
python tools/check_r5b.py --check-only   # 先查数据齐全（7 项 + 5 图 + 热稳定表）
python tools/check_r5b.py                # 再判级，退出码 0=通过 1=不及格/缺数据
```

其它硬指标：

| 指标 | 通过线 | 说明 |
|---|---|---|
| 10 分钟内存增长 | < 50MB | 超过视为泄漏 |
| 温度 | < 45℃ | 超过记录但不阻塞（限频会降帧） |
| APK 体积 | < 30MB | 字体 8.33MB，KI-020 |
| 中文渲染 | 无方块 | Noto 进包校验（CI 已断言） |

## 5. `docs/evidence/r4-device.md` 模板

```markdown
# R4/R5B 真机验证记录

- 设备：______  系统：______  分辨率/密度：______  构建：______
- APK：______（大小 ____ MB）
- 采集时间：______

## A. 启动与环境
- 启动日志：`docs/evidence/r4-logcat.txt`（前 100 行）
- 字体加载：☐ 正常  ☐ 方块（附截图）
- 刘海/安全区：☐ 无遮挡

## B. 帧时间（10 分钟热稳定）
| 时间 | FPS | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|---|
| 0 min | | | | |
| 2 min | | | | |
| 5 min | | | | |
| 10 min | | | | |

## C. 内存与温度
| 时间 | 内存 (MB) | 温度 (℃) |
|---|---|---|
| 0 min | | |
| 2 min | | |
| 5 min | | |
| 10 min | | |

## D. 20 项功能清单
（逐项 ☑/☐ + 备注，失败项附日志）

## E. 截图
- r4-home.png / r4-game.png / r4-ai-stats.png / r4-settings.png / r4-replay.png

## F. 结论
- p99 帧时间：____ ms（通过线 <16ms）
- 平均 FPS：____（通过线 ≥55）
- 阻塞问题：
```

## 6. 常见坑

| 现象 | 处理 |
|---|---|
| `adb cannot connect` | `adb kill-server && adb start-server`，重新授权 USB 调试 |
| `gfxinfo` 无数据 | 先让游戏跑 60s 再 dump；或 `--enable-gpu-profiling` |
| 温度文件为空 | 部分机型在 `/sys/class/thermal/thermal_zone*/temp`，用 `adb shell ls /sys/class/thermal` 找 |
| 截图全黑 | 用 `adb exec-out screencap -p`（不要 `adb shell screencap` 重定向） |
| 日志刷屏 | 先 `adb logcat -c`，再只抓 `python:* SDL:*` |

## 7. 回填后怎么做

1. 把 §A–§E 填进 `docs/evidence/r4-device.md`；
2. 5 张截图放 `docs/evidence/`；
3. 告诉我“数据已回填”，我按 §4 的判定线做 R5B 验收：
   - 全部通过 → 打 `m5-done`（并视情况打 `m5-pack`）；
   - 未通过 → 出优化清单（先降 AI 预算 7.0→6.0ms，再考虑 render 批处理/FBO）。
