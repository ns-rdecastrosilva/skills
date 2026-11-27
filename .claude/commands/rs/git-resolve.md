# git-resolve

Merge with the PR target branch (or master/main if no open PR), resolve the
conflicts, commit and push it.

## Usage

```
/rs:git-resolve
```

## What it does

Merges the correct base branch into the current branch, resolves any conflicts,
commits the merge, and pushes. The base branch is resolved in this order:

1. **Open PR target branch** — if the current branch has an open PR, use the
   PR's base branch (e.g. a stacked PR targeting a feature branch).
2. **Repo default branch** — `master` or `main`, auto-detected, when no open
   PR exists for the current branch.

## Steps

1. Detect the current branch: `git rev-parse --abbrev-ref HEAD`.
2. Check for an open PR on the current branch:
   `gh pr view --json baseRefName --jq '.baseRefName'` (or
   `gh pr list --head <current-branch> --state open --json baseRefName`).
   - If a PR exists, use its `baseRefName` as the base branch.
   - If no PR exists (or `gh` fails/errors), fall back to the default branch:
     check `git symbolic-ref refs/remotes/origin/HEAD`; fall back to `master`
     if it exists, else `main`.
3. Announce which base branch will be merged and why (PR target vs default).
4. `git fetch origin <base-branch>`.
5. `git merge origin/<base-branch>` into the current branch.
6. If conflicts occur:
   - Inspect each conflicted file (`git status`, conflict markers).
   - Resolve them, favoring correctness — keep both sides' intent where possible.
   - `git add` each resolved file.
   - NEVER resolve by blindly taking "ours" or "theirs" without reading the code.
7. Commit the merge (default merge message is fine).
8. `git push` the current branch to origin.
9. If the push is rejected (non-fast-forward), STOP and ask the user — do not
   force-push.

Run `git status` at the end and report the final state: merged branch, conflicts
resolved, commit hash, push result.
