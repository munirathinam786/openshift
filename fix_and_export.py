#!/usr/bin/env python3
"""Fix shadow attribute in all drawio files and export to SVG using draw.io CLI."""
import os, subprocess, glob, re

ROOT = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs"
DRAWIO = "/Applications/draw.io.app/Contents/MacOS/draw.io"
CATEGORIES = ["architecture", "clusters", "pipeline", "code"]

# Step 1: Fix shadow="1" -> shadow="0" in mxGraphModel (and remove shadow=1 from individual styles)
fixed = 0
for cat in CATEGORIES:
    drawio_dir = os.path.join(ROOT, "docs", "diagrams", cat)
    for f in sorted(glob.glob(os.path.join(drawio_dir, "*.drawio"))):
        with open(f, 'r') as fh:
            content = fh.read()
        original = content
        # Fix mxGraphModel shadow attribute
        content = content.replace('shadow="1"', 'shadow="0"')
        # Remove shadow=1 from individual cell styles (keep other shadow properties)
        content = content.replace('shadow=1;', '')
        if content != original:
            with open(f, 'w') as fh:
                fh.write(content)
            fixed += 1

print(f"Fixed shadow attribute in {fixed} drawio files")

# Step 2: Export all .drawio files to SVG
exported = 0
errors = 0
for cat in CATEGORIES:
    drawio_dir = os.path.join(ROOT, "docs", "diagrams", cat)
    for f in sorted(glob.glob(os.path.join(drawio_dir, "*.drawio"))):
        bn = os.path.splitext(os.path.basename(f))[0]
        svg_path = os.path.join(drawio_dir, f"{bn}.svg")
        result = subprocess.run(
            [DRAWIO, "-x", "-f", "svg", "--embed-svg-images", "-b", "10", "-o", svg_path, f],
            capture_output=True, text=True, timeout=60
        )
        if os.path.exists(svg_path) and os.path.getsize(svg_path) > 0:
            exported += 1
            print(f"  OK: {os.path.relpath(svg_path, ROOT)}")
        else:
            errors += 1
            print(f"  FAIL: {os.path.relpath(f, ROOT)} -> {result.stderr.strip()}")

print(f"\nExported: {exported}, Failed: {errors}")
