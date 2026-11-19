"""校对脚本共用的 SRT 读取工具（双语块：序号、时间码、一行印地语、若干行中文）。"""
import re

CJK = re.compile(r"[㐀-鿿豈-﫿]")


def read_text(path):
    raw = open(path, encoding="utf-8", newline="").read()
    bom = raw.startswith("﻿")
    return (raw[1:] if bom else raw), bom


def parse(path):
    """返回 {序号: {"time":..., "hi":..., "zh":[...]}}，以及块顺序列表。"""
    text, _ = read_text(path)
    text = text.replace("\r\n", "\n")
    cues, order = {}, []
    for block in text.strip().split("\n\n"):
        lines = block.split("\n")
        num = lines[0].strip()
        if len(lines) < 4:
            raise SystemExit(f"字幕 {num} 行数不足，不是双语块")
        if CJK.search(lines[2]):
            raise SystemExit(f"字幕 {num} 第3行含中文，不是单行印地语译文，脚本不处理")
        cues[num] = {"time": lines[1], "hi": lines[2], "zh": lines[3:]}
        order.append(num)
    return cues, order
