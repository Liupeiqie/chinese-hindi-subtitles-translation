---
name: hindi-subtitle-proofread
description: 校对本仓库「待校对翻译初稿」下的印地语—中文双语 SRT：重点查佛法法义及增译、漏译、错译，先出可编辑校对报告（不改字幕），用户填写校对意见后再按意见修改、存档报告与修改结果、核验并推送。用户说“校对××字幕”“对待校对翻译初稿进行校对”“按校对报告修改字幕”“继续校对××课”时使用。
---

# 印地语双语字幕校对

两个阶段，中间必须停下等用户确认：**阶段一**只出报告，不改字幕；**阶段二**按用户在报告里填的意见修改并交付。用中文与用户交流。

脚本在本 skill 的 `scripts/` 下，用 `python -B` 运行，避免在仓库里留下 `__pycache__`。下文 `$S` 指 `.claude/skills/hindi-subtitle-proofread/scripts`。

## 阶段一：校对出报告

1. **同步与定位**：`git fetch origin` 后把 `origin/main` 合并进当前开发分支，新项目常在远端。在 `待校对翻译初稿/` 找到项目名；用户没指定时列出候选并询问。
2. **版本核对**：交付副本 `待校对翻译初稿/<项目>/hi-zh.srt`、工作稿 `projects/<项目>/drafts/hi-zh.srt`、`verification.json` 的 `candidate_sha256` 三者必须一致；再跑 `python tools/subtitles.py check projects/<项目>`。若交付副本被人工改过，先按 `prompts/proofread.md` 同步回工作稿。只为核对而跑的 `check` 只会改 `checked_at`，用 `git checkout --` 还原该文件，不留无关改动。
3. **完整阅读依据**：`AGENTS.md`、`prompts/proofread.md`、项目 `reviews/translation-notes.md`、交付目录的翻译报告、最新 `review-v*.json`、项目术语快照 `glossary/glossary.csv`、`terminology/proposals.csv` 中本项目的候选，以及 manifest 登记的全部 REF 资料。
   - 用户指定 buli.page 讲记网站（例如 `https://www.buli.page/learn/lesson/...`）可作校对参考。本环境可能无法访问，被拦截时不绕过权限，请用户粘贴原文或代查，并在报告里说明。
4. **逐条通读全部字幕**，不抽查。重点看：
   - **法义**：佛教概念被说成事实或背书（例如外道“认为”变成陈述）、同一词在相邻字幕中两种含义、“功德”指福德（पुण्य）还是佛和法的德能（गुण）、“布施佛法”被读成“向佛教捐献”等。
   - **增译、漏译、错译**：单复数、程度词、语气词（如“早在”“都”）、判断句被弱化成“相关”。
   - **原文疑误**：同音转写错误，例如“声明学家”误为“神秘学家”。对照讲记找出处；字幕中文永不修改，只在报告中提出译文怎么处理。
   - **术语表**：严格使用 target；与语境冲突时提出，不静默替换。
   - **专名**：不按读音拟造人名、经名的原文。
5. **建立可编辑报告**：用 Claude Docs 在线文档，**不存进项目目录**。按 docs 工具的要求先建框架、打开文档，再一节一节填写：
   - 说明：校对对象、指纹核对、已查阅文档、局限（没有音频、哪些资料无法访问）、编号规则。
   - **A 类 建议修改**（错译、漏译、增译）、**B 类 待确认**（法义、术语、原文疑误、需要听音）、**C 类 沿用翻译报告的未决问题**。
   - 编号用字母加数字：A1、B3、C2。每张表的列：编号｜字幕｜类型或问题｜修改前（中文含义）｜建议修改后（中文含义）｜理由或依据｜**校对意见（留空）**。
   - 每处印地语后用括号注明对应中文含义，括号不进入字幕。
   - 来自自身知识、未在项目资料核对的内容，明确标“据我所知”。
   - 已核查、未发现问题的法义要点。
   - 下一步：说明空白意见如何处理。
6. 给出文档链接，说明需要听音的条目，然后**停下等用户填写**。

## 阶段二：按校对意见修改

1. **读取意见**：用 docs 的 `read` 读整份文档（`kind: view`），逐行取「校对意见」栏。
   - A 类意见空白时不要自行决定，用 AskUserQuestion 确认要不要改（以往用户的意思是 A 类默认要改）。B、C 类空白视为维持原译、问题保持 open。
   - “如果有可靠出处再改”：若报告里已给出具体出处（如某论某品），先问用户是否认可该出处；认可后可改，但要记录“出处为校对者所知，未在项目资料中逐字核对”。
   - 用户说“以讲记为准”时，译文可依讲记，中文字幕照旧，并在记录中写明中印两行不一致。
   - 用户要求换算单位、改用全名等，照做；全名优先用术语表已有译名，例如“法王如意宝→धर्मराज चिन्तामणि जिग्मे फुन्त्सोक”。
