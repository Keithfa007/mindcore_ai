#!/usr/bin/env python3
"""One-shot patch: bigquery_report.py v1.0 -> v1.1
Surfaces query errors in Telegram message instead of silently swallowing them.
Adds diagnostic test query and error summary section.
"""

filepath = "scripts/bigquery_report.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Update version
content = content.replace(
    "BigQuery Analytics Report v1.0",
    "BigQuery Analytics Report v1.1"
)

# 2. Replace run_query to collect errors
old_run_query = '''def run_query(client, sql):
    """Run a BigQuery SQL query and return rows as list of dicts."""
    try:
        result = client.query(sql).result()
        return [dict(row) for row in result]
    except Exception as e:
        print(f"   Query error: {e}")
        return []'''

new_run_query = '''def run_query(client, sql, errors=None):
    """Run a BigQuery SQL query and return rows as list of dicts."""
    try:
        result = client.query(sql).result()
        rows = [dict(row) for row in result]
        print(f"   Query returned {len(rows)} rows")
        return rows
    except Exception as e:
        msg = str(e)[:200]
        print(f"   Query error: {msg}")
        if errors is not None:
            errors.append(msg)
        return []'''

assert old_run_query in content, "run_query function not found!"
content = content.replace(old_run_query, new_run_query)

# 3. Add errors list and diagnostic test after the header lines
old_header = '''    print(f"   Querying {len(recent)} days: {date_range}")

    lines = []
    lines.append("\\U0001f4ca *BigQuery Analytics Report*")
    lines.append(f"_{date_range} ({len(recent)} days)_")
    lines.append("")

    # 1. Overview
    print("   [1/5] Overview...")
    rows = run_query(client, f"""'''

new_header = '''    print(f"   Querying {len(recent)} days: {date_range}")

    errors = []
    lines = []
    lines.append("\\U0001f4ca *BigQuery Analytics Report*")
    lines.append(f"_{date_range} ({len(recent)} days)_")
    lines.append("")

    # 0. Diagnostic: test basic table access
    print("   [0/5] Diagnostic test...")
    test_table = f"`{PROJECT}.{DATASET}.events_{recent[-1]}`"
    diag = run_query(client, f"SELECT COUNT(*) as cnt FROM {test_table}", errors)
    if diag:
        lines.append(f"_Diagnostic: {diag[0].get('cnt', 0)} events in latest table_")
        lines.append("")
    elif errors:
        lines.append(f"_Diagnostic FAILED: {errors[-1]}_")
        lines.append("")

    # 1. Overview
    print("   [1/5] Overview...")
    rows = run_query(client, f"""'''

assert old_header in content, "Header block not found!"
content = content.replace(old_header, new_header)

# 4. Add errors param to each run_query call (5 queries)
# Query 1 - Overview
content = content.replace(
    '''    """)
    if rows:
        r = rows[0]
        lines.append("\\U0001f310 *Overview:*")''',
    '''    """, errors)
    if rows:
        r = rows[0]
        lines.append("\\U0001f310 *Overview:*")'''
)

# Query 2 - Top pages
content = content.replace(
    '''        LIMIT 8
    """)
    if rows:
        lines.append("\\U0001f4c4 *Top Pages:*")''',
    '''        LIMIT 8
    """, errors)
    if rows:
        lines.append("\\U0001f4c4 *Top Pages:*")'''
)

# Query 3 - Traffic sources
content = content.replace(
    '''        LIMIT 8
    """)
    if rows:
        lines.append("\\U0001f517 *Traffic Sources:*")''',
    '''        LIMIT 8
    """, errors)
    if rows:
        lines.append("\\U0001f517 *Traffic Sources:*")'''
)

# Query 4 - Countries
content = content.replace(
    '''        LIMIT 8
    """)
    if rows:
        lines.append("\\U0001f30d *Countries:*")''',
    '''        LIMIT 8
    """, errors)
    if rows:
        lines.append("\\U0001f30d *Countries:*")'''
)

# Query 5 - Devices
content = content.replace(
    '''        ORDER BY users DESC
    """)
    if rows:
        lines.append("\\U0001f4f1 *Devices:*")''',
    '''        ORDER BY users DESC
    """, errors)
    if rows:
        lines.append("\\U0001f4f1 *Devices:*")'''
)

# 5. Add error summary before return
old_return = '    return "\\n".join(lines)'
new_return = '''    # Error summary
    if errors:
        lines.append("\\u26a0\\ufe0f *Query Errors:*")
        for i, err in enumerate(errors[:5], 1):
            lines.append(f"  {i}. {err[:150]}")
        lines.append("")

    return "\\n".join(lines)'''

assert old_return in content, "return statement not found!"
content = content.replace(old_return, new_return, 1)

with open(filepath, "w") as f:
    f.write(content)

print("Patch applied successfully!")

# Verify
with open(filepath, "r") as f:
    patched = f.read()

assert "v1.1" in patched, "Version not updated"
assert "errors = []" in patched, "Error tracking not added"
assert "Diagnostic" in patched, "Diagnostic test not added"
assert "Query Errors" in patched, "Error summary not added"
assert "errors)" in patched, "Errors param not passed to queries"
print("All assertions passed!")
