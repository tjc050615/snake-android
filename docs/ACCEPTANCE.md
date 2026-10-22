# ACCEPTANCE

> 版本：v1.0 ｜ 状态：待复核
> 规则：每条验收必须有**可复现命令 + 可观测输出**；不能自动化的写清人工步骤与判定依据。
> 阶段未全绿不得进入下一阶段；允许带 P2 及以下问题并登记到 KNOWN_ISSUES.md。

## 0. 通用命令

| 用途 | 命令 |
|---|---|
| 桌面运行 | `python main.py` |
| 全量单测 | `pytest -q` |
| 指定模块单测 | `pytest -q -k <关键字>` |
| 性能记录 | `python -m tools.perf_record --seconds 600 --out perf.csv` |
| 种子复现校验 | `python -m tools.seed_check --seed <int> --ticks 500` |
| 回放一致性校验 | `python -m tools.replay_verify --file <replay.json>` |
| 打包 | `buildozer -v android debug` |
| 安装 | `adb install -r bin/*.apk` |
| 真机日志 | `adb logcat -s snake:*` |

---

## M1 世界坐标 + 单 chunk 预生成

| ID | 验收条件 | 命令 / 判定 |
|---|---|---|
| M1-1 | 世界坐标为整数格，负坐标与跨 0 正常；无浮点格坐标参与判定 | `pytest -q -k "world_coords"` |
| M1-2 | 单 chunk 预生成 32×32 空网格（全可通行、无墙无障）+ 食物 3~5 个；重复调用结果一致（纯函数） | `pytest -q -k "chunk_pregen"` |
| M1-3 | 蛇每 Tick 前进 1 格，默认 10 Tick/秒（误差 <5%） | `python main.py` 观察 + `pytest -q -k tick_rate` |
| M1-4 | 仅"自撞"死亡；吃食物 = 长度 +1 且 `ate_food=True`；M1 **无**撞墙/撞障碍判定 | `pytest -q -k collision` |
| M1-5 | 相机死区：距边缘 >10 格相机不动；10 格处 push=0，9 格 push=1，8 格 push=2 | `pytest -q -k "deadzone or push"` |
| M1-6 | 相机滞回：10~12 格之间往返不产生启停抖动 | `pytest -q -k "hysteresis or overshoot"` |
| M1-7 | 蛇头距边缘 <3 格硬吸附，无平滑延迟，蛇头不出屏 | `pytest -q -k "snap"` |
| M1-8 | x/y 独立：仅 x 越界时 y 不动 | `pytest -q -k "axes or independent"` |
| M1-9 | `grid_size = max(16, round(32*density))`；density 1.0/1.5/2.0/3.0 分别得 32/48/64/96 | `pytest -q -k grid_scale` |
| M1-10 | 整数缩放、Nearest 过滤，格子边界无半像素模糊 | 人工判定：`docs/evidence/smoke0001.png`（1920×1080 / grid 48 / 格线清晰） |
| M1-11 | 蛇身插值：中间节 `curr[i+1]→curr[i]`；未吃食物尾 `curr[-1]→curr[-2]`；吃到食物尾不动且 `ate_food` 置位 | `pytest -q -k "interp or segment"` |
| M1-12 | 键盘方向键转向，禁止 180° 反向 | `pytest -q -k "reverse"`（已覆盖）+ `python main.py` 人工 |
| M1-13 | 重开：世界/蛇/AI/相机全部重置，无残留状态 | `pytest -q -k "reset or restart"` |
| M1-14 | 横屏锁定：桌面窗口不可竖屏，安卓端方向不随重力变化 | 桌面侧已验（无竖屏分支、16:9 窗口，见 `docs/evidence/smoke-log.txt`）；安卓侧留 M5 真机复验 |
| M1-15 | 食物只落在可通行格；每 chunk 维持 3~5 个；被吃后同 chunk 补充，数量回到 3~5 | `pytest -q -k food` |
| M1-16 | 蛇走出单 chunk 区域不死亡、不报错；该区域按可通行且无食物处理 | `pytest -q -k out_of_chunk` |

> M1 无墙、无障碍："撞墙/撞障碍死亡"属 M2 验收（M2-4 起）。

## M2 多 chunk 无限加载 + 受控随机墙壁

