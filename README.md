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

## Post-hardening checklist (re-test after security changes)

This gate is **read-only** — it analyzes your code and never modifies the app, so it can't cause a
runtime regression on its own. The risk lives in the *fixes you apply after it flags something*: a
dependency bump or a hardening patch can expose a latent bug or break a runtime path the unit tests
don't cover. Two failure modes we've actually hit — check both before you ship a security change:

- **After a dependency/framework bump the SCA flagged** → smoke-test the app end-to-end, not just
  unit tests. Major bumps surface latent app bugs. *(Real case: a patch-level Next.js bump that
  fixed a CVE also activated React 18 Strict Mode's double-invoked state updater, which exposed an
  **impure `setState` updater** — a mutable closure flag — that silently dropped a rendered message.
  State updaters must be pure: derive the next state only from the `prev` argument, no external
  mutable flags.)*

- **After adding response middleware (security headers, CSP, etc.)** → verify any **streaming
  endpoints (SSE / chunked)** still stream. Inject headers with **pure ASGI middleware**, never
  Starlette's `BaseHTTPMiddleware` / `@app.middleware("http")` — those buffer the full response body
  and break SSE. (Wrap `send` and set headers on the `http.response.start` message instead.)

General rule: every security fix gets one manual pass through the app's happy path — especially
login, streaming/real-time, and file upload — before merge. Unit-test green ≠ app works.

## Notes

- **Private repos:** this repo's Actions access is set to "accessible from repositories owned by
  the user," so your other private repos can call it.
- **Not a proof of 100% security.** It's a strong, repeatable confidence bar. Pair with periodic
  deep passes (e.g. an AI pentester / DAST) for creative coverage.
- **Consolidated report** renders on each run's **Summary** page (GitHub's native Security tab
  needs paid Advanced Security on private repos; this is the free equivalent).
