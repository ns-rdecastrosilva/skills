from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import code_review  # noqa: E402


PATCH = """diff --git a/internal/auth/token.go b/internal/auth/token.go
index 1111111..2222222 100644
--- a/internal/auth/token.go
+++ b/internal/auth/token.go
@@ -10,3 +10,4 @@ func Check(token string) bool {
 \tcontext()
-\tremoved()
+\tadded()
+\taddedTwo()
 \tcontextTwo()
diff --git a/web/src/App.tsx b/web/src/App.tsx
new file mode 100644
--- /dev/null
+++ b/web/src/App.tsx
@@ -0,0 +1,2 @@
+export function App() { return null }
+export default App
diff --git a/removed.php b/removed.php
deleted file mode 100644
--- a/removed.php
+++ /dev/null
@@ -1,1 +0,0 @@
-<?php echo "bye";
"""


class AnchorTests(unittest.TestCase):
    def test_parse_anchors_keeps_new_file_lines(self) -> None:
        anchors = code_review.parse_anchors(PATCH)

        self.assertEqual(anchors["internal/auth/token.go"]["added"], [11, 12])
        self.assertEqual(
            anchors["internal/auth/token.go"]["context"], [10, 13]
        )
        self.assertEqual(anchors["web/src/App.tsx"]["added"], [1, 2])
        self.assertNotIn("removed.php", anchors)

    def test_anchored_range_must_be_contiguous_and_present(self) -> None:
        anchors = code_review.parse_anchors(PATCH)
        files = {
            "internal/auth/token.go": {"filename": "internal/auth/token.go"},
            "web/src/App.tsx": {"filename": "web/src/App.tsx"},
        }

        valid = {
            "path": "internal/auth/token.go",
            "line": 12,
            "start_line": 10,
            "comment": "problem",
        }
        self.assertIsNone(code_review.validate_inline(valid, anchors, files))

        outside = {
            "path": "internal/auth/token.go",
            "line": 14,
            "comment": "problem",
        }
        self.assertIn(
            "outside", code_review.validate_inline(outside, anchors, files)
        )

        unknown = {
            "path": "missing.go",
            "line": 1,
            "comment": "problem",
        }
        self.assertIn(
            "not in the PR", code_review.validate_inline(unknown, anchors, files)
        )

        no_body = {
            "path": "web/src/App.tsx",
            "line": 1,
            "comment": " ",
        }
        self.assertIn(
            "no inline", code_review.validate_inline(no_body, anchors, files)
        )

    def test_build_inline_comments_drops_unanchored(self) -> None:
        anchors = code_review.parse_anchors(PATCH)
        files = {
            "internal/auth/token.go": {"filename": "internal/auth/token.go"},
            "web/src/App.tsx": {"filename": "web/src/App.tsx"},
        }
        findings = [
            {
                "severity": "major",
                "path": "internal/auth/token.go",
                "line": 11,
                "comment": "anchored",
                "title": "one",
            },
            {
                "severity": "minor",
                "path": "internal/auth/token.go",
                "line": 99,
                "comment": "missing",
                "title": "two",
            },
        ]

        comments, dropped = code_review.build_inline_comments(
            findings, anchors, files
        )

        self.assertEqual([item["line"] for item in comments], [11])
        self.assertEqual([item["title"] for item in dropped], ["two"])

    def test_content_that_looks_like_a_header_stays_in_the_hunk(self) -> None:
        patch = """diff --git a/x.txt b/x.txt
--- a/x.txt
+++ b/x.txt
@@ -1,1 +1,3 @@
 keep
+++ this is added content
+--- this is also added
"""
        anchors = code_review.parse_anchors(patch)
        self.assertEqual(anchors["x.txt"]["context"], [1])
        self.assertEqual(anchors["x.txt"]["added"], [2, 3])

    def test_equal_start_line_is_single_line(self) -> None:
        anchors = code_review.parse_anchors(PATCH)
        files = {"web/src/App.tsx": {"filename": "web/src/App.tsx"}}
        comments, _ = code_review.build_inline_comments(
            [
                {
                    "severity": "minor",
                    "path": "web/src/App.tsx",
                    "line": 1,
                    "start_line": 1,
                    "comment": "body",
                    "title": "x",
                }
            ],
            anchors,
            files,
        )
        self.assertNotIn("start_line", comments[0])

    def test_range_cannot_cross_hunks(self) -> None:
        patch = """diff --git a/x.txt b/x.txt
--- a/x.txt
+++ b/x.txt
@@ -1,1 +1,1 @@
 one
@@ -2,1 +2,1 @@
 two
"""
        anchors = code_review.parse_anchors(patch)
        files = {"x.txt": {"filename": "x.txt"}}
        finding = {
            "path": "x.txt",
            "line": 2,
            "start_line": 1,
            "comment": "body",
        }
        self.assertIn(
            "crosses a hunk boundary",
            code_review.validate_inline(finding, anchors, files),
        )
        finding.pop("start_line")
        self.assertIsNone(code_review.validate_inline(finding, anchors, files))


