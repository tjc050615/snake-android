"""M4/R4：安卓适配（pyjnius，全部带守卫；桌面/无 jnius 时安全降级）。"""

from __future__ import annotations

import logging

LOG = logging.getLogger("snake.android")

IS_ANDROID = False
try:  # pragma: no cover - 仅安卓真机
    from kivy.utils import platform as _kivy_platform  # noqa: PLC0415

    IS_ANDROID = _kivy_platform == "android"
except Exception:  # pragma: no cover
    IS_ANDROID = False


def _activity():  # pragma: no cover - 仅安卓
    from jnius import autoclass  # noqa: PLC0415

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    return PythonActivity.mActivity


def display_metrics() -> dict:  # pragma: no cover - 仅安卓
    """读取分辨率与 DPI（DisplayMetrics）。"""
    if not IS_ANDROID:
        return {}
    try:
        from jnius import autoclass  # noqa: PLC0415

        Context = autoclass("android.content.Context")
        activity = _activity()
        metrics = activity.getResources().getDisplayMetrics()
        return {
            "width_px": int(metrics.widthPixels),
            "height_px": int(metrics.heightPixels),
            "density_dpi": int(metrics.densityDpi),
        }
    except Exception as exc:
        LOG.warning("display metrics failed: %s", exc)
        return {}


def set_immersive() -> bool:  # pragma: no cover - 仅安卓
    """沉浸全屏：隐藏状态栏/导航栏（android 30+ 用 WindowInsetsController）。"""
    if not IS_ANDROID:
        return False
    try:
        from jnius import autoclass  # noqa: PLC0415

        activity = _activity()
        window = activity.getWindow()
        decor = window.getDecorView()
        WindowInsetsController = autoclass("android.view.WindowInsetsController")
        insets_type = autoclass("android.view.WindowInsets$Type")

        controller = decor.getWindowInsetsController()
        if controller is not None:
            flags = (
                insets_type.systemBars()
                | insets_type.statusBars()
                | insets_type.navigationBars()
            )
            controller.hide(flags)
            controller.setSystemBarsBehavior(
                WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            )
        return True
    except Exception as exc:
        LOG.warning("immersive failed: %s", exc)
        return False


def safe_insets() -> dict:  # pragma: no cover - 仅安卓
    """刘海/挖孔安全区（WindowInsets.getInsets）。"""
    if not IS_ANDROID:
        return {}
    try:
        from jnius import autoclass  # noqa: PLC0415

        activity = _activity()
        decor = activity.getWindow().getDecorView()
        insets = decor.getRootWindowInsets()
        if insets is None:
            return {}
        Type = autoclass("android.view.WindowInsets$Type")
        cutout = insets.getInsets(Type.displayCutout())
        sysbars = insets.getInsets(Type.systemBars())
        return {
            "cutout": (cutout.left, cutout.top, cutout.right, cutout.bottom),
            "system_bars": (sysbars.left, sysbars.top, sysbars.right, sysbars.bottom),
        }
    except Exception as exc:
        LOG.warning("safe insets failed: %s", exc)
        return {}


def vibrate(milliseconds: int) -> bool:  # pragma: no cover - 仅安卓
    """震动（仅 VIBRATE 权限）。"""
    if not IS_ANDROID:
        return False
    try:
        from jnius import autoclass  # noqa: PLC0415

        Context = autoclass("android.content.Context")
        activity = _activity()
        vibrator = activity.getSystemService(Context.VIBRATOR_SERVICE)
        if vibrator is None:
            return False
        vibrator.vibrate(int(milliseconds))
        return True
    except Exception as exc:
        LOG.warning("vibrate failed: %s", exc)
        return False
