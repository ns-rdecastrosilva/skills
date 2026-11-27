# Authoring rules

## Command or skill

Use a skill when the model must be able to start the workflow in the middle of
a conversation. Use a command when a person starts the workflow explicitly and
the workflow writes to a database, cluster, repository, or external service.

Most workflows use both:

```text
.claude/skills/rs-<name>/SKILL.md    # source of truth
.claude/commands/rs/<name>.md        # three-line stub that loads the skill
```

The stub must not repeat the workflow. It only loads the skill and passes the
arguments:

```markdown
---
description: One line that names the trigger.
---

Load the `rs-<name>` skill and follow it. Arguments: $ARGUMENTS
```

## Skill frontmatter

The description is the trigger. It must name the situations where the model
should load the skill, not only what the skill does.

```yaml
---
name: rs-example
description: Do X for Y. Use when the user asks to ..., ..., or when a task
  needs ..., including mid-task.
---
```

Write the description in English. Keep it under 500 characters.

## Skill layout

A skill owns one job. Put long procedures in `references/` and link them from
`SKILL.md`. The host loads `SKILL.md` first and the references only when the
model asks for them.

```text
.claude/skills/rs-<name>/
  SKILL.md
  references/
    step-one.md
    step-two.md
```

## Naming

- Every public skill and command starts with `rs`.
- Skill directories use `rs-<name>`.
- Command files live under `commands/rs/` so hosts expose `/rs:<name>` or
  `/rs-<name>`.
- A private pack may add its own `rs-*` names, but it must not redefine a public
  one. Name collisions are an error.

## Evidence over claims

Any workflow that can change code or infrastructure writes evidence to a file
outside the target repository. The final message reports the file paths and a
verdict, not a summary that replaces the evidence.

## Safety

- Read-only skills may be model-invoked.
- Mutating commands stay user-invoked, or require an explicit confirmation in
  the skill body.
- Never put credentials, tokens, cookies, or personal data in prompts, files,
  commits, or PR text.
