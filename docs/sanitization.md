# Sanitization rules

This repository is public. It must not contain anything that identifies a
private environment, customer, employer, repository, or ticket prefix.

## Never include

- Company or product names from a private environment.
- Internal hostnames or domains.
- Private repository names or URLs.
- Internal tracker URLs or project keys.
- Real environment IDs, account names, email addresses, or credentials.
- Screenshots, logs, or API responses from a private environment.
- Absolute paths from a developer machine.

## Use these placeholders

| Private value | Public placeholder |
|---|---|
| Tracker key | `ABC-123` |
| Tracker URL | `https://tracker.example.com/browse/ABC-123` |
| GitHub issue | `#123` or `owner/repo#123` |
| GitHub PR | `https://github.com/owner/repo/pull/1234` |
| Repository | `owner/frontend`, `owner/backend`, `owner/legacy-app` |
| Environment | `https://app.example.com` |
| Account | `user@example.com` |
| Cluster context | `example-context` |

## CI gate

`tests/denylist.sh` fails the build when a forbidden term appears. Run it before
every commit:

```bash
bash tests/denylist.sh
```

The gate is intentionally blunt. When a false positive is unavoidable, rewrite
the text instead of adding an exception.
