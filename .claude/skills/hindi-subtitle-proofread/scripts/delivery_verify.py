"""核对交付副本与项目工作稿、核验报告、校对单是否一致，写 reviews/delivery-verification.json。

用法：python delivery_verify.py <项目目录> <交付目录> <reviews/review-vN.json> [--note 说明] [--stdout]
任一项为 false 时退出码为 1，此时不得推送。
"""
import datetime, hashlib, json, os, subprocess, sys

project, delivery, review = sys.argv[1], sys.argv[2], sys.argv[3]
note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else ""
P = lambda p: os.path.join(project, p)
D = lambda p: os.path.join(delivery, p)
h = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()
v = json.load(open(P("reviews/verification.json"), encoding="utf-8"))
m = json.load(open(P("manifest.json"), encoding="utf-8"))
r = json.load(open(P(review), encoding="utf-8"))
cand = h(P("drafts/hi-zh.srt"))
out = {
    "passed": None,
    "checked_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(microsecond=0).isoformat(),
    "output": delivery, "candidate_sha256": cand,
    "source_cues": v["source_cues"], "candidate_cues": v["candidate_cues"],
    "draft_and_delivery_identical": cand == h(D("hi-zh.srt")),
    "report_candidate_matches": bool(v["passed"]) and v["candidate_sha256"] == cand,
    "report_and_notes_copies_identical": h(P("reviews/verification.json")) == h(D("verification.json"))
        and h(P("reviews/translation-notes.md")) == h(D("translation-notes.md")),
    "preprocessed_source_unchanged": h(P("source/zh.srt")) == m["source_sha256"],
    "current_review_bound": r["candidate_sha256"] == cand,
}
if os.path.exists(P("source/original.srt")):
    out["raw_input_unchanged"] = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", P("source/original.srt")]).returncode == 0
if os.path.exists(P("reviews/readability.json")):
    out["current_readability_report_bound"] = json.load(open(P("reviews/readability.json"), encoding="utf-8")).get("candidate_sha256") == cand
if note:
    out["note"] = note
out["passed"] = all(val for val in out.values() if isinstance(val, bool))
print(json.dumps(out, ensure_ascii=False, indent=2))
if "--stdout" not in sys.argv:
    json.dump(out, open(P("reviews/delivery-verification.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
sys.exit(0 if out["passed"] else 1)
