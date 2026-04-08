#!/usr/bin/env python3
"""Convert raw HTML <img> + <details> blocks to mkdocs-material markdown format."""
import re, glob

files = glob.glob('docs/**/*.md', recursive=True)
total_fixed = 0

# Pattern: <img src="..." alt="..." class="drawio-diagram">
# followed by blank line + <details><summary>📥 Download draw.io source</summary> + link + </details>
pattern = re.compile(
    r'<img src="([^"]+)" alt="([^"]+)" class="drawio-diagram">\s*\n'
    r'\s*\n'
    r'<details><summary>📥 Download draw\.io source</summary>\s*\n'
    r'\s*\n'
    r'\[⬇ ([^\]]+)\]\(([^)]+)\)\s*\n'
    r'\s*\n'
    r'</details>',
    re.MULTILINE
)

def replacement(m):
    svg_path = m.group(1)
    alt_text = m.group(2)
    drawio_name = m.group(3)
    drawio_path = m.group(4)
    
    # Convert alt text: "21-acm-import-workflow" -> "ACM Import Workflow"
    label = alt_text.replace('.svg', '')
    # Remove leading number prefix like "21-"
    label = re.sub(r'^\d+-', '', label)
    # Convert hyphens to spaces and title case
    label = label.replace('-', ' ').title()
    
    return (
        f'![{label}]({svg_path}){{: .drawio-diagram }}\n'
        f'\n'
        f'???+ note "Draw.io Source: {label}"\n'
        f'    [:material-download: Download .drawio file]({drawio_path}){{ .md-button }} — Open in [draw.io](https://app.diagrams.net) for interactive editing.'
    )

for f in sorted(files):
    with open(f, 'r') as fh:
        content = fh.read()
    
    original = content
    content = pattern.sub(replacement, content)
    
    if content != original:
        count = len(pattern.findall(original))
        with open(f, 'w') as fh:
            fh.write(content)
        print(f'  Fixed {f}: {count} img tag(s) converted')
        total_fixed += count

# Also handle standalone <img> tags without <details> block
pattern2 = re.compile(
    r'<img src="([^"]+)" alt="([^"]+)" class="drawio-diagram">',
    re.MULTILINE
)

for f in sorted(files):
    with open(f, 'r') as fh:
        content = fh.read()
    
    original = content
    
    def replacement2(m):
        svg_path = m.group(1)
        alt_text = m.group(2)
        label = alt_text.replace('.svg', '')
        label = re.sub(r'^\d+-', '', label)
        label = label.replace('-', ' ').title()
        return f'![{label}]({svg_path}){{: .drawio-diagram }}'
    
    content = pattern2.sub(replacement2, content)
    
    if content != original:
        count = len(pattern2.findall(original))
        with open(f, 'w') as fh:
            fh.write(content)
        print(f'  Fixed {f}: {count} standalone img tag(s) converted')
        total_fixed += count

print(f'\nTotal fixes: {total_fixed}')
