---
name: rs-text
description: Improve a block of English text in place and return only the polished text inside one plaintext code block. Use when the user asks to fix, improve, rewrite, proofread, or polish a message, usually for Slack. Never adds commentary, alternatives, Markdown, em dashes, or Slack link tags.
---

# RS Text

This skill merges the useful parts of `us-business-english`, `slack-messaging`, and `grammar-check`. When they conflict, this skill wins. In particular, ignore Slack mrkdwn guidance here: the output is plain text.

## Contract

Input: one block of text, usually English, usually meant for Slack.

Output: exactly one fenced code block tagged `plaintext`, containing the improved text. Nothing before the block. Nothing after the block.

Do not answer the text. Do not summarize it. Do not explain the changes. Do not list suggestions. Do not offer alternatives. Do not ask questions. One version only.

## Silent passes

Run these internally. Never print findings.

1. Grammar: spelling, punctuation, subject-verb agreement, tense, articles, prepositions, pronoun reference, modifier placement.
2. Clarity: cut filler, redundancy, corporate buzzwords, passive voice, and vague wording. Prefer active voice, concrete verbs, natural contractions, and specific wording.
3. Flow: short paragraphs, one idea per paragraph, plain transitions, no run-on sentences.
4. Register: US business English. Direct, professional, friendly. Slack is casual: no greeting, no sign-off, no "Dear".
5. Scrub: enforce every ban below.

## Preserve

- Meaning, facts, numbers, names, product terms, links, and intent.
- The author's voice and level of formality. Improve the text, do not replace the person.
- The input language. English stays English. Do not translate.
- Paragraph and line-break structure. Do not merge or split paragraphs unless the input is an unreadable wall of text.
- Length: same or shorter. Never pad.

## Never

- Never use an em dash (U+2014) or an en dash (U+2013). Use a comma, a period, a colon, parentheses, or "to" for ranges.
- Never use bold, italics, headers, blockquotes, backticks, emojis, or any Markdown.
- Never use Slack mrkdwn. No asterisks for emphasis.
- Never use angle-bracket link syntax. Keep the bare URL. If the input has a labeled Slack link, output the label, then the bare URL in parentheses. Exception: keep Slack user and channel mentions exactly as written, because they must stay functional.
- Never use curly quotes or curly apostrophes. Use straight ASCII quotes.
- Never output more than one version, a before/after, a list of suggestions, or a note about what changed.
- Never add sentences, caveats, calls to action, greetings, or sign-offs that were not in the input.
- Never ask a clarifying question. Pick the most likely reading and continue.
- Never start with "Here is" or end with an offer to adjust.

## If the input already works

Return it unchanged, still inside the plaintext block. Do not invent edits to look useful.

## Output shape

```plaintext
<improved text>
```

Exactly that. The code fence is the only formatting allowed.

## Example

Input:

```text
hey team, quick update: we have leveraged the new pipeline and it is live now. reach out if you have bandwidth to circle back on the remaining deliverables
```

Output:

```plaintext
Hey team, quick update: the new pipeline is live. Let me know if you have time to follow up on the remaining work.
```

## Final gate

Before sending, verify:

1. The reply is exactly one code block tagged `plaintext`.
2. Nothing exists outside the block.
3. The block contains one version of the text.
4. No U+2014, no U+2013, no `**`, no `##`, no `<http`.
5. Meaning and facts match the input.

If any check fails, fix the output and emit it again. Do not mention the check.
