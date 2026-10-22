# M4 验收表（UI / 交互 / 持久化 / 回放 / 主题）

> 证据均为仓库内可复现命令 + `docs/evidence/` 截图。测试环境：Python 3.11（Kivy 2.3.0）与系统 Python（无 Kivy，跑纯逻辑测试）。

## 0. 总览

| 项 | 结果 |
|---|---|
| 测试 | **356 passed, 1 skipped** |
| 轮次 | R1 分栏/触控/设置 → R2 历史/种子/回放/成就 → R3 面板/调试/回放驱动/主题 |
| tag | `m4-done` |

## 1. 分栏与触控（R1）

| 验收点 | 证据 |
|---|---|
| 70/30 分栏误差 <1px | `test_split_ratio_within_one_pixel`、`docs/evidence/r1_split_annotated.png` |
| 面板点击不转向 | `test_touch_isolation` |
| 摇杆死区 15% | `test_joystick_deadzone` |
| 四向滑动阈值 | `test_swipe_threshold`、`test_swipe_diagonal_picks_dominant_axis` |
| 按钮方案 A（覆盖层 + Button font_name） | `docs/KNOWN_ISSUES.md` KI-012 已关闭；`docs/evidence/settings0001.png` |
| 摇杆/滑动/键盘/面板按钮在回放与确认态全部屏蔽 | `test_replay_blocks_keyboard_joystick_swipe` |

## 2. 设置与可访问性（R1）

| 验收点 | 证据 |
|---|---|
| 设置项齐全（音效/震动/音量/强度/主题/帧率/性能模式/灵敏度/死区/恢复默认） | `docs/evidence/settings0001.png` |
| config 持久化 + 损坏降级 + version | `test_config_survives_restart`、`test_config_corrupt_falls_back_to_defaults` |
| 恢复默认不动 profile | `test_settings_reset_keeps_profile` |
| 滚动：字号 24 仍可访问全部项 | `test_settings_panel_scrollable_at_max_font`、`docs/evidence/settings0003.png` |
| 蛇头高亮 / 网格开关 | `docs/evidence/settings0003.png` |
| 全 UI 中文化 / 无硬编码 | `test_no_hardcoded_cn`、`test_no_hardcoded_cn_detects_fstring` |
| 字体混排（Noto Sans SC） | `docs/evidence/history0001.png`、`settings0005.png` |

## 3. 历史 / 种子 / 持久化（R2）

| 验收点 | 证据 |
|---|---|
| 历史 N=20、淘汰最旧 | `test_history_evict_oldest` |
| 种子显示/复制/输入复现 | `docs/evidence/history0001.png`、`test_seed_reproduce` |
| 非法种子拒绝 | `test_seed_invalid_input_rejected` |
| profile 损坏降级 / 最高分保持 | `test_profile_corrupt_falls_back`、`test_best_score_not_lowered` |
| 备份导入导出 | `test_backup_import_export_roundtrip` |
| 崩溃日志 | `test_crash_guard_detects_previous_crash` |
| 退出强制写盘 | `test_pending_save_flushed_on_app_stop` |
| 常亮存 profile + 幂等迁移 | `test_screen_awake_in_profile_not_config`、`test_screen_awake_migration_idempotent` |

## 4. 回放（R2 数据层 + R3 UI 层）

| 验收点 | 证据 |
|---|---|
| 人类回放逐 tick 一致（数据层） | `test_replay_deterministic_human` |
| AI 回放逐 tick 一致（数据层） | `test_replay_deterministic_ai` |
| 中途切换一致（数据层） | `test_replay_mode_switch_midgame` |
| 人类回放 100 tick 蛇头一致（UI） | `test_replay_ui_advances_snake` |
| AI 回放 100 tick 蛇头一致（UI） | `test_replay_ui_ai_mode` |
| 模式切换回放一致（UI） | `test_replay_ui_mode_switch` |
| 完整文件 <100KB（9 万 tick + 事件） | `test_replay_full_file_size_under_100kb_at_cap`（90,227 字节） |
| 封顶停止录制、不阻塞游戏 | `test_ai_replay_stops_at_tick_cap`、`test_ai_replay_cap_does_not_block_gameplay` |
| 暂停冻结 / 倍速 4x / 结束停 | `test_replay_pause_freezes_snake`、`test_replay_speed_affects_tick_rate`、`test_replay_end_stops` |
| 结束文案同帧 | `test_replay_end_text_same_frame` |
| 播放截图（tick 2→8） | `docs/evidence/replay_a0001.png`、`replay_b0001.png` |
| 暂停截图 | `docs/evidence/replay_p20001.png` |

## 5. 成就 / 引导 / 暂停（R2）

| 验收点 | 证据 |
|---|---|
| 5 成就 + 解锁不重复 | `test_achievements_unlock`、`docs/evidence/achievements0001.png` |
| 引导只显示一次 | `test_onboarding_shows_once_ever`、`docs/evidence/onboarding0001.png` |
| 暂停/恢复 3-2-1 屏蔽输入 | `test_resume_countdown_starts_on_resume_not_on_pause`、`docs/evidence/pause0001.png` |
| 二次确认冻结游戏 | `test_confirm_dialog_blocks_gameplay`、`docs/evidence/confirm0001.png` |

## 6. 统计 / 调试（R3）

