# rs skills

Portable `rs-*` skills and commands for Claude Code and OpenCode.

Every command and skill in this repository uses the `rs` prefix. The prefix is
part of the contract: a private pack can depend on a public `rs-*` skill
without guessing its name.

## What is here

| Item | Kind | What it does |
|---|---|---|
| `rs-text` | skill | Rewrites a block of English text and returns only the polished text. |
| `rs-code-review` | skill | Reviews a GitHub PR with parallel lanes and posts one synthesized review. |
| `rs-task` | skill | Runs a task from context to a verified PR with evidence files and independent QA. |
| `rs-check-ticket-done` | skill | Read-only verification of a ticket, issue, PR, and running app. |
| `rs-git-resolve` | command | Merges the PR base branch and resolves conflicts. |
| `rs-update-kubeconfig` | command | Replaces `~/.kube/config` with a timestamped backup. |

`rs-task` and `rs-check-ticket-done` share phase references. The verification
skill composes phases 0, 1, and 6 instead of duplicating them.

## Layout

```text
.claude/
  commands/rs/        # user-invoked slash commands
  skills/rs-*/        # model-invoked skills
scripts/              # helper scripts called by commands and skills
docs/                 # authoring and sanitization rules
tests/                # repository checks
```

## Install

Claude Code:

```bash
mkdir -p ~/.claude/commands/rs ~/.rs-skills/scripts
cp -R .claude/skills/rs-* ~/.claude/skills/
cp .claude/commands/rs/*.md ~/.claude/commands/rs/
cp scripts/*.py ~/.rs-skills/scripts/
```

OpenCode:

```bash
mkdir -p ~/.config/opencode/commands ~/.rs-skills/scripts
cp -R .claude/skills/rs-* ~/.config/opencode/skills/
for file in .claude/commands/rs/*.md; do
  cp "$file" "$HOME/.config/opencode/commands/rs-$(basename "$file")"
done
cp scripts/*.py ~/.rs-skills/scripts/
```

Skills call helper scripts through `$HOME/.rs-skills/scripts`. Set
`RS_SCRIPTS` to use a different directory.

Restart the host after installing or updating skills. A skill is available to
the model in the middle of a conversation; a command is only available to the
user at the start of a message.

## Requirements

- Python 3.9 or newer for `rs-code-review`.
- `gh` authenticated for PR and issue operations.
- `git` for `rs-git-resolve`.
- A browser automation tool for the live phases of `rs-task` and
  `rs-check-ticket-done`.

The skills do not require Node.js. A host installer may.

## Tracker inputs

The public skills accept a tracker key, a GitHub issue, or plain text. Examples
use `ABC-123`, `#123`, `owner/repo#123`, and `example.com`. A private policy can
map those inputs to an internal tracker without changing the public skill.

## Sanitization

This repository must not contain internal hostnames, customer names, private
repository names, or tracker prefixes from a private environment. See
`docs/sanitization.md`. The CI gate in `tests/denylist.sh` enforces it.

## License

MIT. See `LICENSE`.
