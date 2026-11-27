# Orchestration

## Main agent

The main agent is the orchestrator. It:

- asks the user only for decisions that block the run;
- dispatches each phase and lane to a worker;
- keeps `delegation-ledger.md`;
- reads compact receipts, not full transcripts;
- reports outcomes and file paths.

The orchestrator does not investigate source code, review large diffs, or run
repository checks in its own context when a worker can do it.

## Worker prompts

Every worker prompt contains:

- the task or phase goal;
- the rationale path and triage path when they exist;
- the repository paths in scope;
- the evidence file it must write;
- the rule that it must not change product code outside its phase;
- the receipt format: status, one-line summary, file path, blockers.

Do not paste credentials into a worker prompt.

## Receipts

A receipt is short:

```text
Status: done | blocked | failed
Summary: one line
Evidence: <path>
Blockers: none, or the exact missing input
```

The orchestrator reads the receipt and opens the evidence file only when it
needs detail.

## Degraded mode

When the host has no subagent tool:

- run the phases inline;
- mark the run as degraded in `delegation-ledger.md`;
- do not claim that independent QA ran;
- keep the same evidence files.

## Model selection

Use the host default model for every worker unless the user explicitly selects
a model for this run. Never guess a model name.