| ID | 验收条件 | 命令 / 判定 |
|---|---|---|
| M2-1 | 视口 +2 圈预加载，超 3 圈卸载；边界来回移动不抖动 | `pytest -q -k chunk_lifecycle` |
| M2-2 | 同 seed 同坐标 → 同障碍/墙/食物（跨进程一致） | `python -m tools.seed_check --seed 1 --ticks 200` |
| M2-3 | 每 chunk 障碍密度 5% ±1.5% | `pytest -q -k obstacle_density` |
| M2-4 | chunk 边界整行/整列无任何障碍与墙 | `pytest -q -k boundary_clear` |
| M2-5 | 受控墙：每 chunk 0~2 条、长 3~8、横/竖/拐角、不贴边界、与墙/障碍留 ≥1 格 | `pytest -q -k wall_rules` |
| M2-6 | 墙壁生成后局部洪水填充校验通过；构造"会切断通道"的种子时该墙被丢弃 | `pytest -q -k wall_connectivity` |
| M2-7 | 出生点周围 3×3 chunk 无墙无障碍 | `pytest -q -k spawn_clear` |
| M2-8 | 每 chunk 食物 3~5 个；被吃后同 chunk 补充，不产生幽灵食物 | `pytest -q -k food_refill` |
| M2-9 | 连续移动 2000 格，无重复实体、无丢失、无卡顿尖峰 | `python -m tools.perf_record --scenario stream --seconds 120` |
| M2-10 | 全局连通性：随机 200 个可通行格，任意两点可经 BFS 连通 | `pytest -q -k global_connectivity` |

## M3 AI 与安全策略 + 路径可视化

| ID | 验收条件 | 命令 / 判定 |
|---|---|---|
| M3-1 | BFS 与 A* 均可达；A* 平局键 `(f,h,x,y)` 输出确定且可复现 | `pytest -q -k "search_tiebreak"` |
| M3-2 | 局部搜索半径 = `min(蛇长+20, 80)`，不越界读取 | `pytest -q -k search_radius` |
| M3-3 | 一级校验：模拟吃完后新蛇头可达蛇尾；不可达时该食物被拒绝 | `pytest -q -k safety_l1` |
| M3-4 | 二级校验：洪水填充面积 > 蛇长+10；不满足时拒绝该食物（代码注释与 UI 均标注"启发式加强"） | `pytest -q -k safety_l2` |
| M3-5 | 无安全食物路径时跟随蛇尾，且能持续存活 ≥ N Tick（N 由场景定义） | `pytest -q -k follow_tail` |
| M3-6 | 8ms 硬超时：人为注入慢搜索，超时立即按 上→右→下→左 返回首个安全方向 | `pytest -q -k timeout_fallback` |
| M3-7 | 决策在下一 Tick 生效：本 Tick 提交的方向不受当帧 AI 影响 | `pytest -q -k decision_tick` |
| M3-8 | 防循环：构造往返场景，AI 在阈值内打破循环 | `pytest -q -k loop_guard` |
| M3-9 | 穿墙模式：可穿墙/障碍，自撞仍死 | `pytest -q -k wrap_mode` |
| M3-10 | 双策略切换（安全存活 / 高效吃分）行为可区分（同一局面下吃分策略步数更短） | `pytest -q -k strategy_diff` |
| M3-11 | 路径可视化开关生效，关闭后零绘制开销（对比帧时间无差异） | 人工 + `perf_record` 对比 |
| M3-12 | 人类/AI 一键切换不破坏蛇状态与 Tick 相位 | `pytest -q -k mode_switch` |
| M3-13 | 构造场景集（≥12 个：死角、单通道、贴尾、长蛇、满屏障碍、穿墙边界）全部通过且无"校验通过后 1~2 Tick 内死亡" | `pytest -q -k scenario_suite` |

## M4 完整 UI · 设置 · 历史 · 种子 · 统计 · 调试 · 持久化 · 成就 · 回放

