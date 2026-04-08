#!/usr/bin/env python3
"""Replace mermaid blocks with SVG images in all documentation files.
Keeps existing mermaid code in collapsible details blocks as fallback."""
import re, os

ROOT = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs"

# Mapping: doc file -> list of (mermaid_index, svg_rel_path, drawio_rel_path, label)
# Paths are relative from the doc file's directory
MAPPINGS = {
    "docs/architecture/terraform-multi-cluster-overview.md": [
        (1, "../diagrams/architecture/01-high-level-architecture-ipi.svg", "../diagrams/architecture/01-high-level-architecture-ipi.drawio", "High-Level Architecture (IPI)"),
        (2, "../diagrams/architecture/02-upi-architecture-variant.svg", "../diagrams/architecture/02-upi-architecture-variant.drawio", "UPI Architecture Variant"),
        (3, "../diagrams/architecture/03-upi-install-flow.svg", "../diagrams/architecture/03-upi-install-flow.drawio", "UPI Install Flow"),
        (4, "../diagrams/architecture/04-network-architecture.svg", "../diagrams/architecture/04-network-architecture.drawio", "Network Architecture"),
        (5, "../diagrams/architecture/05-submariner-networking.svg", "../diagrams/architecture/05-submariner-networking.drawio", "Submariner Cross-Cluster Networking"),
        (6, "../diagrams/architecture/06-odf-dr-replication.svg", "../diagrams/architecture/06-odf-dr-replication.drawio", "ODF DR Replication"),
        (7, "../diagrams/architecture/07-management-cluster-architecture.svg", "../diagrams/architecture/07-management-cluster-architecture.drawio", "Management Cluster Architecture"),
        (8, "../diagrams/architecture/08-acm-import-dr-management.svg", "../diagrams/architecture/08-acm-import-dr-management.drawio", "ACM Import/DR Management"),
        (9, "../diagrams/architecture/09-dr-failover-workflow.svg", "../diagrams/architecture/09-dr-failover-workflow.drawio", "DR Failover Workflow"),
        (10, "../diagrams/architecture/10-inter-cluster-connection-map.svg", "../diagrams/architecture/10-inter-cluster-connection-map.drawio", "Inter-Cluster Connection Map"),
        (11, "../diagrams/architecture/11-ado-pipeline-scope.svg", "../diagrams/architecture/11-ado-pipeline-scope.drawio", "ADO Pipeline Scope"),
        (12, "../diagrams/architecture/12-ipi-vs-upi-comparison.svg", "../diagrams/architecture/12-ipi-vs-upi-comparison.drawio", "IPI vs UPI Comparison"),
    ],
    "docs/clusters/terraform-ocp-baremetal.md": [
        (1, "../diagrams/clusters/01-dc-primary-deployment-overview.svg", "../diagrams/clusters/01-dc-primary-deployment-overview.drawio", "DC Primary Deployment Overview"),
        (2, "../diagrams/clusters/02-dc-primary-connectivity.svg", "../diagrams/clusters/02-dc-primary-connectivity.drawio", "DC Primary Connectivity"),
        (3, "../diagrams/clusters/03-dc-primary-secrets-flow-ipi.svg", "../diagrams/clusters/03-dc-primary-secrets-flow-ipi.drawio", "Secrets Flow (IPI)"),
        (4, "../diagrams/clusters/04-quay-mirror-distribution.svg", "../diagrams/clusters/04-quay-mirror-distribution.drawio", "Quay Mirror Distribution"),
    ],
    "docs/clusters/terraform-upi-baremetal.md": [
        (1, "../diagrams/clusters/05-upi-deployment-overview.svg", "../diagrams/clusters/05-upi-deployment-overview.drawio", "UPI Deployment Overview"),
        (2, "../diagrams/clusters/06-upi-deployment-phases.svg", "../diagrams/clusters/06-upi-deployment-phases.drawio", "UPI Deployment Phases"),
        (3, "../diagrams/clusters/07-pxe-boot-sequence.svg", "../diagrams/clusters/07-pxe-boot-sequence.drawio", "PXE Boot Sequence"),
        (4, "../diagrams/clusters/08-upi-secrets-flow.svg", "../diagrams/clusters/08-upi-secrets-flow.drawio", "UPI Secrets Flow"),
    ],
    "docs/clusters/terraform-dr-secondary.md": [
        (1, "../diagrams/clusters/09-dr-secondary-architecture.svg", "../diagrams/clusters/09-dr-secondary-architecture.drawio", "DR Secondary Architecture"),
        (2, "../diagrams/clusters/10-dr-secondary-connectivity.svg", "../diagrams/clusters/10-dr-secondary-connectivity.drawio", "DR Secondary Connectivity"),
        (3, "../diagrams/clusters/19-dr-failover-acm-promotion.svg", "../diagrams/clusters/19-dr-failover-acm-promotion.drawio", "DR Failover ACM Promotion"),
    ],
    "docs/clusters/terraform-mgmt-dc.md": [
        (1, "../diagrams/clusters/11-mgmt-dc-architecture.svg", "../diagrams/clusters/11-mgmt-dc-architecture.drawio", "Mgmt DC Architecture"),
        (2, "../diagrams/clusters/12-mgmt-dc-connectivity.svg", "../diagrams/clusters/12-mgmt-dc-connectivity.drawio", "Mgmt DC Connectivity"),
        (3, "../diagrams/clusters/13-acm-observability-flow.svg", "../diagrams/clusters/13-acm-observability-flow.drawio", "ACM Observability Flow"),
        (4, "../diagrams/clusters/14-acs-central-security-stack.svg", "../diagrams/clusters/14-acs-central-security-stack.drawio", "ACS Central Security Stack"),
        (5, "../diagrams/clusters/15-acm-hub-components.svg", "../diagrams/clusters/15-acm-hub-components.drawio", "ACM Hub Components"),
        (6, "../diagrams/clusters/20-quay-geo-replication-failover.svg", "../diagrams/clusters/20-quay-geo-replication-failover.drawio", "Quay Geo-Replication Failover"),
        (7, "../diagrams/clusters/21-quay-geo-replication-flow.svg", "../diagrams/clusters/21-quay-geo-replication-flow.drawio", "Quay Geo-Replication Flow"),
    ],
    "docs/clusters/terraform-mgmt-dr.md": [
        (1, "../diagrams/clusters/16-mgmt-dr-architecture.svg", "../diagrams/clusters/16-mgmt-dr-architecture.drawio", "Mgmt DR Architecture"),
        (2, "../diagrams/clusters/17-mgmt-dr-connectivity.svg", "../diagrams/clusters/17-mgmt-dr-connectivity.drawio", "Mgmt DR Connectivity"),
        (3, "../diagrams/clusters/18-acs-secured-cluster-components.svg", "../diagrams/clusters/18-acs-secured-cluster-components.drawio", "ACS SecuredCluster Components"),
        (4, "../diagrams/clusters/22-acm-dr-applications.svg", "../diagrams/clusters/22-acm-dr-applications.drawio", "ACM DR Applications"),
    ],
    "docs/pipeline/terraform-ado-pipeline.md": [
        (1, "../diagrams/pipeline/02-ipi-pipeline-parameters.svg", "../diagrams/pipeline/02-ipi-pipeline-parameters.drawio", "IPI Pipeline Parameters"),
        (2, "../diagrams/pipeline/16-ipi-pipeline-scope.svg", "../diagrams/pipeline/16-ipi-pipeline-scope.drawio", "IPI Pipeline Scope Selection"),
        (3, "../diagrams/pipeline/01-ipi-pipeline-stages.svg", "../diagrams/pipeline/01-ipi-pipeline-stages.drawio", "IPI Pipeline Stage Execution"),
        (4, "../diagrams/pipeline/03-post-deployment-topology.svg", "../diagrams/pipeline/03-post-deployment-topology.drawio", "Post-Deployment Topology"),
        (5, "../diagrams/pipeline/17-pipeline-secrets-flow.svg", "../diagrams/pipeline/17-pipeline-secrets-flow.drawio", "Pipeline Secrets Flow"),
    ],
    "docs/pipeline/terraform-upi-ado-pipeline.md": [
        (1, "../diagrams/pipeline/07-upi-pipeline-parameters.svg", "../diagrams/pipeline/07-upi-pipeline-parameters.drawio", "UPI Pipeline Parameters"),
        (2, "../diagrams/pipeline/08-upi-phase-selection.svg", "../diagrams/pipeline/08-upi-phase-selection.drawio", "UPI Phase Selection"),
        (3, "../diagrams/pipeline/09-upi-pipeline-stages.svg", "../diagrams/pipeline/09-upi-pipeline-stages.drawio", "UPI Pipeline Stage Execution"),
    ],
    "docs/pipeline/terraform-acm-import-pipeline.md": [
        (1, "../diagrams/pipeline/04-acm-import-pipeline.svg", "../diagrams/pipeline/04-acm-import-pipeline.drawio", "ACM Cluster Import Pipeline"),
    ],
    "docs/pipeline/terraform-acm-dr-pipeline.md": [
        (1, "../diagrams/pipeline/05-acm-dr-pipeline.svg", "../diagrams/pipeline/05-acm-dr-pipeline.drawio", "ACM DR Failover/Failback Pipeline"),
    ],
    "docs/pipeline/terraform-cnv-pipeline.md": [
        (1, "../diagrams/pipeline/10-cnv-pipeline.svg", "../diagrams/pipeline/10-cnv-pipeline.drawio", "OpenShift Virtualization (CNV) Pipeline"),
    ],
    "docs/pipeline/terraform-vm-migration-pipeline.md": [
        (1, "../diagrams/pipeline/11-vm-migration-pipeline.svg", "../diagrams/pipeline/11-vm-migration-pipeline.drawio", "VM Migration (MTV) Pipeline"),
    ],
    "docs/pipeline/terraform-mtc-pipeline.md": [
        (1, "../diagrams/pipeline/12-mtc-pipeline.svg", "../diagrams/pipeline/12-mtc-pipeline.drawio", "MTC Container Migration Pipeline"),
    ],
    "docs/pipeline/terraform-ado-pipeline-day2.md": [
        (1, "../diagrams/pipeline/06-day2-pipeline-flow.svg", "../diagrams/pipeline/06-day2-pipeline-flow.drawio", "Day-2 Pipeline Flow (IPI)"),
    ],
    "docs/pipeline/terraform-upi-ado-pipeline-day2.md": [
        (1, "../diagrams/pipeline/13-day2-upi-pipeline.svg", "../diagrams/pipeline/13-day2-upi-pipeline.drawio", "Day-2 Pipeline Flow (UPI)"),
    ],
}


