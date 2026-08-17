# security-gate

A **reusable GitHub Actions security gate** — drop it into any repo with ~6 lines and get a
free, deterministic ($0/run, no LLM) layered security check plus one consolidated report.

## Layers

| Layer | Tool | Policy |
|---|---|---|
| Access-control / IDOR + regression tests | your repo's `pytest` suite | blocking |
| SAST (static analysis) | Semgrep | blocking |
| Secrets scan | gitleaks | blocking |
| Dependency CVEs | pip-audit + npm audit | advisory |
| Consolidated report | Job Summary (one page) | — |

The gate runs in the **caller's** context, so your own tests (e.g. an access-control matrix that
asserts a low-privilege role cannot reach another tenant's data) run alongside the generic scanners.
That app-specific authorization test is the highest-value part — automated scanners can't check
*your* access rules, so each app supplies its own `pytest` suite under `<python-path>/tests`.

## Usage

Add `.github/workflows/security.yml` to your repo:

```yaml
name: Security Gate
on: [push, pull_request, workflow_dispatch]
permissions:              # REQUIRED: a reusable workflow can't request more than the caller grants
  contents: read
  actions: read
jobs:
  gate:
    uses: Nilufer-Shah/security-gate/.github/workflows/gate.yml@main
    with:
      python-path: backend    # dir with requirements.txt + tests/  ("" to skip Python)
      node-path: frontend     # dir with package.json               ("" to skip Node)
```

### Inputs

| Input | Default | Meaning |
|---|---|---|
| `python-path` | `''` | Dir with `requirements.txt` and `tests/`. Empty skips Python. |
| `node-path` | `''` | Dir with `package.json`. Empty skips Node. |
| `python-version` | `3.12` | |
| `node-version` | `20` | |
| `run-tests` | `true` | Run `pytest` in `<python-path>/tests`. |
| `semgrep-config` | `p/python p/javascript p/typescript p/react p/security-audit` | Semgrep registry configs. |

## Notes

- **Private repos:** this repo's Actions access is set to "accessible from repositories owned by
  the user," so your other private repos can call it.
- **Not a proof of 100% security.** It's a strong, repeatable confidence bar. Pair with periodic
  deep passes (e.g. an AI pentester / DAST) for creative coverage.
- **Consolidated report** renders on each run's **Summary** page (GitHub's native Security tab
  needs paid Advanced Security on private repos; this is the free equivalent).
