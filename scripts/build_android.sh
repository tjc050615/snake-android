#!/usr/bin/env bash
# 本地 / WSL2 打包脚本（R4）
# 用法：bash scripts/build_android.sh [debug|release]
set -euo pipefail

MODE="${1:-debug}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== 1/5 检查依赖 =="
python3 --version
if ! python3 -c "import buildozer" 2>/dev/null; then
  echo "安装 buildozer==1.5.0 + cython==0.29.36 ..."
  python3 -m pip install --user buildozer==1.5.0 cython==0.29.36
fi
command -v javac >/dev/null || { echo "缺少 JDK 17：sudo apt install openjdk-17-jdk"; exit 1; }
command -v unzip >/dev/null || { echo "缺少 unzip：sudo apt install unzip"; exit 1; }

if [ -z "${ANDROID_HOME:-}" ] && [ ! -d "$HOME/.buildozer/android/platform/android-sdk" ]; then
  echo "未检测到 Android SDK（ANDROID_HOME 未设置，且 ~/.buildozer/android/platform/android-sdk 不存在）"
  echo "首次运行 buildozer 会自动下载 SDK/NDK（约 10~20 分钟），请确保网络可用。"
fi

echo "== 2/5 清理旧产物 =="
rm -rf bin/*.apk

echo "== 3/5 buildozer android $MODE =="
LOG="docs/evidence/buildozer-${MODE}.log"
mkdir -p docs/evidence
set -o pipefail
buildozer -v "android" "$MODE" 2>&1 | tee "$LOG"

echo "== 4/5 校验 APK 内容 =="
APK=$(ls bin/*.apk | head -n1)
unzip -l "$APK" | tee docs/evidence/apk-contents.txt
if unzip -l "$APK" | grep -E "(^|/)tests/|(^|/)docs/|(^|/)tools/"; then
  echo "ERROR: APK 内包含 tests/docs/tools" >&2
  exit 1
fi
unzip -l "$APK" | grep -q "NotoSansSC-Regular.otf" || { echo "ERROR: 字体未进 APK" >&2; exit 1; }

echo "== 5/5 完成 =="
echo "APK: $ROOT/$APK"
echo "日志: $ROOT/$LOG"
echo "安装: adb install -r $ROOT/$APK"
