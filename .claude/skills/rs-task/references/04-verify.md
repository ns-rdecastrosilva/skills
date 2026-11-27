# Phase 4: verify

Assign a fresh, independent QA worker. Never reuse the implementation worker as
QA. Give it the rationale, the plan, the evidence paths, and the environment
context. Do not paste the diff or full logs into its prompt. It reads the code
and the plan in its own context.

When the host has no subagent tool, run the checks inline and mark the run as
degraded.

## Required checks

1. Trace each acceptance criterion to the implementation and an observed result.
2. Run focused tests, relevant integration tests, type checks, lint, formatting,
   and build checks required by the repository. Capture the command, working
   directory, exit status, and a short output summary.
3. When practical, prove the regression test fails against the unpatched
   revision in a disposable worktree. Otherwise record why the negative control
   was not run.
4. For a UI change, start the patched application or service and use a real
   browser to repeat the original steps against the confirmed backend. Check
   visible behavior, network responses, console errors, and persisted state.
5. Test the main success path and the failure or boundary cases in the plan.
   Check adjacent behavior the diff could affect.
6. For a migrated flow, compare the required behavior and contract with the
   legacy implementation. Do not claim parity when only the new stack was
   inspected.
7. Remove fixtures, empty temporary state, stop extra services, and close
   browser tabs used by the run.
8. Record the login attempt count and every check that remains unverified.

A green build does not prove the bug is fixed. A local browser pass proves only
the tested local build against the stated backend. It does not prove deployed
behavior.

## Write `04-verification.md`

```text
# Verification report

## Verdict
PASS, FAIL, or BLOCKED, followed by the exact scope of that verdict.

## Requirements traced
One row per acceptance criterion, with its evidence and result.

## Subject under test
Base revision, local diff summary, services, ports, environment URL, deployed
versions, flags, and test data identifiers. Include no credentials.

## Method
Who ran each check, which tools and browser were used, and which prior steps
supplied the baseline.

## Automated checks
Each command, working directory, exit status, and relevant output summary.
Include the regression test and its negative control when run.

## Browser checks
For each scenario, the Given/When/Then setup, numbered actions, expected result,
observed result, assertions, and screenshot paths. Include relevant sanitized
network and console evidence.

## Regression and compatibility checks
Adjacent flows checked, legacy comparison when applicable, and any disabled or
unavailable checks.

## Cleanup and account safety
Fixtures removed, processes and tabs closed, pending state checked, and login
attempts used.

## Limitations and residual risk
Unverified behavior, environment differences, skipped negative controls, and
remaining uncertainty.

## Conclusion
Why the evidence supports or rejects the fix. State explicitly that deployed
validation is still pending.
```

A FAIL or BLOCKED verdict stops the PR. Return to phase 2 when the plan or
diagnosis changed, or phase 3 for a direct correction, then repeat phase 4.
Append later rounds instead of hiding failed evidence.
