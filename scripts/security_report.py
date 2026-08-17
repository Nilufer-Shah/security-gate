#!/usr/bin/env python3
"""Merge every security-gate layer into one Markdown summary (to $GITHUB_STEP_SUMMARY).

Reads each layer's artifact from ./reports/<artifact>/... and job results from env
(TESTS_RESULT / SAST_RESULT / SECRETS_RESULT / SCA_RESULT). Fetches the caller's latest Strix
run if one exists. Never raises — a missing/odd artifact degrades to "n/a".
"""
import json
import os
import subprocess
from pathlib import Path

R = Path("reports")


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def emoji(r):
    return {"success": "✅", "failure": "❌", "skipped": "⚪", "cancelled": "⚪"}.get(r, "❓")


def semgrep():
    d = load(R / "semgrep-report" / "semgrep.json")
    return "n/a" if d is None else str(len(d.get("results", [])))


def gitleaks():
    p = R / "gitleaks-report" / "gitleaks.json"
    d = load(p)
    if d is None:
        return "0" if not p.exists() else "n/a"
    return str(len(d)) if isinstance(d, list) else "n/a"


def tests():
    p = R / "tests-report" / "pytest-report.xml"
    try:
        import xml.etree.ElementTree as ET

        root = ET.parse(p).getroot()
        s = root if root.tag == "testsuite" else root.find("testsuite")
        t = int(s.get("tests", 0))
        bad = int(s.get("failures", 0)) + int(s.get("errors", 0))
        return f"{t - bad}/{t} passed"
    except Exception:
        return "n/a"


def sca():
    out = []
    pa = load(R / "sca-report" / "pip-audit.json")
    if isinstance(pa, dict):
        deps = pa.get("dependencies", pa.get("vulnerabilities", []))
        n = sum(len(x.get("vulns", [])) for x in deps) if isinstance(deps, list) else 0
        out.append(f"pip: {n}")
    elif isinstance(pa, list):
        out.append(f"pip: {sum(len(x.get('vulns', [])) for x in pa)}")
    na = load(R / "sca-report" / "npm-audit.json")
    if isinstance(na, dict):
        v = na.get("metadata", {}).get("vulnerabilities", {})
        out.append(f"npm: {v.get('total', 0)} ({v.get('high', 0) + v.get('critical', 0)} high/crit)")
    return ", ".join(out) if out else "n/a"


def strix():
    try:
        o = subprocess.run(
            ["gh", "run", "list", "--repo", os.environ.get("REPO", ""),
             "--workflow", "strix-security.yml", "--limit", "1",
             "--json", "conclusion,createdAt,url"],
            capture_output=True, text=True, timeout=30,
        ).stdout
        runs = json.loads(o)
        if not runs:
            return "not configured"
        r = runs[0]
        return f"[{r.get('conclusion') or 'in progress'}]({r.get('url')}) · {(r.get('createdAt') or '')[:10]}"
    except Exception:
        return "not configured"


def main():
    tr, sr, kr, cr = (os.environ.get(k, "unknown")
                      for k in ("TESTS_RESULT", "SAST_RESULT", "SECRETS_RESULT", "SCA_RESULT"))
    ok = all(x in ("success", "skipped") for x in (tr, sr, kr))
    verdict = ("✅ **PASS** — all blocking layers clean" if ok
               else "❌ **FAIL** — a blocking layer has findings")
    rows = [
        ("Access-control / IDOR + security tests", emoji(tr), tests(), "blocking"),
        ("SAST (Semgrep)", emoji(sr), f"{semgrep()} findings", "blocking"),
        ("Secrets (gitleaks)", emoji(kr), f"{gitleaks()} leaks", "blocking"),
        ("Dependency CVEs", emoji(cr), sca(), "advisory"),
        ("AI pentest (Strix)", "🔍", strix(), "separate · paid"),
    ]
    print("## 🔒 Security Gate report\n")
    print(f"### {verdict}\n")
    print("| Layer | Status | Detail | Policy |")
    print("|---|---|---|---|")
    for n, s, d, p in rows:
        print(f"| {n} | {s} | {d} | {p} |")
    print("\n> Dependency CVEs also surface natively via **Dependabot alerts**.")
    print("> A strong confidence bar, not a proof of 100% security.")


if __name__ == "__main__":
    main()
