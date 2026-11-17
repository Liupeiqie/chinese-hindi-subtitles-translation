# 中文 → 印地语字幕翻译仓库

按术语表将中文 SRT 翻译为印地语—中文双语 SRT，经过结构核验、人工校对后定稿。需要 Python 3.10+ 和 Git；脚本仅使用标准库，不需要 API 密钥。

## 流程

1. **准备**：提供 UTF-8 中文 `.srt` 和术语表，为每个视频建立独立项目。脚本保存原始文件与术语表快照及 SHA-256。
2. **翻译**：替换草稿里的 `__TODO_HI__`，按术语表翻译。每条字幕先印地语、再中文；原中文有几行就保留几行。
3. **核验**：逐条检查字幕数量、顺序、序号、完整时间码行和中文原文；任何差异都阻止通过。
4. **校对**：结构通过后生成校对单，人工检查印地语、术语、漏译和可读性，记录问题并修订。修订后重新核验并生成新的校对单。
5. **定稿**：只有绑定当前字幕、原文和术语表的校对单全部通过、没有未解决问题，才能导出定稿。

自动核验只能确认结构和原文未改，不能判断翻译质量。翻译和校对由人工或当前 AI 助手完成，脚本不会自动调用在线服务。

## 已接入的用户规范（2026-11-17）

- 翻译规范：[专业版 v5 原件](prompts/source/印地语翻译提示词_专业版_v5.txt)，执行入口为 [translate.md](prompts/translate.md)。按本次要求，中文换行也保留，不采用原件中的中文合行例外。
- 术语主表：[glossary.csv](terminology/glossary.csv)，已导入用户 20261111 版的 808 条词条。原文件存于 terminology/source/，出处和指纹见 [导入记录](terminology/imports/2026-11-17.json)。中文和印地语字段原样保留，增加维护说明和来源字段。
- 术语表高于提示词推荐示例；“汉地”首次全译、后续简称按整份字幕判断，具体写法见主表 note。
- 翻译后必须实际运行 check，逐条比对翻译前后的序号、时间轴和中文，查看保存的核验报告后再交付。当前尚未提供具体字幕或课程讲记，不能据此声称已完成某份字幕核验。

## 快速开始（PowerShell）

先按 [术语表说明](templates/README.md) 填写主表 `terminology/glossary.csv`，将讲记、论释等资料放到 `references/library/` 并登记 `references/catalog.csv`。再运行（替换示例输入路径）：

```powershell
python tools/subtitles.py new lesson-001 --source 'E:\素材\中文.srt' --glossary terminology/glossary.csv --reference references/catalog.csv --reference 'references/library/讲记.md'
```

`--reference` 可重复使用；尚未提供资料时可省略，后续补齐，但不可声称已参考未提供的资料。编辑 `projects/lesson-001/drafts/hi-zh.srt`，也可以让 AI 按 [翻译提示词](prompts/translate.md) 查阅相关资料并翻译。然后：

```powershell
python tools/subtitles.py check projects/lesson-001
python tools/subtitles.py review projects/lesson-001
```

按 [校对提示词](prompts/proofread.md) 校对，填写 `reviews/review.json` 中的校对人、带时区的日期时间、检查项和问题。发现问题先修订字幕；修订后重新生成校对单（保留之前的记录）：

```powershell
python tools/subtitles.py check projects/lesson-001
python tools/subtitles.py review projects/lesson-001 --output reviews/review-v2.json
python tools/subtitles.py finalize projects/lesson-001 --review reviews/review-v2.json
```

如果首次校对不需要修改，直接使用默认校对单：

```powershell
python tools/subtitles.py finalize projects/lesson-001
```

定稿位于 `final/hi-zh.srt`，同时生成 `final/release.json`，记录字幕、原文、术语表和校对单的哈希。已定稿项目禁止覆盖定稿；新版本另建项目，例如 `lesson-001-v2`。

已有两份字幕也可独立比较：

```powershell
python tools/subtitles.py compare 'E:\素材\中文.srt' 'E:\素材\双语.srt'
```

## 项目目录

```text
projects/<项目名>/
  manifest.json          原始文件及术语表指纹
  source/zh.srt          中文原件，只读约定
  glossary/glossary.csv  本项目术语表快照
  references/           本项目参考资料快照
  history/              更新依据前的清单和术语表
  drafts/hi-zh.srt       双语工作稿
  reviews/              结构报告与各版校对单
  final/                双语定稿和发布记录
```

输入须为 UTF-8（允许 BOM）。核验忽略 BOM、LF/CRLF 换行格式及字幕块间空行的差异；中文内部换行、空格、标点、序号文本和时间码行必须完全一致。时间码必须合法，结束时间不得早于开始时间；保留原有的字幕重叠。每条双语字幕的末尾必须是完整原中文，前面必须有印地语译文。无法可靠识别译文语言，因此还需校对。

## 持续维护术语和参考资料

主表为 `terminology/glossary.csv`，列为 `source,target,note,reference`，支持空表。新术语、争议译法先记录在 `terminology/proposals.csv`，核实后更新主表并在 `terminology/CHANGELOG.md` 记录理由、出处和受影响项目。不要将待确认建议直接当作定译。

按 [资料说明](references/README.md) 维护讲记、论释、原件和文字提取稿。关键翻译决定在项目 `reviews/translation-notes.md` 中标注字幕序号、资料编号、页码或章节；可从 `templates/translation-notes.md` 复制格式。资料用于理解中文，不得用资料内容扩写字幕。

中央主表和资料更新不会静默改变旧项目。工作项目需要采纳新依据时运行：

```powershell
python tools/subtitles.py sync-inputs projects/lesson-001 --glossary terminology/glossary.csv --reference references/catalog.csv --reference 'references/library/讲记.md'
```

不传 `--reference` 保留当前资料；传入时应列出本次完整资料清单。旧清单和术语表保存在 history/，旧资料副本保留，原中文始终不变。依据内容改变后旧校对单失效，需复核受影响译文、重新 check 和 review。已定稿项目禁止同步，须另建版本。

哈希核验防止无意改动，不是防篡改签名。Git 历史保留人工决策和各版依据，校对单如实记录实际检查结果。

## Git 使用

字幕、术语表、校对记录和定稿均纳入版本管理；视频、音频、缓存和密钥不纳入。建议在准备、翻译完成、校对完成和定稿后分别提交：

```powershell
git status
git add projects/lesson-001
git commit -m 'lesson-001: 完成双语字幕翻译'
```

首次自行提交前，如尚未设置身份，请配置本仓库的真实姓名和邮箱：

```powershell
git config user.name '你的名字'
git config user.email '你的邮箱'
```

运行仓库自检：`python -m unittest discover -s tests -v`。
