#!/usr/bin/env python3
"""Replace all 18 remaining mermaid blocks with SVG images + collapsible source."""
import re, os

ROOT = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs"

# Mapping: (file_relative_to_docs, approx_start_line) -> (svg_path_relative_to_docs, drawio_path_relative_to_docs)
REPLACEMENTS = [
    ("docs/architecture/terraform-multi-cluster-overview.md", 900,
     "diagrams/architecture/13-protocol-port-map.svg",
     "diagrams/architecture/13-protocol-port-map.drawio"),
    ("docs/clusters/terraform-mgmt-dc.md", 402,
     "diagrams/clusters/23-acm-import-topology.svg",
     "diagrams/clusters/23-acm-import-topology.drawio"),
    ("docs/clusters/terraform-mgmt-dc.md", 431,
     "diagrams/clusters/24-acm-dr-application-failover.svg",
     "diagrams/clusters/24-acm-dr-application-failover.drawio"),
    ("docs/clusters/terraform-mgmt-dr.md", 215,
     "diagrams/clusters/25-quay-failover-behavior.svg",
     "diagrams/clusters/25-quay-failover-behavior.drawio"),
    ("docs/clusters/terraform-mgmt-dr.md", 285,
     "diagrams/clusters/26-acm-post-failover-reimport.svg",
     "diagrams/clusters/26-acm-post-failover-reimport.drawio"),
    ("docs/pipeline/terraform-ado-pipeline.md", 207,
     "diagrams/pipeline/19-ado-deploy-topology.svg",
     "diagrams/pipeline/19-ado-deploy-topology.drawio"),
    ("docs/pipeline/terraform-ado-pipeline.md", 289,
     "diagrams/pipeline/20-full-deployment-sequence.svg",
     "diagrams/pipeline/20-full-deployment-sequence.drawio"),
    ("docs/pipeline/terraform-acm-import-pipeline.md", 71,
     "diagrams/pipeline/21-acm-import-workflow.svg",
     "diagrams/pipeline/21-acm-import-workflow.drawio"),
    ("docs/pipeline/terraform-acm-dr-pipeline.md", 70,
     "diagrams/pipeline/22-acm-dr-stages.svg",
     "diagrams/pipeline/22-acm-dr-stages.drawio"),
    ("docs/pipeline/terraform-acm-dr-pipeline.md", 115,
     "diagrams/pipeline/23-acm-dr-failover-workflow.svg",
     "diagrams/pipeline/23-acm-dr-failover-workflow.drawio"),
    ("docs/pipeline/terraform-cnv-pipeline.md", 82,
     "diagrams/pipeline/24-cnv-deploy-workflow.svg",
     "diagrams/pipeline/24-cnv-deploy-workflow.drawio"),
    ("docs/pipeline/terraform-vm-migration-pipeline.md", 75,
     "diagrams/pipeline/25-vm-migration-workflow.svg",
     "diagrams/pipeline/25-vm-migration-workflow.drawio"),
    ("docs/pipeline/terraform-upi-ado-pipeline.md", 122,
     "diagrams/pipeline/26-upi-boot-gate.svg",
     "diagrams/pipeline/26-upi-boot-gate.drawio"),
    ("docs/code/ipi-method/openshiftbaremetal/main.md", 8,
     "diagrams/code/07-ipi-dc-dep-chain.svg",
     "diagrams/code/07-ipi-dc-dep-chain.drawio"),
    ("docs/code/ipi-method/openshiftbaremetal-dr/main.md", 9,
     "diagrams/code/08-ipi-dr-dep-chain.svg",
     "diagrams/code/08-ipi-dr-dep-chain.drawio"),
    ("docs/code/ipi-method/pipeline/azure-pipelines.md", 36,
     "diagrams/code/09-ipi-pipeline-stage-order.svg",
     "diagrams/code/09-ipi-pipeline-stage-order.drawio"),
    ("docs/code/upi-method/main.md", 18,
     "diagrams/code/10-upi-dc-dep-chain.svg",
     "diagrams/code/10-upi-dc-dep-chain.drawio"),
    ("docs/code/upi-method/openshiftbaremetal-dr/main.md", 14,
     "diagrams/code/11-upi-dr-dep-chain.svg",
     "diagrams/code/11-upi-dr-dep-chain.drawio"),
]