| 验收点 | 证据 |
|---|---|
| 统计面板 10 字段、2Hz、只读 stats | `test_stats_panel_fields`、`test_stats_panel_mounted_in_ai_mode`、`docs/evidence/stats0001.png` |
| 调试面板字段齐全 | `test_debug_panel_renders_when_on`、`docs/evidence/debug_on0001.png` |
| 关闭零采样、FPS 不采集 | `test_debug_fps_no_collect_when_off`、`docs/evidence/follow10017.png` |

## 7. 音效 / 震动（R3）

| 验收点 | 证据 |
|---|---|
| 三事件触发 SoundManager/Haptics | `test_sound_haptics_triggered_on_events` |
| 缺文件静默、桌面震动 no-op | 同上；`assets/sounds/` 为空（M5 补资源） |

## 8. 主题（R3）

| 验收点 | 证据 |
|---|---|
| 三主题（暗色/亮色/高对比） | `test_theme_panel_follows` |
| 面板/按钮/覆盖层跟随主题（KI-022 关闭） | `docs/evidence/history0001.png`（亮色）、`settings0005.png`（高对比） |
| 设置页无 Kivy Switch | `test_no_switch_widget` |

## 9. 跨模块

| 验收点 | 证据 |
|---|---|
| 设置生效（音效/音量/震动/主题即时同步） | `_on_settings_change` 同步 `sound/haptics/theme`；`test_panel_follows_theme` |
| 回放一致（人类/AI/切换，UI 层） | `test_replay_ui_advances_snake`、`test_replay_ui_ai_mode`、`test_replay_ui_mode_switch` |
| 种子复现 | `test_seed_reproduce` |
| 字体渲染 | `test_font_mix_render` + 截图 |
| 触控隔离 | `test_touch_isolation` |
| 主题切换 | `test_theme_panel_follows` |

## 10. resize 相机（KI-005）

| 验收点 | 证据 |
|---|---|
| 按格子尺寸比例换算，画面不漂移 | `core/camera.py::rescale_for_grid`、`tests/test_resize_camera.py`、`GameCanvas.on_size` |


## 11. M4 原 19 条验收逐条测试名

| # | 验收点 | 测试/证据 |
|---|---|---|
| 1 | 横屏锁定 + 70/30 分栏误差 <1px | `test_split_ratio_within_one_pixel`、`test_android_orientation_landscape` |
| 2 | 面板点击不转向（触控隔离） | `test_touch_isolation`、`test_panel_area_never_maps_to_game_area` |
| 3 | 虚拟摇杆死区 15% | `test_joystick_deadzone`、`test_joystick_deadzone_blocks_small_drag` |
| 4 | 四向滑动阈值 | `test_swipe_threshold`、`test_swipe_diagonal_picks_dominant_axis` |
| 5 | 设置项齐全且**重启生效** | `test_config_survives_restart`、`test_perf_mode_survives_restart`（改 theme/perf_mode/font 后新进程读回） |
| 6 | 恢复默认不动历史/profile | `test_settings_reset_keeps_profile` |
| 7 | 可访问性：字体 12~24 不溢出、可滚动 | `test_settings_panel_scrollable_at_max_font` |
| 8 | 字体混排渲染（中文/数字/英文/空格） | `test_font_mix_render`、`history0001.png` |
| 9 | 全 UI 中文化无硬编码 | `test_no_hardcoded_cn`、`test_no_hardcoded_cn_detects_fstring` |
| 10 | 历史 N=20、超限淘汰最旧 | `test_history_evict_oldest`、`test_history_bad_entries_dropped` |
| 11 | **种子复现同局** | `test_seed_reproduce`（同 seed 两 World 的 blocked/foods 完全相同）、`test_replay_ui_ai_mode` |
| 12 | 非法种子拒绝 | `test_seed_invalid_input_rejected`（8 类输入） |
| 13 | 回放人类/AI/中途切换一致 | `test_replay_deterministic_human`、`test_replay_deterministic_ai`、`test_replay_mode_switch_midgame`、`test_replay_ui_ai_mode`、`test_replay_ui_mode_switch` |
| 14 | 回放文件 ≤100KB、AI 封顶不阻塞 | `test_replay_full_file_size_under_100kb_at_cap`（含切换变体）、`test_ai_replay_cap_does_not_block_gameplay` |
| 15 | **成就进度正确** | `test_achievements_unlock`、`test_achievement_progress_values`（score 40/100、1800/3600） |
| 16 | 持久化：config/profile 损坏降级、备份往返、崩溃日志 | `test_config_corrupt_falls_back_to_defaults`、`test_profile_corrupt_falls_back`、`test_backup_import_export_roundtrip`、`test_crash_guard_detects_previous_crash` |
| 17 | 统计面板 10 字段 2Hz、只读 stats | `test_stats_panel_fields`、`test_stats_panel_mounted_in_ai_mode` |
| 18 | 调试面板字段齐全、关闭零开销 | `test_debug_panel_renders_when_on`、`test_debug_fps_no_collect_when_off` |
| 19 | 三主题 + 面板跟随（KI-022） | `test_theme_panel_follows`、`test_no_switch_widget`、`history0001.png`（亮色）、`settings0005.png`（高对比） |

补充：音效/震动三事件 → `test_sound_haptics_triggered_on_events`；引导只显示一次 → `test_onboarding_shows_once_ever`；暂停 3-2-1 屏蔽输入 → `test_resume_countdown_starts_on_resume_not_on_pause`、`test_pause_countdown_blocks_input`；'?' 占位语义 → `test_placeholder_direction_is_none_keeps_last`、`test_recorder_pads_with_placeholder_on_switch`。