class EventTests(unittest.TestCase):
    def test_critical_requests_changes(self) -> None:
        self.assertEqual(
            code_review.derive_event(
                False, False, {"critical": 1, "major": 0, "minor": 0}
            ),
            "REQUEST_CHANGES",
        )

    def test_major_comments(self) -> None:
        self.assertEqual(
            code_review.derive_event(
                False, False, {"critical": 0, "major": 1, "minor": 3}
            ),
            "COMMENT",
        )

    def test_minor_approves(self) -> None:
        self.assertEqual(
            code_review.derive_event(
                False, False, {"critical": 0, "major": 0, "minor": 2}
            ),
            "APPROVE",
        )

    def test_clean_pr_approves(self) -> None:
        self.assertEqual(
            code_review.derive_event(
                False, False, {"critical": 0, "major": 0, "minor": 0}
            ),
            "APPROVE",
        )

    def test_own_pr_and_draft_only_comment(self) -> None:
        counts = {"critical": 2, "major": 2, "minor": 2}
        self.assertEqual(code_review.derive_event(True, False, counts), "COMMENT")
        self.assertEqual(code_review.derive_event(False, True, counts), "COMMENT")


class FindingTests(unittest.TestCase):
    def test_rejects_extra_severity(self) -> None:
        with self.assertRaises(code_review.ReviewError):
            code_review.normalize_findings(
                [{"severity": "nit", "path": "a.go", "title": "x"}]
            )

    def test_normalizes_case(self) -> None:
        findings = code_review.normalize_findings(
            [{"severity": "CRITICAL", "path": "a.go", "title": "x"}]
        )
        self.assertEqual(findings[0]["severity"], "critical")

    def test_counts(self) -> None:
        counts = code_review.count_findings(
            [
                {"severity": "critical"},
                {"severity": "major"},
                {"severity": "major"},
                {"severity": "minor"},
            ]
        )
        self.assertEqual(counts, {"critical": 1, "major": 2, "minor": 1})


