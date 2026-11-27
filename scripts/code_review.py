#!/usr/bin/env python3
"""Deterministic helpers for the /rs:code-review command.

Subcommands:

  anchors  Parse a PR diff and write the new-file lines and hunk ranges that
           GitHub accepts for inline review comments.

  post     Validate synthesized findings, derive the review event from the
           three severities, and post. A PR authored by the current user gets
           an issue comment only. A draft or own PR never gets
           approve/request-changes.

The command uses gh for PR metadata, diff, files, spec, and language
selection. This script owns only diff line math and the atomic GitHub review
call. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

MARKER = "<!-- rs-code-review:{sha} -->"
MAX_INLINE = 30
SEVERITIES = ("critical", "major", "minor")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
# The review body is a short human note. A banner, a reviewed-SHA line, a
# skills line, or a verdict header adds nothing the author can act on.
PREAMBLE_RE = re.compile(
    r"^#{1,3}[ \t]*Code review[ \t]*$"
    r"|^Reviewed[ \t]+`?[0-9a-f]{7,40}"
    r"|^Skills:",
    re.MULTILINE,
)
VERDICT_RE = re.compile(r"^[ \t]*(?:\*\*)?Verdict:", re.MULTILINE)


class ReviewError(RuntimeError):
    """User-facing failure with an actionable message."""


def run(
    args: Iterable[Any],
    *,
    cwd: Optional[Path] = None,
    check: bool = True,
    stdin: Optional[str] = None,
) -> subprocess.CompletedProcess:
    cmd = [str(arg) for arg in args]
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=stdin,
        text=True,
        capture_output=True,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise ReviewError(f"{' '.join(cmd)} failed: {detail}")
    return proc


def gh_json(args: Iterable[Any], cwd: Optional[Path] = None) -> Any:
    proc = run(["gh", *args], cwd=cwd)
    if not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ReviewError(f"gh returned invalid JSON: {exc}") from exc


def repo_root(cwd: Path) -> Path:
    proc = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(proc.stdout.strip())


def flatten_pages(data: Any) -> List[Dict[str, Any]]:
    """Flatten `gh api --paginate --slurp` output into one list."""
    if not isinstance(data, list):
        return []
    if data and all(isinstance(page, list) for page in data):
        return [item for page in data for item in page]
    return [item for item in data if isinstance(item, dict)]


def parse_anchors(patch: str) -> Dict[str, Dict[str, Any]]:
    """Map every changed file to the new-file lines present in the diff.

    Added and context lines anchor review comments. Removed lines do not:
    GitHub anchors comments on the RIGHT side of the diff. Hunks are recorded
    so multi-line comments cannot cross a hunk boundary.
    """
    anchors: Dict[str, Dict[str, Any]] = {}
    current: Optional[str] = None
    new_line = 0
    in_hunk = False

    for raw in patch.splitlines():
        if raw.startswith("diff --git "):
            current = None
            in_hunk = False
            continue
        if raw.startswith("+++ ") and not in_hunk:
            target = raw[4:].strip()
            if target == "/dev/null":
                current = None
            else:
                if target.startswith('"') and target.endswith('"'):
                    try:
                        target = target[1:-1].encode().decode("unicode_escape")
                    except UnicodeDecodeError:
                        target = target[1:-1]
                if target.startswith("b/"):
                    target = target[2:]
                current = target
                anchors.setdefault(
                    current, {"added": set(), "context": set(), "hunks": []}
                )
            continue
        if raw.startswith("--- ") and not in_hunk:
            continue
        match = HUNK_RE.match(raw)
        if match:
            new_line = int(match.group(1))
            in_hunk = True
            if current is not None:
                anchors[current]["hunks"].append([new_line, new_line])
            continue
        if current is None:
            continue
        if raw.startswith("+"):
            anchors[current]["added"].add(new_line)
            anchors[current]["hunks"][-1][1] = new_line
            new_line += 1
        elif raw.startswith("-"):
            continue
        elif raw.startswith(" "):
            anchors[current]["context"].add(new_line)
            anchors[current]["hunks"][-1][1] = new_line
            new_line += 1
        # "\ No newline at end of file" needs no handling.

    return {
        path: {
            "added": sorted(lines["added"]),
            "context": sorted(lines["context"]),
            "hunks": lines["hunks"],
        }
        for path, lines in anchors.items()
    }


def anchored_lines(anchors: Dict[str, Dict[str, Any]], path: str) -> Set[int]:
    entry = anchors.get(path) or {}
    return set(entry.get("added") or []) | set(entry.get("context") or [])


def ensure_marker(body: str, marker: str) -> str:
    """Keep exactly one marker and put it at the end of the review body."""
    cleaned = body.replace(marker, "").rstrip()
    return cleaned + "\n\n" + marker + "\n"


def missing_body_findings(
    findings: List[Dict[str, Any]], body: str, include_inline: bool = False
) -> List[Dict[str, Any]]:
    missing = []
    for finding in findings:
        if not include_inline and finding.get("inline", True):
            continue
        if finding["title"] not in body:
            missing.append(finding)
    return missing


def check_body_size(body: str, label: str = "review body") -> None:
    if len(body) > 60000:
        raise ReviewError(
            f"{label} has {len(body)} characters; GitHub rejects bodies over 65536. "
            "Trim Minor findings or split the review."
        )


def check_body_preamble(body: str) -> None:
    """Reject a banner, a reviewed-SHA line, a skills line, or a verdict header."""
    match = PREAMBLE_RE.search(body)
    if match:
        raise ReviewError(
            f"review body contains a tooling preamble: {match.group(0)!r}. "
            "Start with the short summary and keep the skills in the run receipt."
        )
    verdict = VERDICT_RE.search(body)
    if verdict:
        raise ReviewError(
            f"review body contains a verdict header: {verdict.group(0)!r}. "
            "Write a short human summary with the counts and what each present "
            "severity means instead."
        )


def check_inline_duplication(
    body: str,
    findings: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
) -> None:
    """Reject detail repeated in the body for a finding that got an inline comment.

    The explanation belongs next to the code. The body holds one pointer line.
    """
    posted = {(comment["path"], comment["line"]) for comment in comments}
    if not posted:
        return
    offenders: List[str] = []
    for finding in findings:
        key = (finding["path"], finding.get("line"))
        if key not in posted:
            continue
        fix = str(finding.get("fix") or "").strip()
        suggestion = str(finding.get("suggestion") or "").strip()
        where = f"{finding['path']}:{finding.get('line')}"
        if len(fix) >= 24 and fix in body:
            offenders.append(f"{where} repeats its fix sentence")
        elif len(suggestion) >= 24 and suggestion in body:
            offenders.append(f"{where} repeats its suggested code")
    if offenders:
        raise ReviewError(
            "review body duplicates inline findings: "
            + "; ".join(offenders[:5])
            + ". Keep one bullet per inline finding and put the detail in its comment."
        )


def check_body_index(
    body: str,
    findings: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
) -> None:
    """Reject a file index in the body for findings that got an inline comment."""
    posted = {(comment["path"], comment.get("line")) for comment in comments}
    if not posted:
        return
    offenders: List[str] = []
    for finding in findings:
        key = (finding["path"], finding.get("line"))
        if key not in posted:
            continue
        location = f"{finding['path']}:{finding.get('line')}"
        if location in body:
            offenders.append(location)
    if offenders:
        raise ReviewError(
            "review body lists inline findings by file: "
            + ", ".join(offenders[:5])
            + ". The location lives in the inline comment. Keep the body to the "
            "summary, the counts, and what each severity means."
        )


def check_brief_body(
    body: str,
    findings: List[Dict[str, Any]],
    comments: List[Dict[str, Any]],
) -> None:
    """Hard cap when every finding can live in an inline comment."""
    if not findings or len(comments) != len(findings):
        return
    limit = 1600
    if len(body) > limit:
        raise ReviewError(
            f"review body has {len(body)} characters for {len(findings)} inline "
            f"findings; the short-note cap is {limit}. Keep the summary, the "
            "counts, and the severity meaning, and move the rest into the inline "
            "comments."
        )


def first_url(text: str, fallback: Optional[str]) -> Optional[str]:
    match = re.search(r"https?://\S+", text or "")
    return match.group(0) if match else fallback


def derive_event(own_pr: bool, is_draft: bool, counts: Dict[str, int]) -> str:
    if own_pr or is_draft:
        return "COMMENT"
    if counts.get("critical", 0) > 0:
        return "REQUEST_CHANGES"
    if counts.get("major", 0) > 0:
        return "COMMENT"
    return "APPROVE"


def count_findings(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        severity = str(finding.get("severity", "")).strip().lower()
        if severity not in counts:
            raise ReviewError(f"unknown severity: {finding.get('severity')!r}")
        counts[severity] += 1
    return counts


def normalize_findings(data: Any) -> List[Dict[str, Any]]:
    items = data.get("findings") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ReviewError("findings must be a list or an object with a findings list")

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ReviewError("every finding must be an object")
        severity = str(item.get("severity", "")).strip().lower()
        if severity not in SEVERITIES:
            raise ReviewError(
                f"severity must be Critical, Major, or Minor: {item.get('severity')!r}"
            )
        path = str(item.get("path", "")).strip()
        if not path:
            raise ReviewError("every finding needs a path")
        title = str(item.get("title", "")).strip()
        if not title:
            raise ReviewError(f"{path}: finding without a title")
        normalized.append(
            {
                **item,
                "severity": severity,
                "path": path,
                "title": title,
            }
        )
    return normalized


def load_findings(path: Path) -> List[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ReviewError(f"findings file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReviewError(f"findings file is not valid JSON: {path}: {exc}") from exc
    return normalize_findings(data)


def validate_inline(
    finding: Dict[str, Any],
    anchors: Dict[str, Dict[str, Any]],
    files_by_path: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    if finding.get("inline") is False:
        return "inline disabled"
    path = finding["path"]
    if path not in files_by_path:
        return f"{path} is not in the PR"
    line = finding.get("line")
    if not isinstance(line, int):
        return "no line"
    start = finding.get("start_line")
    if start is not None:
        if not isinstance(start, int):
            return "start_line is not an integer"
        if start > line:
            return "start_line is after line"
    allowed = anchored_lines(anchors, path)
    first = start if start is not None else line
    if any(number not in allowed for number in range(first, line + 1)):
        return f"line range {first}-{line} is outside the diff"
    hunks = (anchors.get(path) or {}).get("hunks") or []
    if not any(
        int(hunk[0]) <= first and line <= int(hunk[1]) for hunk in hunks
    ):
        return f"line range {first}-{line} crosses a hunk boundary"
    if not str(finding.get("comment") or "").strip():
        return "no inline comment body"
    return None


def build_inline_comments(
    findings: List[Dict[str, Any]],
    anchors: Dict[str, Dict[str, Any]],
    files_by_path: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    comments: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for finding in findings:
        reason = validate_inline(finding, anchors, files_by_path)
        if reason:
            dropped.append(finding)
            continue
        if len(comments) >= MAX_INLINE:
            dropped.append(finding)
            continue
        comment: Dict[str, Any] = {
            "path": finding["path"],
            "line": finding["line"],
            "side": "RIGHT",
            "body": finding["comment"],
        }
        if (
            finding.get("start_line") is not None
            and finding["start_line"] != finding["line"]
        ):
            comment["start_line"] = finding["start_line"]
            comment["start_side"] = "RIGHT"
        comments.append(comment)

    return comments, dropped


def render_findings_section(findings: List[Dict[str, Any]], title: str) -> str:
    if not findings:
        return ""
    parts = [f"**{title}**", ""]
    for finding in findings:
        location = finding["path"]
        if finding.get("line") is not None:
            location = f"{location}:{finding['line']}"
        heading = f"### `{location}`"
        title = str(finding.get("title") or "").strip()
        if title:
            heading += f" - {title}"
        body = str(finding.get("comment") or "").strip()
        if not body:
            body = str(finding.get("problem") or finding.get("fix") or "").strip()
        elif title:
            first, _, rest = body.partition("\n")
            if first.strip().strip("*").strip() == title:
                body = rest.strip()
        parts.extend([heading, "", body, ""])
    return "\n".join(parts).rstrip() + "\n"


def fetch_files(repo: str, number: int, cwd: Path) -> List[Dict[str, Any]]:
    data = gh_json(
        [
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/pulls/{number}/files?per_page=100",
        ],
        cwd=cwd,
    )
    return flatten_pages(data)


def find_existing_review(
    ctx: Dict[str, Any], marker: str, cwd: Path
) -> Optional[str]:
    me = ctx.get("me")
    if not me:
        return None
    repo = ctx["repo"]
    number = ctx["number"]

    if ctx.get("own_pr"):
        data = gh_json(["pr", "view", str(number), "--json", "comments"], cwd=cwd)
        for comment in (data or {}).get("comments") or []:
            author = ((comment.get("author") or {}).get("login") or "").lower()
            if author == str(me).lower() and marker in str(comment.get("body") or ""):
                return (
                    comment.get("url")
                    or f"{ctx.get('url')}#issuecomment-{comment.get('id')}"
                )
        return None

    data = gh_json(
        [
            "api",
            "--paginate",
            "--slurp",
            f"repos/{repo}/pulls/{number}/reviews?per_page=100",
        ],
        cwd=cwd,
    )
    for review in flatten_pages(data):
        author = ((review.get("user") or {}).get("login") or "").lower()
        if (
            author == str(me).lower()
            and review.get("commit_id") == ctx.get("head_sha")
            and marker in str(review.get("body") or "")
        ):
            return review.get("html_url")
    return None


def cmd_anchors(args: argparse.Namespace) -> int:
    diff_path = Path(args.diff).expanduser()
    try:
        patch = diff_path.read_text()
    except FileNotFoundError as exc:
        raise ReviewError(f"diff not found: {diff_path}") from exc

    anchors = parse_anchors(patch)
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(anchors, indent=2))

    summary = {
        "files": len(anchors),
        "anchors": sum(
            len(entry.get("added") or []) + len(entry.get("context") or [])
            for entry in anchors.values()
        ),
        "out": str(out_path),
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_post(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().resolve()
    cwd = repo_root(Path.cwd())
    repo = gh_json(["repo", "view", "--json", "nameWithOwner"], cwd=cwd)[
        "nameWithOwner"
    ]
    number = int(args.pr)
    head_sha = str(args.head_sha)

    current = gh_json(
        [
            "pr",
            "view",
            str(number),
            "--json",
            "headRefOid,state,isDraft,author,url",
        ],
        cwd=cwd,
    )
    if (current or {}).get("state") != "OPEN":
        raise ReviewError(f"PR #{number} is no longer open")
    if (current or {}).get("headRefOid") != head_sha:
        raise ReviewError(
            f"PR head moved from {head_sha[:7]} to "
            f"{str(current.get('headRefOid'))[:7]}. Re-run Phase 1."
        )

    me = None
    try:
        me = gh_json(["api", "user"], cwd=cwd).get("login")
    except (ReviewError, AttributeError):
        me = None
    author = str((current.get("author") or {}).get("login") or "")
    own_pr = bool(me and author and str(me).lower() == author.lower())
    is_draft = bool(current.get("isDraft"))
    ctx = {
        "repo": repo,
        "number": number,
        "head_sha": head_sha,
        "url": current.get("url"),
        "me": me,
        "own_pr": own_pr,
    }

    findings = load_findings(Path(args.findings).expanduser())
    counts = count_findings(findings)
    event = derive_event(own_pr, is_draft, counts)

    body_path = Path(args.body).expanduser()
    body = body_path.read_text().rstrip()
    if not body:
        raise ReviewError(f"review body is empty: {body_path}")
    marker = MARKER.format(sha=head_sha)

    files_path = run_dir / "files.json"
    if files_path.exists():
        files = json.loads(files_path.read_text())
    else:
        files = fetch_files(repo, number, cwd)
    files_by_path = {str(item.get("filename")): item for item in files}

    anchors_path = run_dir / "anchors.json"
    if not anchors_path.exists():
        raise ReviewError(
            f"anchors not found: {anchors_path}. Run `code_review.py anchors` first."
        )
    anchors = json.loads(anchors_path.read_text())

    if own_pr:
        missing = missing_body_findings(findings, body, include_inline=True)
        if missing:
            body += "\n\n" + render_findings_section(missing, "Additional findings")
        suggested = [
            finding
            for finding in findings
            if str(finding.get("suggestion") or "").strip()
            and str(finding["suggestion"]) not in body
        ]
        if suggested:
            body += "\n\n" + render_findings_section(
                suggested, "Suggested changes (review-only)"
            )
        body = ensure_marker(body, marker)
        check_body_size(body)
        check_body_preamble(body)
        (run_dir / "review.md").write_text(body)

        if args.dry_run:
            result = {
                "posted": False,
                "dry_run": True,
                "own_pr": True,
                "event": "COMMENT",
                "body_path": str(run_dir / "review.md"),
                "inline": 0,
                "body_only": len(findings),
                **{key: counts[key] for key in SEVERITIES},
            }
            (run_dir / "post-result.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2))
            return 0

        if not args.force:
            existing = find_existing_review(ctx, marker, cwd)
            if existing:
                result = {
                    "posted": False,
                    "existing": True,
                    "own_pr": True,
                    "event": "COMMENT",
                    "url": existing,
                    "inline": 0,
                    "body_only": len(findings),
                    **{key: counts[key] for key in SEVERITIES},
                }
                (run_dir / "post-result.json").write_text(json.dumps(result, indent=2))
                print(json.dumps(result, indent=2))
                return 0

        proc = run(
            [
                "gh",
                "pr",
                "comment",
                str(number),
                "--body-file",
                str(run_dir / "review.md"),
            ],
            cwd=cwd,
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            raise ReviewError(f"gh pr comment failed: {detail}")
        result = {
            "posted": True,
            "own_pr": True,
            "event": "COMMENT",
            "url": first_url(proc.stdout, ctx.get("url")),
            "inline": 0,
            "body_only": len(findings),
            **{key: counts[key] for key in SEVERITIES},
        }
        (run_dir / "post-result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return 0

    comments, dropped = build_inline_comments(findings, anchors, files_by_path)
    if dropped:
        section = render_findings_section(dropped, "Findings without inline anchors")
        if section:
            body += "\n\n" + section
    missing = missing_body_findings(findings, body, include_inline=False)
    if missing:
        section = render_findings_section(missing, "Additional findings")
        if section:
            body += "\n\n" + section
    body = ensure_marker(body, marker)
    check_body_size(body)
    check_body_preamble(body)
    check_inline_duplication(body, findings, comments)
    check_body_index(body, findings, comments)
    check_brief_body(body, findings, comments)

    payload = {
        "commit_id": head_sha,
        "event": event,
        "body": body,
        "comments": comments,
    }
    payload_path = run_dir / "payload.json"
    payload_path.write_text(json.dumps(payload, indent=2))

    if args.dry_run:
        result = {
            "posted": False,
            "dry_run": True,
            "own_pr": False,
            "event": event,
            "payload_path": str(payload_path),
            "inline": len(comments),
            "body_only": len(dropped),
            **{key: counts[key] for key in SEVERITIES},
        }
        (run_dir / "post-result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return 0

    if not args.force:
        existing = find_existing_review(ctx, marker, cwd)
        if existing:
            result = {
                "posted": False,
                "existing": True,
                "own_pr": False,
                "event": event,
                "url": existing,
                "inline": len(comments),
                "body_only": len(dropped),
                **{key: counts[key] for key in SEVERITIES},
            }
            (run_dir / "post-result.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2))
            return 0

    proc = run(
        [
            "gh",
            "api",
            "--method",
            "POST",
            f"repos/{repo}/pulls/{number}/reviews",
            "--input",
            "-",
        ],
        cwd=cwd,
        stdin=json.dumps(payload),
        check=False,
    )

    fallback = False
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        lowered = detail.lower()
        if "pending review" in lowered:
            raise ReviewError(
                "You have a pending review on this PR. Submit or discard it, then retry."
            )
        if "your own pull request" in lowered:
            raise ReviewError(
                "GitHub refuses approve or request changes on your own PR. "
                "Ensure `gh api user` resolves the PR author so the command posts "
                "an issue comment."
            )
        if "422" not in detail and "Unprocessable" not in detail:
            raise ReviewError(f"gh api review failed: {detail}")
        fallback = True
        fallback_body = body
        if comments:
            fallback_body += "\n\n" + render_findings_section(
                [
                    {
                        "path": comment["path"],
                        "line": comment["line"],
                        "title": "Inline finding",
                        "comment": comment["body"],
                    }
                    for comment in comments
                ],
                "Inline findings (anchors rejected)",
            )
        payload = {
            "commit_id": head_sha,
            "event": event,
            "body": ensure_marker(fallback_body, marker),
            "comments": [],
        }
        check_body_size(payload["body"])
        check_body_preamble(payload["body"])
        payload_path.write_text(json.dumps(payload, indent=2))
        proc = run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                f"repos/{repo}/pulls/{number}/reviews",
                "--input",
                "-",
            ],
            cwd=cwd,
            stdin=json.dumps(payload),
            check=False,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            raise ReviewError(
                f"review failed with and without inline comments: {detail}. "
                f"Payload kept at {payload_path}"
            )

    try:
        review = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ReviewError(
            f"GitHub returned an unreadable review response: {proc.stdout[:200]}"
        ) from exc
    result = {
        "posted": True,
        "own_pr": False,
        "event": event,
        "url": review.get("html_url"),
        "fallback": fallback,
        "inline": 0 if fallback else len(comments),
        "body_only": len(dropped) + (len(comments) if fallback else 0),
        **{key: counts[key] for key in SEVERITIES},
    }
    (run_dir / "post-result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code_review.py",
        description="Anchors and posting for the /rs:code-review command.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    anchors = subparsers.add_parser("anchors")
    anchors.add_argument("--diff", required=True)
    anchors.add_argument("--out", required=True)
    anchors.set_defaults(func=cmd_anchors)

    post = subparsers.add_parser("post")
    post.add_argument("--run-dir", required=True)
    post.add_argument("--pr", required=True)
    post.add_argument("--head-sha", required=True)
    post.add_argument("--findings", required=True)
    post.add_argument("--body", required=True)
    post.add_argument("--dry-run", action="store_true")
    post.add_argument("--force", action="store_true")
    post.set_defaults(func=cmd_post)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ReviewError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
