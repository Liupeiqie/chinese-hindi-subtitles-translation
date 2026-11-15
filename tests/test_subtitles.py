import tempfile
import unittest
from pathlib import Path

from tools import subtitles as workflow


SOURCE = "1\n00:00:01,000 --> 00:00:03,000\n你好。\n第二行中文。\n\n2\n00:00:04,000 --> 00:00:06,000\n谢谢。\n"
BILINGUAL = "1\n00:00:01,000 --> 00:00:03,000\nनमस्ते।\nचीनी की दूसरी पंक्ति।\n你好。\n第二行中文。\n\n2\n00:00:04,000 --> 00:00:06,000\nधन्यवाद।\n谢谢。\n"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original.srt"
        self.source.write_text(SOURCE, encoding="utf-8", newline="\n")
        self.glossary = self.root / "glossary.csv"
        self.glossary.write_text("source,target,note,reference\n", encoding="utf-8", newline="\n")
        self.reference = self.root / "讲记.md"
        self.reference.write_text("# 第1讲\n资料正文\n", encoding="utf-8", newline="\n")
        self.project = workflow.new_project("课程-001", self.source, self.glossary, self.root / "projects", [self.reference])
        self.candidate = self.project / "drafts/hi-zh.srt"

    def translated(self, text=BILINGUAL):
        self.candidate.write_text(text, encoding="utf-8", newline="\n")

    def approved_review(self):
        self.translated()
        path = workflow.make_review(self.project)
        value = workflow.read_json(path)
        value.update(reviewer="测试校对员", reviewed_at="2026-11-15T14:00:00+08:00")
        value["checks"] = dict.fromkeys(workflow.CHECKS, True)
        workflow.write_json(path, value)
        return path, value

    def test_prepare_preserves_source_and_blocks_placeholder(self):
        self.assertEqual(self.source.read_bytes(), (self.project / "source/zh.srt").read_bytes())
        self.assertFalse(workflow.check_project(self.project)["passed"])

    def test_valid_multiline_bilingual(self):
        self.translated()
        self.assertTrue(workflow.check_project(self.project)["passed"])

    def test_detects_each_protected_change(self):
        variants = {
            "Chinese": BILINGUAL.replace("你好。", "您好。"),
            "Chinese spacing": BILINGUAL.replace("你好。", "你好。 "),
            "Chinese wrapping": BILINGUAL.replace("你好。\n第二行中文。", "你好。第二行中文。"),
            "index": BILINGUAL.replace("1\n00:", "01\n00:", 1),
            "timing": BILINGUAL.replace("00:00:01,000", "00:00:01,001"),
            "missing translation": BILINGUAL.replace("धन्यवाद।\n", ""),
            "missing cue": BILINGUAL.split("\n\n")[0],
            "extra cue": BILINGUAL + "\n3\n00:00:07,000 --> 00:00:08,000\n添加\n",
            "order": "\n\n".join(reversed(BILINGUAL.strip().split("\n\n"))) + "\n",
        }
        for label, text in variants.items():
            with self.subTest(label=label):
                self.translated(text)
                self.assertFalse(workflow.check_project(self.project)["passed"])

    def test_bom_and_crlf_are_allowed_for_comparison(self):
        self.candidate.write_bytes(b"\xef\xbb\xbf" + BILINGUAL.replace("\n", "\r\n").encode("utf-8"))
        self.assertTrue(workflow.compare(self.source, self.candidate)["passed"])

    def test_invalid_srt_rejected(self):
        for text in ("", "无序号\n00:00:01,000 --> 00:00:02,000\n中文", SOURCE.replace("00:00:01,000", "00:61:01,000"), SOURCE.replace("00:00:03,000", "00:00:00,000")):
            with self.subTest(text=text):
                self.translated(text)
                with self.assertRaises(ValueError):
                    workflow.parse_srt(self.candidate)

    def test_source_tampering_rejected(self):
        self.translated()
        (self.project / "source/zh.srt").write_text(SOURCE.replace("你好", "您好"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "冻结输入"):
            workflow.check_project(self.project)

    def test_glossary_tampering_rejected(self):
        (self.project / "glossary/glossary.csv").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "冻结输入"):
            workflow.check_project(self.project)

    def test_reference_tampering_rejected(self):
        manifest = workflow.read_json(self.project / "manifest.json")
        (self.project / manifest["references"][0]["path"]).write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "参考资料"):
            workflow.check_project(self.project)

    def test_review_does_not_overwrite(self):
        self.translated()
        workflow.make_review(self.project)
        with self.assertRaises(FileExistsError):
            workflow.make_review(self.project)

    def test_unreviewed_cannot_finalize(self):
        self.translated()
        workflow.make_review(self.project)
        with self.assertRaisesRegex(ValueError, "校对人"):
            workflow.finalize(self.project)

    def test_review_validation(self):
        path, valid = self.approved_review()
        for changes in ({"reviewed_at": "2026-11-15T14:00:00"}, {"checks": dict.fromkeys(workflow.CHECKS, "true")}, {"issues": [{"cue": "1", "description": "待核实", "status": "open"}]}, {"issues": [{"status": "resolved"}]}):
            with self.subTest(changes=changes):
                workflow.write_json(path, {**valid, **changes})
                with self.assertRaises(ValueError):
                    workflow.finalize(self.project)
                self.assertFalse((self.project / "final/hi-zh.srt").exists())

    def test_translation_edit_invalidates_review(self):
        self.approved_review()
        self.translated(BILINGUAL.replace("नमस्ते।", "नमस्कार।"))
        with self.assertRaisesRegex(ValueError, "已失效"):
            workflow.finalize(self.project)

    def test_glossary_sync_archives_and_invalidates_review(self):
        self.approved_review()
        old = (self.project / "glossary/glossary.csv").read_bytes()
        self.glossary.write_text("source,target,note,reference\n你好,नमस्ते,测试,REF-001\n", encoding="utf-8")
        archive = workflow.sync_inputs(self.project, self.glossary)
        self.assertEqual((archive / "glossary.csv").read_bytes(), old)
        self.assertTrue(workflow.check_project(self.project)["passed"])
        with self.assertRaisesRegex(ValueError, "已失效"):
            workflow.finalize(self.project)

    def test_reference_sync_invalidates_review(self):
        self.approved_review()
        self.reference.write_text("新版资料", encoding="utf-8")
        workflow.sync_inputs(self.project, self.glossary, [self.reference])
        self.assertEqual(len(list((self.project / "references").iterdir())), 2)
        with self.assertRaisesRegex(ValueError, "已失效"):
            workflow.finalize(self.project)

    def test_sync_before_translation_is_allowed(self):
        workflow.sync_inputs(self.project, self.glossary)
        self.assertFalse(workflow.check_project(self.project)["passed"])

    def test_finalize_receipt_and_protection(self):
        review, value = self.approved_review()
        value["issues"] = [{"cue": "1", "description": "已核实", "status": "resolved"}]
        workflow.write_json(review, value)
        output = workflow.finalize(self.project)
        self.assertEqual(output.read_bytes(), self.candidate.read_bytes())
        receipt = workflow.read_json(self.project / "final/release.json")
        self.assertEqual(receipt["final_sha256"], workflow.digest(output))
        self.assertEqual(receipt["review_sha256"], workflow.digest(review))
        with self.assertRaisesRegex(ValueError, "禁止覆盖"):
            workflow.finalize(self.project)
        with self.assertRaisesRegex(ValueError, "已定稿"):
            workflow.sync_inputs(self.project, self.glossary)

    def test_glossary_invalid_rows_rejected(self):
        for text in ("source,target,note\n", "source,target,note,reference\n词,,说明,\n", "source,target,note,reference\n词,译法,,\n词,另一译法,,\n", "source,target,note,reference\n词,译法,\n"):
            with self.subTest(text=text):
                self.glossary.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    workflow.validate_glossary(self.glossary)

    def test_path_and_project_overwrite_guards(self):
        self.translated()
        for path in ("../outside.json", "manifest.json", "reviews/../../outside.json"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    workflow.make_review(self.project, path)
        with self.assertRaises(FileExistsError):
            workflow.new_project("课程-001", self.source, self.glossary, self.root / "projects")
        for name in ("../outside", "CON", "a/b", "bad."):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    workflow.new_project(name, self.source, self.glossary, self.root / "projects")


if __name__ == "__main__":
    unittest.main()
