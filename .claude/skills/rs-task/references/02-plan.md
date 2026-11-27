# Phase 2: plan

Use OpenSpec when the host provides it. Invoke `/openspec-propose` with the task,
the rationale path, and the triage path. When a matching open change exists,
inspect it and update that change instead of creating a duplicate.

When OpenSpec is unavailable, write a plan file in the run directory.

## Plan contents

- Root cause or feature goal.
- Smallest viable change.
- Affected repositories, APIs, components, migrations, and data.
- Acceptance criteria as Given/When/Then scenarios.
- Regression tests and browser scenarios that verify the result.
- Compatibility limits and explicit non-goals.
- Cleanup and the separate post-deploy validation gate.

Do not approve a plan that depends only on a passing build. Each acceptance
criterion needs a planned verification method.

## Approval

Present the plan to the user when the change is broad, risky, or irreversible.
Do not start implementation while a blocking question is unresolved.
