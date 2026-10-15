"""
Check that every REST endpoint a document lists exists in the running app.

    python check_report_endpoints.py ../docs/broker_demand_analysis.md
    python check_report_endpoints.py "C:/Users/.../alip_farmer_broker_master_report2.md"

Lines such as "GET  /market/demand/analysis/..." are matched as prefixes (the
master report truncates long paths); path parameters match any name.
Exit code 1 when anything listed is missing.
"""
import re
import sys
from pathlib import Path

ENDPOINT = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s`|),]+)")


def normalise(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path.split("?")[0]).rstrip("/")


def documented_endpoints(text: str) -> list[tuple[str, str, bool]]:
    found = []
    for method, raw in ENDPOINT.findall(text):
        truncated = raw.endswith("..") or raw.endswith("...")
        found.append((method, normalise(raw.rstrip(".")), truncated))
    return sorted(set(found))


def api_endpoints() -> set[tuple[str, str]]:
    from main import app

    return {
        (method.upper(), normalise(path))
        for path, ops in app.openapi()["paths"].items()
        for method in ops
    }


def check(doc_path: str) -> int:
    documented = documented_endpoints(Path(doc_path).read_text(encoding="utf-8"))
    api = api_endpoints()
    missing = 0
    print(f"{len(documented)} endpoint(s) listed in {Path(doc_path).name}\n")
    for method, path, truncated in documented:
        if truncated:
            ok = any(m == method and p.startswith(path) for m, p in api)
        else:
            ok = (method, path) in api
        missing += not ok
        print(f"  {'ok     ' if ok else 'MISSING'}  {method:<6} {path}{'...' if truncated else ''}")
    print(f"\n{missing} missing")
    return 1 if missing else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(check(sys.argv[1]))
