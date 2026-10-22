# R4 安卓打包（buildozer + python-for-android + pyjnius）

## 版本锁定（不要用最新版）

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | 3.11 | Kivy 2.3.0 支持 3.8~3.12 |
| Kivy | 2.3.0 | `requirements` 已锁定 |
| buildozer | **1.5.0** | 写死在 spec 注释中 |
| python-for-android | 随 buildozer 1.5.0 的兼容 commit | 首次构建时记录实际 commit 到本节 |
| minSdk / targetSdk | 23 / 33 | `android.minapi` / `android.api` |
| 权限 | 仅 `VIBRATE` | `android.permissions` |

## 打包命令（Linux / WSL2 或 CI）

```bash
python3 -m venv .venv-build && source .venv-build/bin/activate
pip install buildozer==1.5.0 cython==0.29.36
cd <repo>
buildozer -v android debug 2>&1 | tee docs/evidence/buildozer-debug.log
ls -lh bin/*.apk
unzip -l bin/snake-*-debug.apk | grep -E "assets/fonts|tests/|docs/"   # 校验字体进包、测试/文档未进包
buildozer android deploy run 2>&1 | tee docs/evidence/buildozer-run.log
```

## 资源打包清单

**必须进 APK**
- `assets/fonts/NotoSansSC-Regular.otf`（8.33MB，OFL）

**可选**
- `assets/sounds/*.wav`（当前为空目录；缺文件时 `SoundManager.play` 静默）

**绝不进 APK**
- `docs/`（含 `docs/evidence/*.png`、`*.md`）
- `tests/`、`tools/`
- `.venv/`、`.data/`、`.kivyhome/`、`__pycache__/`、`.git/`
- `requirements*.txt`、`*.md`

校验方式：`unzip -l bin/*.apk | grep -E "tests/|docs/"` 必须无输出。

## pyjnius 适配（`src/platform_layer/android.py`）

| 功能 | Android API | 失败降级 |
|---|---|---|
| 分辨率/DPI | `DisplayMetrics`（widthPixels/heightPixels/densityDpi） | 返回 `{}` |
| 沉浸全屏 | `WindowInsetsController.hide(systemBars)` + `BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE` | 返回 False |
| 刘海/挖孔安全区 | `WindowInsets.getInsets(Type.displayCutout()/systemBars())` | 返回 `{}` |
| 震动 | `Context.VIBRATOR_SERVICE.vibrate(ms)` | 返回 False |
| 返回键 / 后台暂停 | Kivy `Window.on_key_down` + `on_pause/on_resume` | 桌面无影响 |

所有函数都 `try/except` 包裹，失败只记 warning，不影响游戏。

## 数据目录

`data/storage.py::home_dir()`：`SNAKE_HOME` → 安卓 `App.get_running_app().user_data_dir` → 桌面 `~/.snake_android`。
测试：`test_home_dir_android_uses_user_data_dir`、`test_home_dir_env_override`。

## 常见问题

| 现象 | 处理 |
|---|---|
| `Cython` 编译失败 | 锁 `cython==0.29.36`（Kivy 2.3 需要 0.29.x） |
| 字体中文显示成方块 | 确认 `assets/fonts/NotoSansSC-Regular.otf` 已进 APK（`unzip -l` 检查） |
| 列表文字不显示 | KI-024：`TextInput` 首布局不渲染，真机确认是否仍存在 |
| 启动黑屏 | 检查 `fullscreen=1` 与 `orientation=landscape`；看 `adb logcat -s python` |
| 安装失败 `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | 先 `adb uninstall org.example.snake` |
| 返回键直接退出 | `on_key_down` 里拦截 key 27 并改弹确认框 |

## 当前状态（诚实记录）

- `buildozer.spec`、`platform_layer/android.py`、数据目录适配、spec 解析测试**已完成**（`tests/test_android_packaging.py` 7 条全绿）。
- **本环境（Windows + 无 Android SDK/NDK/设备）无法执行 `buildozer android debug`，也无法真机安装与 10 分钟热稳定测试。**
- 因此：无打包日志片段、无真机截图、无热稳定数据；`m5-pack` **未打**（需要构建成功后才能证明）。
- 需要在 Linux/WSL2 + Android SDK/NDK 环境执行上面命令，把 `buildozer-debug.log`、`unzip -l` 输出、真机截图 5 张、热稳定数据补进 `docs/evidence/`。
