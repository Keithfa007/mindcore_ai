#!/usr/bin/env python3
"""Fix BigQuery scope: readonly can list tables but cannot run queries."""

filepath = "scripts/bigquery_report.py"

with open(filepath, "r") as f:
    content = f.read()

old = 'scopes=["https://www.googleapis.com/auth/bigquery.readonly"]'
new = 'scopes=["https://www.googleapis.com/auth/bigquery"]'

assert old in content, "Target scope string not found"
content = content.replace(old, new)

with open(filepath, "w") as f:
    f.write(content)

print("Scope updated: bigquery.readonly -> bigquery")
assert new in content
print("Verified!")