| ID | 验收条件 | 命令 / 判定 |
|---|---|---|
| M4-1 | 70/30 分栏；游戏区与面板区触控完全隔离（面板点击不转向） | 人工 + `pytest -q -k touch_isolation` |
| M4-2 | 摇杆固定左下、仅游戏区响应、死区 15%、连续无跳变 | `pytest -q -k joystick` |
| M4-3 | 游戏区四向滑动转向；滑动阈值与误触抑制生效 | 人工 |
| M4-4 | 返回键弹暂停菜单；后台切出自动暂停；边缘不误触系统返回 | 真机人工 |
| M4-5 | 暂停恢复 3-2-1 倒计时；退出/重开二次确认 | 人工 |
| M4-6 | 屏幕常亮在游戏与暂停态生效，退出后释放 | 真机人工 |
| M4-7 | 新手引导 3 步，可跳过，仅首次展示 | 人工 + `pytest -q -k onboarding` |
| M4-8 | 设置项齐全：音效/震动（开关+强度/音量）、主题三套、帧率显示、性能模式（默认均衡）、触控灵敏度、摇杆死区、恢复默认（不动历史/成就/最高分） | 人工逐项 + `pytest -q -k settings_defaults` |
| M4-9 | 可访问性：蛇头高亮纹理、网格开关、字体大小调节不溢出安全区 | 人工（三种字体档 × 三套主题） |
| M4-10 | 调试面板默认关闭；开启显示 FPS、相机 target/current、蛇头格坐标、chunk 边界、AI 路径节点数；关闭后帧时间无可测差异 | `perf_record` 开/关对比，差值 <0.2ms |
| M4-11 | 历史保留最近 20 局，字段完整（模式/时长/分数/种子/时间/是否 AI/是否穿墙） | `pytest -q -k history` |
| M4-12 | 一键回放：人类存输入序列+时间戳+模式切换+调速；AI 存种子+每 Tick 1 字节方向+模式/策略切换 | `pytest -q -k replay_record` |
| M4-13 | 回放支持暂停与倍速，不支持拖拽后退；文件 ≤100KB（超限截断策略生效） | `python -m tools.replay_verify --file <f>` |
| M4-14 | 回放一致性：同回放两次结果逐 Tick 一致 | `pytest -q -k replay_deterministic` |
| M4-15 | 种子显示/复制/输入合法种子可复现同局 | `pytest -q -k seed_reproduce` |
| M4-16 | 导出并系统分享，且不申请存储权限 | 真机人工 + `adb shell dumpsys package <pkg> \| grep permission` |
| M4-17 | 最高分持久化；5 个成就判定与进度条正确；V1 无每日挑战入口 | `pytest -q -k achievements` |
| M4-18 | config.json / profile.json 损坏时降级默认且不崩溃；导入导出备份可用 | `pytest -q -k storage_corrupt` |
| M4-19 | 隐私说明、版本号、更新日志入口可达 | 人工 |

## M5 安卓打包 + 性能优化

| ID | 验收条件 | 命令 / 判定 |
|---|---|---|
| M5-1 | `buildozer -v android debug` 产出 APK，`adb install` 成功启动 | 上述命令 |
| M5-2 | 权限仅 VIBRATE；`minSdk 23`、`targetSdk 33` | `aapt dump badging bin/*.apk` |
| M5-3 | 真机横屏锁定、沉浸式全屏、刘海/挖孔安全区正确 | 真机人工 |
| M5-4 | 帧时间 p50/p95/max + 掉帧率 + 10 分钟热稳定记录落盘 | `python -m tools.perf_record --seconds 600 --out perf_m5.csv` |
| M5-5 | 达到 55+FPS 底线；90~120FPS 作为渲染上限能力如实报告（不达标出瓶颈报告） | 同上 CSV + 报告 |
| M5-6 | 降载策略生效：模拟低电量/温控触发后按 §10.3 顺序降级，可恢复 | 人工 + 日志 |
| M5-7 | 崩溃日志落盘并可读；崩溃后重启降级默认配置 | 人工注入崩溃 |
| M5-8 | 单测全绿：AI 安全、种子复现、相机死区、像素缩放、存档回放一致性 | `pytest -q` |
| M5-9 | 交付物齐全（目录/requirements/buildozer.spec/README/打包排错/性能记录） | 人工核对清单 |

---

## 测试矩阵（必须存在）

| 测试文件 | 覆盖 |
|---|---|
| `tests/test_ai_safety.py` | 一级/二级校验、跟尾、超时降级、构造场景集 |
| `tests/test_seed.py` | 同种子同世界、跨进程一致、种子解析合法性 |
| `tests/test_camera.py` | 死区边界值、滞回、硬吸附、x/y 独立、平滑帧率无关 |
| `tests/test_grid_scale.py` | grid_size 公式、21 格下限、整数对齐 |
| `tests/test_replay.py` | 录制/回放一致性、100KB 截断、不可拖拽 |
| `tests/test_chunk.py` | 加载卸载、边界无墙、密度、连通性 |

## 验收纪律

1. 失败条目必须登记 KNOWN_ISSUES.md（现象 + 复现命令 + 归属阶段 + 级别）。
2. P0 阻断项不得带入下一阶段；P1 必须附修复计划。
3. 验收数据（CSV、截图、日志）落盘到 `docs/acceptance/`，不接受口头通过。
4. 每条命令必须能在干净环境中复现（写清依赖安装步骤）。
