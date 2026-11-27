# Phase 1: parallel triage

Run the lanes in parallel when the host provides subagents. Triage is read-only.
No lane changes product code.

Each lane writes one file under the run directory and returns a compact receipt.
The orchestrator reads the receipt and the file path, not the whole transcript.

## Static analysis

Write `01-static.md`.

Trace the affected flow through source, tests, configuration, and generated
contracts. Inspect validation, error handling, data transformations, and side
effects. Cite files and lines. Separate evidence from inference. Name the
existing tests that should catch the issue.

## Live analysis

Write `01-live.md` and save browser evidence beside it.

Use a real browser through the host browser tool or a browser automation CLI.
Reproduce the reported steps against the confirmed environment before changing
code. Record visible behavior, request methods and URLs, response status,
console errors, and screenshots with sensitive values redacted.

When a legacy and a modern implementation both exist, compare them against the
same backend. Different environments or versions do not establish a valid
comparison.

Use unique fixtures and clean up every mutation. If login, browser startup,
routing, flags, or environment access blocks the lane, mark it BLOCKED. Do not
replace a missing browser result with static inspection.

## Repository specialist

Write `01-repository.md`.

Detect the repository type from its instructions, manifests, routes, and tests.
Assign a worker with the matching specialty. Use the closest available
equivalent when the named specialist is not installed.

| Signals | Focus |
|---|---|
| React, Vue, Svelte, TypeScript, Vite | Components, data fetching, routing, state, i18n, tests |
| Go, Java, Python, Node service | Routes, validation, services, database, outbound calls |
| Legacy frontend or backend | Existing behavior and the contract it implies |
| Playwright, Cypress, pytest | Fixtures, page objects, assertions, isolation |
| OpenAPI, generated clients | Request and response compatibility |
| Another stack | The framework's own conventions |

The specialist explains how the task fits repository conventions. Do not force
a fix designed for one stack onto another.

## Git history

Write `01-git.md`.

Read recent history for the implicated files and symbols with `git log`,
`git log -S`, `git log -G`, `git blame`, and `git show`. Compare the last known
good release when one is available. Follow extracted or renamed code when the
current path has little history.

Run `git bisect` only when a reproducible check and clean good and bad revisions
exist. Use a disposable worktree. Never reset, discard, or rewrite user changes.

Return one verdict: recent regression, older regression, pre-existing defect,
environment or version mismatch, or inconclusive. No match is not proof that no
regression occurred.

## Duplicate search

Write `01-duplicates.md`.

Search the tracker or GitHub for distinctive summary phrases, route names,
component names, error text, and confirmed root-cause terms. Read candidate
descriptions and comments instead of deciding from titles. Check status and
linked PRs.

- A credible open duplicate: report both references and ask whether to
  consolidate or continue.
- A duplicate with a merged or deployed fix: stop new implementation, link the
  evidence, and ask whether to verify the existing fix.
- An unresolved candidate: list the differences and continue only when the
  evidence supports a separate scope.

Do not close, link, comment on, or transition tickets without user approval.

## Synthesis

Write `01-triage.md`.

Resolve contradictions with direct evidence, not majority voting. State the root
cause, affected layer, regression verdict, duplicate status, proposed scope, and
the checks needed to prove the fix. For a bug that could not be reproduced,
explain what was tried and ask before implementing a speculative fix.
