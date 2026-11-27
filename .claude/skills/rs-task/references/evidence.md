# Evidence files

Create the run directory outside every target repository:

```text
~/.rs-skills/task-runs/<TASK-ID>/<RUN-ID>/
```

Use a tracker key or short slug for `<TASK-ID>` and a UTC timestamp for
`<RUN-ID>`. When the host provides a shared artifact directory, use it and
record the path in the ledger.

## Files

| File | Owner | Content |
|---|---|---|
| `delegation-ledger.md` | orchestrator | Worker IDs, scopes, models, states, receipt paths |
| `00-rationale.md` | context worker | Problem, reproduction, expected result, acceptance criteria |
| `01-triage.md` | synthesis worker | Combined findings and root cause |
| `01-static.md`, `01-live.md`, `01-repository.md`, `01-git.md`, `01-duplicates.md` | lane workers | Raw lane evidence |
| `04-verification.md` | QA worker | Pre-PR verification report |
| `05-pr.md` | PR worker | PR identity, CI, review, repair state |
| `06-post-deploy-validation.md` | QA worker | Deployed validation, only when authorized |

## Redaction

- Never write passwords, tokens, cookies, session IDs, or personal data.
- Redact sensitive response fields from network logs.
- Crop or mask screenshots that show secrets or unrelated environment data.
- Keep commands in reports safe to read.
- Do not commit the run directory or OpenSpec artifacts.

## Ledger fields

```text
| Worker | Scope | Model | State | Receipt |
|---|---|---|---|---|
| context-1 | ticket ABC-123, acceptance criteria | host default | done | 00-rationale.md |
```