def update_doc(rel_path, mappings):
    fpath = os.path.join(ROOT, rel_path)
    if not os.path.exists(fpath):
        print(f"  SKIP (not found): {rel_path}")
        return

    with open(fpath, 'r') as f:
        content = f.read()

    # First, remove any previously-added draw.io info admonitions from update_docs.py
    content = re.sub(
        r'\n\n!!! info "Draw\.io Diagram: [^"]*"\n    📐 \[Open in Draw\.io\]\([^)]*\) — Download and open in \[draw\.io\]\(https://app\.diagrams\.net\) for interactive editing\.\n',
        '\n',
        content
    )

    # Find all mermaid blocks
    pattern = re.compile(r'(```mermaid\n.*?```)', re.DOTALL)
    matches = list(pattern.finditer(content))

    if not matches:
        print(f"  SKIP (no mermaid): {rel_path}")
        return

    # Build replacement map: match_index -> (svg_path, drawio_path, label)
    replacement_map = {}
    for mermaid_idx, svg_path, drawio_path, label in mappings:
        if mermaid_idx <= len(matches):
            replacement_map[mermaid_idx - 1] = (svg_path, drawio_path, label)

    # Replace mermaid blocks from end to start
    for idx in sorted(replacement_map.keys(), reverse=True):
        match = matches[idx]
        svg_path, drawio_path, label = replacement_map[idx]
        mermaid_code = match.group(1)

        replacement = f'''![{label}]({svg_path}){{: .drawio-diagram }}

???+ note "Draw.io Source: {label}"
    [:material-download: Download .drawio file]({drawio_path}){{ .md-button }} — Open in [draw.io](https://app.diagrams.net) for interactive editing.

    <details>
    <summary>View original Mermaid source</summary>

    {mermaid_code}

    </details>'''

        content = content[:match.start()] + replacement + content[match.end():]

    with open(fpath, 'w') as f:
        f.write(content)

    print(f"  Updated: {rel_path} ({len(replacement_map)} mermaid blocks replaced with SVG)")


if __name__ == "__main__":
    print("Replacing mermaid diagrams with SVG images...")
    for doc, maps in MAPPINGS.items():
        update_doc(doc, maps)
    print("\nDone!")