class HelperTests(unittest.TestCase):
    def test_flatten_pages(self) -> None:
        self.assertEqual(
            code_review.flatten_pages([[{"id": 1}], [{"id": 2}]]),
            [{"id": 1}, {"id": 2}],
        )
        self.assertEqual(code_review.flatten_pages([{"id": 1}]), [{"id": 1}])

    def test_render_findings_section_keeps_code(self) -> None:
        text = code_review.render_findings_section(
            [
                {
                    "path": "a.go",
                    "line": 7,
                    "title": "Title",
                    "comment": "**Title**\n\n```suggestion\nx\n```",
                }
            ],
            "Findings without inline anchors",
        )
        self.assertIn("a.go:7", text)
        self.assertIn("```suggestion", text)
        self.assertIn("### `a.go:7` - Title", text)
        self.assertEqual(text.count("**Title**"), 0)

    def test_write_and_load_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final.json"
            path.write_text(
                json.dumps(
                    {
                        "findings": [
                            {
                                "severity": "Minor",
                                "path": "a.go",
                                "title": "x",
                            }
                        ]
                    }
                )
            )
            findings = code_review.load_findings(path)
            self.assertEqual(findings[0]["severity"], "minor")

    def test_ensure_marker_moves_to_end_once(self) -> None:
        marker = "<!-- rs-code-review:abc -->"
        body = f"body\n\n{marker}\n\nmore"
        result = code_review.ensure_marker(body, marker)
        self.assertEqual(result.count(marker), 1)
        self.assertTrue(result.rstrip().endswith(marker))

    def test_missing_body_findings_skips_inline(self) -> None:
        findings = [
            {"title": "inline", "inline": True},
            {"title": "body", "inline": False},
        ]
        self.assertEqual(
            [
                f["title"]
                for f in code_review.missing_body_findings(
                    findings, "inline only", include_inline=False
                )
            ],
            ["body"],
        )
        self.assertEqual(
            [
                f["title"]
                for f in code_review.missing_body_findings(
                    findings, "none", include_inline=True
                )
            ],
            ["inline", "body"],
        )

    def test_body_size_guard(self) -> None:
        code_review.check_body_size("x" * 10)
        with self.assertRaises(code_review.ReviewError):
            code_review.check_body_size("x" * 60001)

    def test_body_preamble_guard(self) -> None:
        code_review.check_body_preamble(
            "I found one security problem. 1 major.\n\n"
            "Major is a suggestion worth a calm look."
        )
        for body in (
            "## Code review\n\nI found one problem.",
            "Reviewed `05061ac` (23 files, +620/-283).\n\nI found one problem.",
            "Reviewed `05061ac`.\n\nI found one problem.",
            "I found one problem.\n\nSkills: `code-review`, `security-review`",
            "**Verdict: Comment.** 1 major, 0 minor.",
        ):
            with self.subTest(body=body):
                with self.assertRaises(code_review.ReviewError):
                    code_review.check_body_preamble(body)

    def test_body_index_guard(self) -> None:
        findings = [{"path": "a.go", "line": 7, "title": "Empty token"}]
        comments = [{"path": "a.go", "line": 7}]
        code_review.check_body_index(
            "I found one auth problem. 1 major.", findings, comments
        )
        with self.assertRaises(code_review.ReviewError):
            code_review.check_body_index(
                "- `a.go:7` Empty token", findings, comments
            )
        code_review.check_body_index("- `a.go:7` Empty token", findings, [])

    def test_inline_duplication_guard(self) -> None:
        findings = [
            {
                "path": "a.go",
                "line": 7,
                "fix": "Reject whitespace-only tokens before the role check.",
                "suggestion": "if strings.TrimSpace(token) != \"\" {",
            }
        ]
        comments = [{"path": "a.go", "line": 7}]
        code_review.check_inline_duplication(
            "- `a.go:7` Empty token passes the admin guard", findings, comments
        )
        with self.assertRaises(code_review.ReviewError):
            code_review.check_inline_duplication(
                "Reject whitespace-only tokens before the role check.",
                findings,
                comments,
            )
        with self.assertRaises(code_review.ReviewError):
            code_review.check_inline_duplication(
                "if strings.TrimSpace(token) != \"\" {", findings, comments
            )
        code_review.check_inline_duplication(
            "Reject whitespace-only tokens before the role check.", findings, []
        )

    def test_brief_body_cap(self) -> None:
        findings = [{"path": "a.go", "line": 1}, {"path": "b.go", "line": 2}]
        comments = [{"path": "a.go", "line": 1}, {"path": "b.go", "line": 2}]
        code_review.check_brief_body(
            "I found two problems. 1 major, 1 minor.", findings, comments
        )
        with self.assertRaises(code_review.ReviewError):
            code_review.check_brief_body("x" * 1601, findings, comments)
        code_review.check_brief_body("x" * 5000, findings, comments[:1])

    def test_first_url(self) -> None:
        self.assertEqual(
            code_review.first_url(
                "https://github.com/o/r/pull/1#issuecomment-2\n",
                "fallback",
            ),
            "https://github.com/o/r/pull/1#issuecomment-2",
        )
        self.assertEqual(code_review.first_url("no url", "fallback"), "fallback")

    def test_cmd_anchors_writes_anchor_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            diff = Path(tmp) / "diff.patch"
            diff.write_text(PATCH)
            out = Path(tmp) / "anchors.json"
            args = argparse.Namespace(diff=str(diff), out=str(out))
            with contextlib.redirect_stdout(io.StringIO()):
                code = code_review.cmd_anchors(args)

            self.assertEqual(code, 0)
            anchors = json.loads(out.read_text())
            self.assertEqual(
                anchors["internal/auth/token.go"]["added"], [11, 12]
            )
            self.assertEqual(
                anchors["internal/auth/token.go"]["hunks"], [[10, 13]]
            )


if __name__ == "__main__":
    unittest.main()
