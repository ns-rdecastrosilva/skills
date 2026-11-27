---
name: rs-check-ticket-done
description: Verify that a tracker ticket or GitHub issue is actually complete by comparing its requirements, the pull request diff, and the running app. Read-only. Use when the user asks to check a ticket, verify a fix, confirm acceptance criteria, or validate a deployed change.
---

# RS Check Ticket Done

Read-only verification mode of `rs-task`. This skill does not restate the task
procedure. It composes the shared references.

## Load

1. Load the `rs-task` skill.
2. Read `references/00-context.md` from that skill.
3. Read `references/01-triage.md` from that skill.
4. Read `references/evidence.md` from that skill.
5. Read `references/04-verify.md` when the target is a local or development
   build.
6. Read `references/06-post-deploy.md` when the target is a deployed build.

## Policy hook

Read every file that matches
`~/.rs-skills/policy/*/check-ticket-done.md`. A policy file adds environment
rules: tracker mapping, environment access, legacy comparison, and repository
names. The policy wins over this skill when they conflict.

## Mode

Determine the target before starting:

| Input | Use |
|---|---|
| No flag, local or development build available | Phase 0, phase 1, and the browser procedure from `04-verify.md`. Label the result pre-deploy. |
| `--deployed` or the user says the change is deployed | Phase 0, phase 1, and `06-post-deploy.md`. |
| No runtime available | Static verification only. State that live behavior was not checked. A static-only result cannot be PASS for a UI or runtime requirement. |

## Procedure

1. Resolve the ticket, issue, or task with `00-context.md`. The input may be a
   tracker key such as `ABC-123`, a GitHub issue such as `#123` or
   `owner/repo#123`, a URL, or plain text.
2. Fetch the requirements, acceptance criteria, and comments.
3. Fetch the PR and the full diff. Read the changed code in the repository when
   the diff lacks context.
4. Run the read-only triage lanes from `01-triage.md` that apply. Skip the
   duplicate search unless the user asks for it.
5. Verify each acceptance criterion against three sources:
   - the requirement text;
   - the implementation in the diff;
   - the observed behavior in the running app.
6. Check unresolved review comments and failing checks.
7. Run the repository guards when they are cheap and read-only.
8. Clean up every fixture and browser tab.

Do not implement code, open a PR, merge, or deploy. When the target is a local
build, use only the read-only checks from `04-verify.md`.

## Verdict

End with one of:

- `PASS`: every requirement has evidence from the required sources.
- `FAIL`: a requirement is missing or the observed behavior contradicts it.
- `BLOCKED`: a required source is unavailable, such as the tracker, the PR, the
  runtime, or the account. Name the missing input.

## Report

Write `~/.rs-skills/task-runs/<TASK-ID>/check-<RUN-ID>.md`:

```text
# Ticket verification

## Verdict
PASS, FAIL, or BLOCKED, with the exact scope.

## Requirement trace
One row per acceptance criterion: requirement, code evidence, live evidence,
result.

## PR state
Number, URL, head SHA, review state, CI state.

## Live checks
Environment, build or revision, actions, expected result, observed result,
screenshot paths.

## Gaps and residual risk
Missing evidence, unavailable sources, and behavior that was not exercised.

## Cleanup
Fixtures removed, tabs closed, login attempts used.
```

If the verdict is FAIL or BLOCKED, state what is missing and where. Do not
suggest a fix unless the user asks for one.
