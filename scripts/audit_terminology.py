"""
scripts/audit_terminology.py

Audits backend and frontend source trees for potential clinical claims:
- "recommended approach"
- "recommended surgery"
- "surgical risk"
- "safe margin"
- "safe distance"
- "unsafe"
- "best approach"
- "diagnosis"
- "malignant"
- "benign"
"""

import os
import re
from pathlib import Path

TERMS = [
    "recommended approach",
    "recommended surgery",
    "surgical risk",
    "safe margin",
    "safe distance",
    "unsafe",
    "best approach",
    "diagnosis",
    "malignant",
    "benign",
]

roots = ["src", "frontend/src"]
results = {t: [] for t in TERMS}

for root in roots:
    for path in Path(root).rglob("*"):
        if path.is_file() and path.suffix in [".py", ".js", ".jsx", ".ts", ".tsx", ".json"]:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for line_no, line in enumerate(content.splitlines(), 1):
                    for t in TERMS:
                        if re.search(r"\b" + re.escape(t) + r"\b", line, re.IGNORECASE):
                            results[t].append((str(path), line_no, line.strip()))
            except Exception:
                pass

print("=== CLINICAL TERMINOLOGY AUDIT RESULTS ===")
total_matches = 0
for t, occurrences in results.items():
    print(f"\nTERM: '{t}' ({len(occurrences)} occurrences):")
    total_matches += len(occurrences)
    for p, lno, text in occurrences:
        print(f"  {p}:{lno} -> {text[:140]}")

print(f"\nTOTAL MATCHES: {total_matches}")
