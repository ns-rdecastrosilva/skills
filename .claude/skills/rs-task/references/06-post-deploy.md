# Phase 6: post-deploy validation

Stop after the PR. Do not schedule this phase automatically.

Only after the user explicitly confirms deployment and authorizes validation,
start a fresh QA worker with the earlier reports and the deployed revision.

## Checks

1. Confirm the environment and account again. Reuse an authenticated session
   when available and respect the host's login attempt limit.
2. Confirm that the deployed build contains the tested change. Check the merge
   commit, image tag, release record, or other release evidence. A version
   mismatch blocks the verdict; it does not prove a code failure.
3. Use a real browser on the deployed environment to repeat the original steps
   and every acceptance criterion affected by the release. Capture fresh UI,
   network, console, and persistence evidence.
4. Check adjacent behavior and permissions the release could affect. Restrict
   mutations to a test environment and clean them up.
5. Append a deployed PASS, FAIL, or BLOCKED section to
   `06-post-deploy-validation.md`. Include the deployed version, observations,
   screenshots, cleanup, login attempts, and residual risk.

A post-deploy failure cannot be converted into a pass by successful earlier
checks. Report the failing steps, preserve the evidence, and ask before starting
another correction cycle.
