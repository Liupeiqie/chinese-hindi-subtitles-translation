"""按项目既有方法重算 reviews/readability.json（空格分词，>6 词/秒仅作提示）。

用法：python readability.py <项目目录> [--stdout]
"""
import hashlib, json, sys, os
from srtlib import parse

project = sys.argv[1]
draft = os.path.join(project, "drafts/hi-zh.srt")
out_path = os.path.join(project, "reviews/readability.json")


def seconds(stamp):
    h, m, rest = stamp.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


cues, order = parse(draft)
rows = []
for n in order:
    start, end = cues[n]["time"].split(" --> ")
    dur = round(seconds(end.strip()) - seconds(start.strip()), 2)
    words = len(cues[n]["hi"].split())
    wps = round(words / dur, 2) if dur > 0 else None
    rows.append({"cue": n, "duration_seconds": dur, "hindi_words": words, "words_per_second": wps, "flag": bool(wps and wps > 6)})
data = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {
    "method": "按空格分词；大于6词/秒仅作为本次人工复核提示，不是语言质量合格标准；未试听视频"}
data.update(candidate_sha256=hashlib.sha256(open(draft, "rb").read()).hexdigest(),
            cues_checked=len(rows), flagged_count=sum(r["flag"] for r in rows), cues=rows)
print("超阈值：", [r["cue"] for r in rows if r["flag"]])
if "--stdout" not in sys.argv:
    json.dump(data, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
