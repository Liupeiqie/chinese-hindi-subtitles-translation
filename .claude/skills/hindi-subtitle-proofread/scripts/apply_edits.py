"""只替换指定字幕的印地语行，旧文本必须逐字匹配。

用法：python apply_edits.py <drafts/hi-zh.srt> <edits.json>
edits.json：{"125": ["旧印地语", "新印地语"], ...}
"""
import json, sys
from srtlib import CJK, read_text

path, edits_path = sys.argv[1], sys.argv[2]
edits = json.load(open(edits_path, encoding="utf-8"))
text, bom = read_text(path)
nl = "\r\n" if "\r\n" in text else "\n"
blocks = text.split(nl + nl)
done = set()
for i, block in enumerate(blocks):
    lines = block.split(nl)
    num = lines[0].strip().lstrip("﻿")
    if num in edits:
        old, new = edits[num]
        if lines[2] != old:
            raise SystemExit(f"字幕 {num} 旧文本不匹配，未写入任何修改。\n文件：{lines[2]}\n期望：{old}")
        if CJK.search(new) or any(c in new for c in ",.，。、；：！？"):
            raise SystemExit(f"字幕 {num} 新译文含中文或禁用标点，未写入")
        lines[2] = new
        blocks[i] = nl.join(lines)
        done.add(num)
missing = set(edits) - done
if missing:
    raise SystemExit(f"找不到字幕 {sorted(missing, key=int)}，未写入任何修改")
open(path, "w", encoding="utf-8", newline="").write(("﻿" if bom else "") + (nl + nl).join(blocks))
print(f"已修改 {len(done)} 条：{', '.join(sorted(done, key=int))}")
