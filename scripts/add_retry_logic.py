#!/usr/bin/env python3
"""One-shot: Add retry logic for Anthropic 529 errors to blog_automation.py"""
import re

with open("scripts/blog_automation.py") as f:
    content = f.read()

# Add retry helper after imports
RETRY_HELPER = '''
import time as _time
import random as _random

def _call_anthropic_with_retry(client, max_retries=5, **kwargs):
    """Wrapper for Anthropic API calls with retry on 529 overloaded errors."""
    for attempt in range(1, max_retries + 1):
        try:
            return client.messages.create(**kwargs)
        except Exception as e:
            if "529" in str(e) or "overloaded" in str(e).lower():
                wait = 30 * attempt + _random.randint(0, 30)
                print(f"   Anthropic overloaded (attempt {attempt}/{max_retries}), waiting {wait}s...")
                _time.sleep(wait)
                if attempt == max_retries:
                    raise
            else:
                raise

'''

# Insert after the existing imports (after the last import line)
import_end = content.rfind("\nimport ") 
if import_end == -1:
    import_end = content.rfind("\nfrom ")
# Find end of that line
next_newline = content.index("\n", import_end + 1)
# Find end of import block (next blank line or non-import line)
lines = content.split("\n")
insert_after = 0
for i, line in enumerate(lines):
    if line.startswith("import ") or line.startswith("from ") or line.strip() == "":
        if line.startswith("import ") or line.startswith("from "):
            insert_after = i

# Check if retry helper already exists
if "_call_anthropic_with_retry" in content:
    print("SKIP: retry helper already exists")
else:
    # Find the line "anthropic_client = Anthropic(...)" and insert after it
    idx = content.find("anthropic_client")
    if idx > 0:
        # Find end of that line
        eol = content.index("\n", idx)
        content = content[:eol+1] + RETRY_HELPER + content[eol+1:]
        print("Added retry helper function")
    
    # Replace direct API calls with retry wrapper
    # Pattern: anthropic_client.messages.create(
    old_call = "anthropic_client.messages.create("
    new_call = "_call_anthropic_with_retry(anthropic_client, "
    count = content.count(old_call)
    content = content.replace(old_call, new_call)
    print(f"Replaced {count} direct API calls with retry wrapper")

    with open("scripts/blog_automation.py", "w") as f:
        f.write(content)
    print("Done!")
