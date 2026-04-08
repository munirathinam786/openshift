#!/usr/bin/env python3
"""Check if remaining mermaid blocks are inside <details> tags."""
import subprocess, os

ROOT = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs"
result = subprocess.run(['grep', '-rn', '^```mermaid', 'docs/', '--include=*.md'],
                       capture_output=True, text=True, cwd=ROOT)
for line in result.stdout.strip().split('\n'):
    if not line: continue
    parts = line.split(':')
    fpath, linenum = parts[0], int(parts[1])
    with open(os.path.join(ROOT, fpath)) as f:
        lines = f.readlines()
    start = max(0, linenum - 6)
    context = ''.join(lines[start:linenum])
    status = 'IN_DETAILS' if '<details>' in context else 'EXPOSED'
    print(f'{status}: {fpath}:{linenum}')
