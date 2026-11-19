"""比较两版双语 SRT：确认只有印地语行变化，列出改动，可核对报告中的「修改结果」表。

用法：
  python compare_versions.py <旧.srt> <新.srt>                 列出改动并做结构检查
  python compare_versions.py <旧.srt> <新.srt> --table         另输出 Markdown 表格草稿（中文含义需人工补）
  python compare_versions.py <旧.srt> <新.srt> --check-report <报告.md>
        核对报告「## 修改结果」表的每行 | 字幕 | 条目 | 修改前（含义） | 修改后（含义） | 与实际一致
"""
import re, sys
from srtlib import parse

old_path, new_path = sys.argv[1], sys.argv[2]
a, oa = parse(old_path)
b, ob = parse(new_path)
problems = []
if oa != ob:
    problems.append("字幕序号或条数不同")
for n in oa:
    if n in b and (a[n]["time"] != b[n]["time"] or a[n]["zh"] != b[n]["zh"]):
        problems.append(f"字幕 {n} 的时间码或中文发生变化")
changed = {n: (a[n]["hi"], b[n]["hi"]) for n in oa if n in b and a[n]["hi"] != b[n]["hi"]}
bad_punct = [n for n, (_, new) in changed.items() if re.search(r"[,.，。、；：！？]", new)]
if bad_punct:
    problems.append(f"新译文含禁用标点：{bad_punct}")
print(f"改动 {len(changed)} 条印地语：{', '.join(sorted(changed, key=int))}")
for n in sorted(changed, key=int):
    print(f"  {n}: {changed[n][0]}  →  {changed[n][1]}")
if "--table" in sys.argv:
    print("\n| 字幕 | 校对条目 | 修改前（中文含义） | 修改后（中文含义） |\n| --- | --- | --- | --- |")
    for n in sorted(changed, key=int):
        print(f"| {n} | ? | {changed[n][0]}（?） | {changed[n][1]}（?） |")
if "--check-report" in sys.argv:
    report = open(sys.argv[sys.argv.index("--check-report") + 1], encoding="utf-8").read()
    section = report.split("## 修改结果", 1)
    if len(section) < 2:
        problems.append("报告缺少「## 修改结果」一节")
    else:
        rows = {}
        for line in section[1].splitlines():
            m = re.match(r"\| (\d+) \| [^|]+ \| (.+?)（[^|]*） \| (.+?)（[^|]*） \|$", line)
            if m:
                rows[m.group(1)] = (m.group(2), m.group(3))
        if set(rows) != set(changed):
            problems.append(f"报告表格字幕集合与实际不符：多 {sorted(set(rows)-set(changed))} 少 {sorted(set(changed)-set(rows))}")
        for n in set(rows) & set(changed):
            if rows[n] != changed[n]:
                problems.append(f"报告字幕 {n} 的修改前后文本与实际不符")
        print(f"报告表格 {len(rows)} 行已核对")
if problems:
    print("未通过：\n- " + "\n- ".join(problems))
    sys.exit(1)
print("通过：只有印地语行变化，序号、时间码、中文一致")
