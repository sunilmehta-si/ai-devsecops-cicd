# Security policy

Report vulnerabilities privately through GitHub's "Report a vulnerability" button on the Security tab.
Please do not open public issues for security problems. This is a reference project, so there is no
SLA, but reports are read and acknowledged.

## Handling credentials in this repository

- No real credentials are ever committed. `.gitignore` blocks env files, keys, kubeconfigs and state files.
- `scripts/check_secrets.py` runs as a pre-commit hook (`make hooks`), in CI over the full history, and
  never prints the offending line, so a CI log cannot become a second leak.
- Workflows use short-lived OIDC identities and the per-run `GITHUB_TOKEN`; there are no stored signing keys.
- If a secret is ever committed: revoke it first, then rewrite history. Deleting the file is not enough.
