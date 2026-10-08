#!/usr/bin/env python3
"""Semantic Linter for CrowdSight.

Scans Python code, TypeScript/React frontend code, technical documentation,
and export templates to prevent semantic violations:
- No capacity / attendance / 'sức chứa' / 'độ đông' terminology.
- No 'mức an toàn' or 'nguy hiểm' associated with count metrics.
- No metric density (people/m²) outside explicit 'unavailable' / null contexts.
- No confidence scores presented with percentage (%) or called confidence level.
- No heat maps referred to as geographic maps.

Exits with code 0 if clean, code 1 if violations are detected.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


@dataclass
class Violation:
    file_path: Path
    line_number: int
    matched_term: str
    line_content: str
    description: str


def run_semantic_lint(root_dir: Path) -> int:
    config_file = root_dir / "scripts" / "semantic_lint_config.json"
    if not config_file.is_file():
        print(f"Error: Configuration file not found at {config_file}", file=sys.stderr)
        return 1

    with open(config_file, encoding="utf-8") as f:
        config = json.load(f)

    file_extensions = tuple(config.get("file_extensions", []))
    ignore_dirs = set(config.get("ignore_dirs", []))
    ignore_files = {root_dir / p for p in config.get("ignore_files", [])}
    ignore_globs = config.get("ignore_globs", [])

    forbidden_terms = config.get("forbidden_terms", [])
    compiled_patterns = [
        (p["name"], re.compile(p["pattern"], re.IGNORECASE), p["description"])
        for p in config.get("forbidden_patterns", [])
    ]

    violations: list[Violation] = []
    scanned_files_count = 0

    for path in root_dir.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignore_dirs for part in path.parts):
            continue
        rel_str = str(path.relative_to(root_dir)).replace("\\", "/")
        if any(path.match(g) or (g.endswith("/**") and rel_str.startswith(g[:-3])) for g in ignore_globs):
            continue
        if path.suffix.lower() not in file_extensions:
            continue
        if path.resolve() in {f.resolve() for f in ignore_files}:
            continue

        scanned_files_count += 1
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            line_lower = line.lower()

            # 1. Check forbidden terms
            for item in forbidden_terms:
                term = item["term"]
                term_match = term if item.get("case_sensitive") else term.lower()
                target_text = line if item.get("case_sensitive") else line_lower

                if term_match in target_text:
                    # Check if covered by an allowed disclaimer phrase
                    allowed = False
                    for phrase in item.get("allowed_phrases", []):
                        if phrase.lower() in line_lower:
                            allowed = True
                            break

                    if not allowed:
                        violations.append(
                            Violation(
                                file_path=path.relative_to(root_dir),
                                line_number=line_no,
                                matched_term=term,
                                line_content=line.strip(),
                                description=f"Forbidden term '{term}' without approved disclaimer context.",
                            )
                        )

            # 2. Check forbidden regex patterns
            for name, pattern, desc in compiled_patterns:
                if pattern.search(line):
                    violations.append(
                        Violation(
                            file_path=path.relative_to(root_dir),
                            line_number=line_no,
                            matched_term=name,
                            line_content=line.strip(),
                            description=desc,
                        )
                    )

    # Print Report
    print("=== CrowdSight Semantic Linter ===")
    print(f"Files scanned: {scanned_files_count}")

    if not violations:
        print("Result: [PASS] All scanned files comply with semantic invariants.\n")
        return 0

    print(f"Result: [FAIL] Found {len(violations)} semantic violation(s):\n")
    for v in violations:
        print(f"  --> {v.file_path}:{v.line_number}")
        print(f"      Matched: {v.matched_term}")
        print(f"      Line:    {v.line_content}")
        print(f"      Reason:  {v.description}\n")

    return 1


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    sys.exit(run_semantic_lint(repo_root))
