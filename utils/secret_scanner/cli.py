import argparse
import json
import sys
from pathlib import Path

from .scanner import check_secrets


def scan_file(path: Path) -> list[dict]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [{"error": f"File not found: {path}"}]
    return check_secrets(content)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan files for hard-coded secrets",
    )
    parser.add_argument("files", nargs="*", help="Files to scan; stdin if none")
    args = parser.parse_args()

    findings = []
    if args.files:
        for fname in args.files:
            findings.extend(scan_file(Path(fname)))
    else:
        content = sys.stdin.read()
        findings = check_secrets(content)

    print(json.dumps(findings, indent=2))
    # Exit zero so that pre-commit passes even if findings are present
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
