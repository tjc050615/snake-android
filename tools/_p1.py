p = "src/core/interp.py"
s = open(p, encoding="utf-8").read()
s = s.replace(
    "def segment_cells(snake, progress: float) -> list[tuple[float, float]]:\n    \"\"\"返回从蛇头到蛇尾的浮点格坐标列表（长度与蛇身一致）。\"\"\"\n    body = list(snake.body)",
    "def segment_cells(snake, progress: float, out: list | None = None) -> list[tuple[float, float]]:\n"
    "    \"\"\"返回从蛇头到蛇尾的浮点格坐标列表（长度与蛇身一致）。\n\n"
    "    out 传入时复用该 list（R5A：避免每帧新建），返回值可能不是新对象。\n"
    "    \"\"\"\n"
    "    body = list(snake.body)",
)
# 在结尾把结果写入 out：找到 return 语句结构，改为先构造 result 再回填
s = s.replace(
    "    if n == 1:\n        return [(float(body[0][0]), float(body[0][1]))]",
    "    if n == 1:\n"
    "        one = [(float(body[0][0]), float(body[0][1]))]\n"
    "        if out is not None:\n"
    "            out[:] = one\n"
    "            return out\n"
    "        return one",
)
open(p, "w", encoding="utf-8").write(s)
print("interp patched (part 1)")
