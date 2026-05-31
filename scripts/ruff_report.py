"""Print ruff JSON diagnostics grouped by rule."""

import json
import sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else ".ruff-errors.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)
rules = Counter(d["code"] for d in data)
print("total", len(data))
for code, n in rules.most_common(30):
    print(f"  {code}: {n}")
code_filter = sys.argv[2] if len(sys.argv) > 2 else None
if code_filter:
    print(f"\n{code_filter}:")
    for d in sorted([x for x in data if x["code"] == code_filter], key=lambda x: (x["filename"], x["location"]["row"])):
        loc = d["location"]["row"]
        print(f"  {d['filename']}:{loc} {d['message']}")