2. **备份旧交付**：把交付目录现有的 `hi-zh.srt`、`verification.json`、`translation-notes.md` 及翻译报告复制到 `待校对翻译初稿/<项目>/history/v<版本号>-<日期>/`。
3. **术语维护**（有新增或改动时）：
   - 依次处理 `terminology/proposals.csv`（新增行、改 status、补 reason）、`terminology/glossary.csv`（用户同意入表的条目）、`terminology/CHANGELOG.md`。用 csv 模块写，保留原换行符。
   - 新资料登记 `references/catalog.csv`。未亲自读取的写明“用户查阅，未读取正文”。
   - 再运行 `python tools/subtitles.py sync-inputs projects/<项目> --glossary terminology/glossary.csv --reference references/catalog.csv --reference <各REF文件>`。
   - 若报错缺少 `final` 目录：git 不保存空目录，`mkdir projects/<项目>/final` 后重跑，这不代表定稿。
   - 资料快照指纹变化而正文相同，通常是旧快照为 CRLF 换行，在记录里注明即可。
4. **只改印地语行**：先把工作稿复制到 scratchpad 作对照，再写 edits.json（`{"字幕号": ["旧印地语", "新印地语"]}`），运行：
   `python -B $S/apply_edits.py projects/<项目>/drafts/hi-zh.srt <edits.json>`。
   旧文本不逐字匹配、新译文含中文或标点时，脚本会拒绝写入。
5. **核验**：
   - `python tools/subtitles.py check projects/<项目>`，查看 `reviews/verification.json` 的 passed、条数和 errors。
   - `python -B $S/compare_versions.py <修改前副本> projects/<项目>/drafts/hi-zh.srt`，确认只有印地语行变化。
   - `python -B $S/readability.py projects/<项目>`：方法与原报告一致。修改让某条超过 6 词/秒时，在校对单里列为 open，不擅自缩短；如有更短的写法，说明精度代价供用户选。
   - 任何一步失败就停止，不交付、不推送。
6. **新校对单**：`python tools/subtitles.py review projects/<项目> --output reviews/review-v<N+1>.json`，只填 `reviewer`（实际执行校对的 AI 名称，加“校对意见由用户逐条确认”）、带时区的 `reviewed_at`、`checks`、`issues` 和 `notes`。
   - 有 open 问题的检查项保持 false。
   - 已解决的写 resolved 并说明依据，未解决的写 open。
   - 不手改哈希。
7. **存档报告到项目**：写 `projects/<项目>/reviews/proofreading-report-v<轮次>.md`，内容包括：
   - 说明：版本、指纹、修订结果摘要。
   - A、B、C 三张表，原样保留用户的「校对意见」，并增加「处理」列。
   - 末节 `## 修改结果`：`| 字幕 | 校对条目 | 修改前（中文含义） | 修改后（中文含义） |`，覆盖相对上一交付版本的全部改动行。
     - 可用 `compare_versions.py <旧> <新> --table` 生成草稿，再补中文含义。
     - 写完必须运行 `python -B $S/compare_versions.py <基准版本> <当前稿> --check-report <报告>`，表格与实际逐字一致才算完成。
8. **更新记录与交付**：
   - 在 `reviews/translation-notes.md` 末尾追加「第N版修订」一节：依据、改了哪些字幕、未改项、核验结果。在交付目录的翻译报告末尾注明新版本和 history 位置。
   - 把工作稿、`verification.json`、`translation-notes.md` 复制到交付目录。
   - 运行 `python -B $S/delivery_verify.py projects/<项目> 待校对翻译初稿/<项目> reviews/review-v<N+1>.json --note "<版本说明>"`，必须 passed。
   - 复制后若再跑过 `check`，要重新复制 `verification.json`。
9. **提交推送一次**：
   - `git add -A` 前检查 `git status`，不夹带无关改动。
   - 提交说明写清版本和要点，结尾附会话要求的署名行。
   - `git push -u origin <开发分支>` 后，用 `git ls-remote` 核对远端提交。
10. **向用户汇报**：已改条目（按 A/B/C 编号）、未改条目及原因、新出现的问题（例如阅读速度）、中印两行不一致之处、提交号。不运行 finalize，除非用户明确要求定稿。

## 用户偏好（来自以往校对）

- 报告必须可编辑；确认之前不存入项目目录；修改后把校对报告和逐条修改结果一并写入项目 `reviews/`。
- 条目编号用字母加数字，并在表格中留空白的「校对意见」栏；印地语后括号注中文含义。
- 人名身份按中文称谓推断时（如“某某氏”为已婚女性），提出并让用户确认，确认后连带改印地语动词的性别变化。
- 中国传统单位：用户倾向换算为印度读者熟悉的单位，并注明换算依据（例如清代 1 寸约 3.2 厘米）。
- 用户放弃的条目（如“不改了”）在校对单中写 resolved，并注明用户决定维持现译。
