"""pytest 引导：把 src/ 放进 sys.path，使核心逻辑在无 Kivy 环境下可测。"""

import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
