"""R3：中文字体与文案地基。"""

import pytest

from app import strings


def test_strings_have_all_required_keys():
    for lang, table in strings.STRINGS.items():
        for key in strings.REQUIRED_KEYS:
            assert key in table, f"{lang} 缺少 {key}"


def test_default_lang_is_zh():
    assert strings.DEFAULT_LANG == "zh"


def test_game_over_text_is_chinese():
    assert strings.t("game_over") == "游戏结束"
    assert strings.t("score") == "得分"
    assert strings.t("restart_hint") == "按 R 重新开始"


def test_missing_key_raises():
    with pytest.raises(KeyError):
        strings.t("not_a_key")


def test_font_registers_without_error():
    pytest.importorskip("kivy")
    from app import fonts

    path = fonts.font_path()
    assert path is not None, "assets/fonts 下没有随包字体"
    assert fonts.register_fonts() == path
    assert fonts.font_name() == fonts.FONT_NAME


def test_font_file_is_valid_sfnt():
    """不在这里做 CoreLabel.refresh()：Kivy 需要窗口/GL 上下文，无窗口会崩（0xC0000005）。

    真正的渲染验证由 GUI 截图（中文 GAME OVER）承担。
    """
    from app import fonts

    path = fonts.font_path()
    assert path is not None
    with open(path, "rb") as fh:
        head = fh.read(4)
    assert head in (b"\x00\x01\x00\x00", b"OTTO", b"ttcf", b"true"), head
