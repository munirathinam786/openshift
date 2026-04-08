#!/usr/bin/env python3
"""Remove all 'Original Mermaid source' <details> blocks from docs."""
import re, glob

files = glob.glob('docs/**/*.md', recursive=True)
total_removed = 0

# Pattern for standalone <details> blocks with mermaid source
# Handles both formats:
#   <details><summary>📝 Original Mermaid source</summary> ... </details>
#   <details>\n<summary>View original Mermaid source</summary> ... </details>
pattern = re.compile(
    r'\n*[ \t]*<details>\s*<summary>\s*(?:\U0001f4dd\s*)?(?:View )?[Oo]riginal [Mm]ermaid [Ss]ource\s*</summary>\s*\n'
    r'.*?'
    r'\n[ \t]*</details>',
    re.DOTALL
)

for f in sorted(files):
    with open(f, 'r') as fh:
        content = fh.read()

    original = content
    content = pattern.sub('', content)

    # Clean up multiple consecutive blank lines left behind
    content = re.sub(r'\n{3,}', '\n\n', content)

    if content != original:
        before = original.count('```mermaid')
        after = content.count('```mermaid')
        count = before - after
        with open(f, 'w') as fh:
            fh.write(content)
        print(f'  Cleaned {f}: removed {count} mermaid block(s)')
        total_removed += count

print(f'\nTotal mermaid blocks removed: {total_removed}')
