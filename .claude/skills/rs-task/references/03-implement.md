# Phase 3: implement

Apply the approved plan in the target repository.

## Rules

- Follow the repository's instructions, patterns, and package scripts.
- Keep the diff scoped to the plan.
- Add a regression test that exercises the reported state and inputs, not only
  a convenient new fixture.
- When practical, watch the regression test fail on the unpatched code before
  adding the fix.
- Run the focused tests and guards needed for the implementation.
- Do not mark plan tasks complete because code was written. Completion requires
  the matching evidence in phase 4.
- Leave changes uncommitted for the PR phase.
- Do not commit OpenSpec artifacts or run evidence.

## Scope check

Before handing off to verification, inspect the diff and confirm:

- every changed file has a reason in the plan;
- no unrelated refactor, formatting, or dependency change slipped in;
- generated files, vendored code, and build output were not edited by hand;
- the test added would fail without the fix.