def compute_relative_path(md_file, target_file):
    """Compute the relative path from md_file directory to target_file, both relative to docs/."""
    md_dir = os.path.dirname(md_file)  # e.g. "docs/architecture" or "docs/code/ipi-method/openshiftbaremetal"
    target = os.path.join("docs", target_file)  # e.g. "docs/diagrams/code/07-ipi-dc-dep-chain.svg"
    return os.path.relpath(target, md_dir)

def replace_mermaid_block(content, approx_line, svg_rel, drawio_rel, md_file):
    """Find and replace the mermaid block nearest to approx_line."""
    lines = content.split('\n')
    
    # Find the ```mermaid line nearest to approx_line (1-indexed)
    target_idx = approx_line - 1  # 0-indexed
    search_range = range(max(0, target_idx - 10), min(len(lines), target_idx + 10))
    
    start_idx = None
    min_dist = 999
    for i in search_range:
        if lines[i].strip() == '```mermaid' and not lines[i].startswith('    '):
            dist = abs(i - target_idx)
            if dist < min_dist:
                min_dist = dist
                start_idx = i
    
    if start_idx is None:
        print(f"  WARNING: No mermaid block found near line {approx_line} in {md_file}")
        return content, False
    
    # Find closing ```
    end_idx = None
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip() == '```' and not lines[i].startswith('    '):
            end_idx = i
            break
    
    if end_idx is None:
        print(f"  WARNING: No closing ``` found for block at line {start_idx+1} in {md_file}")
        return content, False
    
    # Extract the mermaid source
    mermaid_source = '\n'.join(lines[start_idx:end_idx+1])
    
    # Build replacement
    svg_name = os.path.basename(svg_rel).replace('.svg', '')
    replacement = f'''<img src="{svg_rel}" alt="{svg_name}" class="drawio-diagram">

<details><summary>📥 Download draw.io source</summary>

[⬇ {os.path.basename(drawio_rel)}]({drawio_rel})

</details>

<details><summary>📝 Original Mermaid source</summary>

{mermaid_source}

</details>'''
    
    # Replace
    new_lines = lines[:start_idx] + replacement.split('\n') + lines[end_idx+1:]
    return '\n'.join(new_lines), True

def process_file(md_file, replacements_for_file):
    """Process a single markdown file with multiple replacements, largest line first."""
    filepath = os.path.join(ROOT, md_file)
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Sort by line number descending so replacements don't shift line numbers
    replacements_for_file.sort(key=lambda x: x[0], reverse=True)
    
    changed = False
    for approx_line, svg_path, drawio_path in replacements_for_file:
        svg_rel = compute_relative_path(md_file, svg_path)
        drawio_rel = compute_relative_path(md_file, drawio_path)
        content, ok = replace_mermaid_block(content, approx_line, svg_rel, drawio_rel, md_file)
        if ok:
            changed = True
            print(f"  Replaced line ~{approx_line}")
    
    if changed:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ Written: {md_file}")

def main():
    # Group replacements by file
    by_file = {}
    for md_file, line, svg, drawio in REPLACEMENTS:
        by_file.setdefault(md_file, []).append((line, svg, drawio))
    
    print(f"Processing {len(by_file)} files with {len(REPLACEMENTS)} replacements...")
    for md_file, repls in by_file.items():
        print(f"\n{md_file} ({len(repls)} blocks):")
        process_file(md_file, repls)
    
    print(f"\nDone! All {len(REPLACEMENTS)} replacements processed.")

if __name__ == "__main__":
    main()
