"""Local, standard-library-only Chinese/Hindi subtitle workflow."""

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TODO = "__TODO_HI__"
CHECKS = ("meaning", "terminology", "reference_consistency", "hindi_language", "numbers_and_names", "readability", "source_integrity")
TIMING = re.compile(r"^(\d{2,}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2,}):([0-5]\d):([0-5]\d),(\d{3})(?:[ \t]+\S.*)?$")


@dataclass
class Cue:
    index: str
    timing: str
    lines: list[str]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def parse_srt(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    blocks, block = [], []
    for line in text.splitlines():
        if not line.strip():
            if block:
                blocks.append(block)
                block = []
        else:
            block.append(line)
    if block:
        blocks.append(block)
    if not blocks:
        raise ValueError(f"字幕为空：{path}")
    cues = []
    for position, lines in enumerate(blocks, 1):
        if len(lines) < 3 or not re.fullmatch(r"[0-9]+", lines[0]):
            raise ValueError(f"第 {position} 块格式错误：需要序号、时间码和正文")
        match = TIMING.fullmatch(lines[1])
        if not match:
            raise ValueError(f"第 {position} 块时间码格式错误")
        values = [int(x) for x in match.groups()]
        start = ((values[0] * 60 + values[1]) * 60 + values[2]) * 1000 + values[3]
        end = ((values[4] * 60 + values[5]) * 60 + values[6]) * 1000 + values[7]
        if end < start:
            raise ValueError(f"第 {position} 块结束时间早于开始时间")
        cues.append(Cue(lines[0], lines[1], lines[2:]))
    return cues


def validate_glossary(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != ["source", "target", "note", "reference"]:
        raise ValueError("术语表表头必须为 source,target,note,reference")
    seen = set()
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"术语表第 {reader.line_num} 行列数错误")
        source, target = row["source"].strip(), row["target"].strip()
        if not source or not target or source in seen:
            raise ValueError(f"术语表第 {reader.line_num} 行存在空术语、空译法或重复中文术语")
        seen.add(source)


def compare(source, candidate, *, single_line_chinese=False):
    original, bilingual = parse_srt(source), parse_srt(candidate)
    errors = []
    if len(original) != len(bilingual):
        errors.append(f"字幕数量不同：原文 {len(original)}，双语 {len(bilingual)}")
    for position, (zh, hi) in enumerate(zip(original, bilingual), 1):
        label = f"第 {position} 块（原序号 {zh.index}）"
        if zh.index != hi.index:
            errors.append(f"{label}：序号被修改")
        if zh.timing != hi.timing:
            errors.append(f"{label}：时间码被修改")
        if single_line_chinese:
            if len(hi.lines) != 2 or hi.lines[1] != " ".join(zh.lines):
                errors.append(f"{label}：需要一行译文及用空格连接的完整中文")
            elif not hi.lines[0].strip() or TODO in hi.lines[0]:
                errors.append(f"{label}：缺少译文")
        elif len(hi.lines) <= len(zh.lines):
            errors.append(f"{label}：缺少译文或中文行")
        elif hi.lines[-len(zh.lines):] != zh.lines:
            errors.append(f"{label}：中文原文或其换行被修改")
        else:
            translation = hi.lines[:-len(zh.lines)]
            if any(TODO in line for line in translation):
                errors.append(f"{label}：仍有待翻译占位符")
    return {"passed": not errors, "source_cues": len(original), "candidate_cues": len(bilingual), "errors": errors}


def project_paths(project):
    project = Path(project).resolve()
    return project, project / "source/zh.srt", project / "glossary/glossary.csv", project / "drafts/hi-zh.srt"


def check_project(project):
    project, source, glossary, candidate = project_paths(project)
    manifest = read_json(project / "manifest.json")
    if manifest.get("schema_version") != 1:
        raise ValueError("不支持的项目清单版本")
    for key, path in (("source_sha256", source), ("glossary_sha256", glossary)):
        if manifest.get(key) != digest(path):
            raise ValueError(f"冻结输入被修改：{path}")
    validate_glossary(glossary)
    references = manifest.get("references", [])
    for reference in references:
        path = (project / reference["path"]).resolve()
        if not path.is_relative_to(project / "references") or digest(path) != reference["sha256"]:
            raise ValueError(f"参考资料快照被修改：{reference['path']}")
    result = compare(source, candidate, single_line_chinese=manifest.get("chinese_layout") == "single-line")
    result.update(checked_at=now(), source_sha256=digest(source), glossary_sha256=digest(glossary), candidate_sha256=digest(candidate))
    result["context_sha256"] = hashlib.sha256(json.dumps(references, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return result


def require_passed(result):
    if not result["passed"]:
        raise ValueError("核验未通过：\n" + "\n".join(result["errors"]))


def snapshot_references(project, references):
    snapshots = []
    for value in references:
        path = Path(value)
        fingerprint = digest(path)
        relative = Path("references") / f"{fingerprint}_{path.name}"
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(path, target)
        elif digest(target) != fingerprint:
            raise ValueError(f"参考资料快照被修改：{target}")
        snapshots.append({"name": path.name, "path": relative.as_posix(), "sha256": fingerprint})
    return snapshots


def new_project(name, source, glossary, root=None, references=()):
    if not re.fullmatch(r"[^<>:\"/\\|?*\x00-\x1f]+", name) or name.endswith((".", " ")) or name in (".", ".."):
        raise ValueError("项目名必须是合法的单个文件夹名称")
    if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", name):
        raise ValueError("项目名使用了 Windows 保留名称")
    source, glossary = Path(source), Path(glossary)
    cues = parse_srt(source)
    validate_glossary(glossary)
    for reference in references:
        digest(reference)
    project = (Path(root) if root is not None else ROOT / "projects") / name
    project.mkdir(parents=True, exist_ok=False)
    for directory in ("source", "glossary", "drafts", "reviews", "final", "references", "history"):
        (project / directory).mkdir()
    shutil.copyfile(source, project / "source/zh.srt")
    shutil.copyfile(glossary, project / "glossary/glossary.csv")
    write_json(project / "manifest.json", {
        "schema_version": 1, "name": name, "created_at": now(),
        "source_language": "zh", "target_language": "hi", "layout": "hi-then-zh",
        "source_sha256": digest(project / "source/zh.srt"),
        "glossary_sha256": digest(project / "glossary/glossary.csv"),
        "references": snapshot_references(project, references),
    }, exclusive=True)
    draft = "\n\n".join("\n".join([cue.index, cue.timing, TODO, *cue.lines]) for cue in cues) + "\n"
    (project / "drafts/hi-zh.srt").write_text(draft, encoding="utf-8", newline="\n")
    shutil.copyfile(ROOT / "templates/translation-notes.md", project / "reviews/translation-notes.md")
    return project


def sync_inputs(project, glossary, references=None):
    project, source, old_glossary, candidate = project_paths(project)
    if any((project / "final").iterdir()):
        raise ValueError("已定稿项目不能更新依据，请另建项目版本")
    # Integrity checks still run when translations contain TODO placeholders.
    check_project(project)
    validate_glossary(glossary)
    glossary_bytes = Path(glossary).read_bytes()
    if references is not None:
        for reference in references:
            digest(reference)
    manifest = read_json(project / "manifest.json")
    archive = project / "history" / datetime.now().strftime("%Y%m%dT%H%M%S%f")
    archive.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(project / "manifest.json", archive / "manifest.json")
    shutil.copyfile(old_glossary, archive / "glossary.csv")
    if references is not None:
        manifest["references"] = snapshot_references(project, references)
    old_glossary.write_bytes(glossary_bytes)
    manifest["glossary_sha256"] = digest(old_glossary)
    manifest["inputs_updated_at"] = now()
    write_json(project / "manifest.json", manifest)
    return archive


def inside(project, relative):
    project = Path(project).resolve()
    relative = Path(relative)
    if relative.is_absolute():
        raise ValueError("校对单路径须相对于项目目录")
    path = (project / relative).resolve()
    if not path.is_relative_to(project / "reviews") or path.suffix != ".json":
        raise ValueError("校对单必须位于项目 reviews 目录，扩展名为 .json")
    return path


def make_review(project, output="reviews/review.json"):
    result = check_project(project)
    require_passed(result)
    path = inside(project, output)
    review = {
        "schema_version": 1, "created_at": now(),
        **{key: result[key] for key in ("source_sha256", "glossary_sha256", "candidate_sha256", "context_sha256")},
        "reviewer": "", "reviewed_at": "",
        "checks": {key: False for key in CHECKS}, "issues": [], "notes": "",
    }
    write_json(path, review, exclusive=True)
    return path


def finalize(project, review_file="reviews/review.json"):
    project, source, glossary, candidate = project_paths(project)
    result = check_project(project)
    require_passed(result)
    review_path = inside(project, review_file)
    review = read_json(review_path)
    if review.get("schema_version") != 1:
        raise ValueError("不支持的校对单版本")
    for key in ("source_sha256", "glossary_sha256", "candidate_sha256", "context_sha256"):
        if review.get(key) != result[key]:
            raise ValueError("校对单已失效：文件已修改，请重新生成校对单并校对")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise ValueError("请填写实际校对人")
    try:
        timestamp = datetime.fromisoformat(review.get("reviewed_at", "").replace("Z", "+00:00"))
        if timestamp.utcoffset() is None:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValueError("请填写带时区的 ISO 校对时间") from None
    checks = review.get("checks")
    if not isinstance(checks, dict) or any(checks.get(key) is not True for key in CHECKS):
        raise ValueError("所有校对检查项必须完成且为 true")
    issues = review.get("issues")
    if not isinstance(issues, list):
        raise ValueError("issues 必须是数组")
    for issue in issues:
        if not isinstance(issue, dict) or issue.get("status") != "resolved" or not str(issue.get("cue", "")).strip() or not isinstance(issue.get("description"), str) or not issue["description"].strip():
            raise ValueError("存在未解决或格式不完整的校对问题")
    output = project / "final/hi-zh.srt"
    receipt = project / "final/release.json"
    if output.exists() or receipt.exists():
        raise ValueError("定稿已存在，禁止覆盖；请创建新的项目版本")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(candidate.read_bytes())
    write_json(receipt, {
        "schema_version": 1, "released_at": now(), "reviewer": review["reviewer"],
        "review_file": review_path.relative_to(project).as_posix(), "review_sha256": digest(review_path),
        "final_sha256": digest(output), "verification": result,
    }, exclusive=True)
    return output


def main():
    # Keep Chinese/Hindi output readable when Windows pipes use a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="中文 → 印地语双语字幕：准备、核验、校对、定稿")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new", help="建立项目并生成待翻译草稿")
    new.add_argument("name")
    new.add_argument("--source", required=True)
    new.add_argument("--glossary", required=True)
    new.add_argument("--reference", action="append", default=[], help="参考资料文件，可重复指定")
    sync = commands.add_parser("sync-inputs", help="更新工作项目术语和资料，保留旧依据")
    sync.add_argument("project")
    sync.add_argument("--glossary", required=True)
    sync.add_argument("--reference", action="append", help="新的完整资料列表；不传则保留当前列表")
    check = commands.add_parser("check", help="核验项目并保存报告")
    check.add_argument("project")
    compare_cmd = commands.add_parser("compare", help="直接比较中文和双语两份 SRT")
    compare_cmd.add_argument("source")
    compare_cmd.add_argument("candidate")
    review = commands.add_parser("review", help="生成绑定当前文件的待填写校对单")
    review.add_argument("project")
    review.add_argument("--output", default="reviews/review.json")
    final = commands.add_parser("finalize", help="验证校对单并生成不可覆盖的定稿")
    final.add_argument("project")
    final.add_argument("--review", default="reviews/review.json")
    args = parser.parse_args()
    try:
        if args.command == "new":
            print(f"项目已建立：{new_project(args.name, args.source, args.glossary, references=args.reference)}")
        elif args.command == "sync-inputs":
            print(f"依据已更新，旧依据保存在：{sync_inputs(args.project, args.glossary, args.reference)}；请重新核验和校对")
        elif args.command in ("check", "compare"):
            if args.command == "check":
                result = check_project(args.project)
                write_json(Path(args.project) / "reviews/verification.json", result)
            else:
                result = compare(args.source, args.candidate)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["passed"] else 1
        elif args.command == "review":
            print(f"待填写校对单：{make_review(args.project, args.output)}")
        elif args.command == "finalize":
            print(f"定稿已生成：{finalize(args.project, args.review)}")
    except (ValueError, OSError, csv.Error) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
