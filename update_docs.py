#!/usr/bin/env python3
"""Update all documentation files to reference draw.io diagrams."""
import re, os

ROOT = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs"

# Mapping: doc file -> list of (mermaid_index, drawio_path, label)
# mermaid_index is 1-based (1st mermaid block, 2nd mermaid block, etc.)
MAPPINGS = {
    "docs/architecture/terraform-multi-cluster-overview.md": [
        (1, "diagrams/architecture/01-high-level-architecture-ipi.drawio", "High-Level Architecture (IPI)"),
        (2, "diagrams/architecture/02-upi-architecture-variant.drawio", "UPI Architecture Variant"),
        (3, "diagrams/architecture/03-upi-install-flow.drawio", "UPI Install Flow"),
        (4, "diagrams/architecture/04-network-architecture.drawio", "Network Architecture"),
        (5, "diagrams/architecture/05-submariner-networking.drawio", "Submariner Cross-Cluster Networking"),
        (6, "diagrams/architecture/06-odf-dr-replication.drawio", "ODF DR Replication"),
        (7, "diagrams/architecture/07-management-cluster-architecture.drawio", "Management Cluster Architecture"),
        (8, "diagrams/architecture/08-acm-import-dr-management.drawio", "ACM Import/DR Management"),
        (9, "diagrams/architecture/09-dr-failover-workflow.drawio", "DR Failover Workflow"),
        (10, "diagrams/architecture/10-inter-cluster-connection-map.drawio", "Inter-Cluster Connection Map"),
        (11, "diagrams/architecture/11-ado-pipeline-scope.drawio", "ADO Pipeline Scope"),
        (12, "diagrams/architecture/12-ipi-vs-upi-comparison.drawio", "IPI vs UPI Comparison"),
    ],
    "docs/clusters/terraform-ocp-baremetal.md": [
        (1, "diagrams/clusters/01-dc-primary-deployment-overview.drawio", "DC Primary Deployment Overview"),
        (2, "diagrams/clusters/02-dc-primary-connectivity.drawio", "DC Primary Connectivity"),
        (3, "diagrams/clusters/03-dc-primary-secrets-flow-ipi.drawio", "Secrets Flow (IPI)"),
        (4, "diagrams/clusters/04-quay-mirror-distribution.drawio", "Quay Mirror Distribution"),
    ],
    "docs/clusters/terraform-upi-baremetal.md": [
        (1, "diagrams/clusters/05-upi-deployment-overview.drawio", "UPI Deployment Overview"),
        (2, "diagrams/clusters/06-upi-deployment-phases.drawio", "UPI Deployment Phases"),
        (3, "diagrams/clusters/07-pxe-boot-sequence.drawio", "PXE Boot Sequence"),
        (4, "diagrams/clusters/08-upi-secrets-flow.drawio", "UPI Secrets Flow"),
    ],
    "docs/clusters/terraform-dr-secondary.md": [
        (1, "diagrams/clusters/09-dr-secondary-architecture.drawio", "DR Secondary Architecture"),
        (2, "diagrams/clusters/10-dr-secondary-connectivity.drawio", "DR Secondary Connectivity"),
        (3, "diagrams/clusters/19-dr-failover-acm-promotion.drawio", "DR Failover ACM Promotion"),
    ],
    "docs/clusters/terraform-mgmt-dc.md": [
        (1, "diagrams/clusters/11-mgmt-dc-architecture.drawio", "Mgmt DC Architecture"),
        (2, "diagrams/clusters/12-mgmt-dc-connectivity.drawio", "Mgmt DC Connectivity"),
        (3, "diagrams/clusters/13-acm-observability-flow.drawio", "ACM Observability Flow"),
        (4, "diagrams/clusters/14-acs-central-security-stack.drawio", "ACS Central Security Stack"),
        (5, "diagrams/clusters/15-acm-hub-components.drawio", "ACM Hub Components"),
        (6, "diagrams/clusters/20-quay-geo-replication-failover.drawio", "Quay Geo-Replication Failover"),
        (7, "diagrams/clusters/21-quay-geo-replication-flow.drawio", "Quay Geo-Replication Flow"),
    ],
    "docs/clusters/terraform-mgmt-dr.md": [
        (1, "diagrams/clusters/16-mgmt-dr-architecture.drawio", "Mgmt DR Architecture"),
        (2, "diagrams/clusters/17-mgmt-dr-connectivity.drawio", "Mgmt DR Connectivity"),
        (3, "diagrams/clusters/18-acs-secured-cluster-components.drawio", "ACS SecuredCluster Components"),
        (4, "diagrams/clusters/22-acm-dr-applications.drawio", "ACM DR Applications"),
    ],
    "docs/pipeline/terraform-ado-pipeline.md": [
        (1, "diagrams/pipeline/02-ipi-pipeline-parameters.drawio", "IPI Pipeline Parameters"),
        (2, "diagrams/pipeline/16-ipi-pipeline-scope.drawio", "IPI Pipeline Scope Selection"),
        (3, "diagrams/pipeline/01-ipi-pipeline-stages.drawio", "IPI Pipeline Stage Execution"),
        (4, "diagrams/pipeline/03-post-deployment-topology.drawio", "Post-Deployment Topology"),
        (5, "diagrams/pipeline/17-pipeline-secrets-flow.drawio", "Pipeline Secrets Flow"),
    ],
    "docs/pipeline/terraform-upi-ado-pipeline.md": [
        (1, "diagrams/pipeline/07-upi-pipeline-parameters.drawio", "UPI Pipeline Parameters"),
        (2, "diagrams/pipeline/08-upi-phase-selection.drawio", "UPI Phase Selection"),
        (3, "diagrams/pipeline/09-upi-pipeline-stages.drawio", "UPI Pipeline Stage Execution"),
    ],
    "docs/pipeline/terraform-acm-import-pipeline.md": [
        (1, "diagrams/pipeline/04-acm-import-pipeline.drawio", "ACM Cluster Import Pipeline"),
    ],
    "docs/pipeline/terraform-acm-dr-pipeline.md": [
        (1, "diagrams/pipeline/05-acm-dr-pipeline.drawio", "ACM DR Failover/Failback Pipeline"),
    ],
    "docs/pipeline/terraform-cnv-pipeline.md": [
        (1, "diagrams/pipeline/10-cnv-pipeline.drawio", "OpenShift Virtualization (CNV) Pipeline"),
    ],
    "docs/pipeline/terraform-vm-migration-pipeline.md": [
        (1, "diagrams/pipeline/11-vm-migration-pipeline.drawio", "VM Migration (MTV) Pipeline"),
    ],
    "docs/pipeline/terraform-mtc-pipeline.md": [
        (1, "diagrams/pipeline/12-mtc-pipeline.drawio", "MTC Container Migration Pipeline"),
    ],
    "docs/pipeline/terraform-ado-pipeline-day2.md": [
        (1, "diagrams/pipeline/06-day2-pipeline-flow.drawio", "Day-2 Pipeline Flow (IPI)"),
    ],
    "docs/pipeline/terraform-upi-ado-pipeline-day2.md": [
        (1, "diagrams/pipeline/13-day2-upi-pipeline.drawio", "Day-2 Pipeline Flow (UPI)"),
    ],
}

def update_doc(rel_path, mappings):
    fpath = os.path.join(ROOT, rel_path)
    if not os.path.exists(fpath):
        print(f"  SKIP (not found): {rel_path}")
        return

    with open(fpath, 'r') as f:
        content = f.read()

    # Find all mermaid blocks
    pattern = re.compile(r'(```mermaid\n.*?```)', re.DOTALL)
    matches = list(pattern.finditer(content))

    if not matches:
        print(f"  SKIP (no mermaid): {rel_path}")
        return

    # Build insertion map: offset -> text to insert after
    insertions = {}
    for mermaid_idx, drawio_path, label in mappings:
        if mermaid_idx <= len(matches):
            match = matches[mermaid_idx - 1]
            end_pos = match.end()
            # Calculate relative path from the doc to the drawio file
            doc_dir = os.path.dirname(rel_path)
            drawio_rel = os.path.relpath(os.path.join("docs", ""), doc_dir)
            # Build the relative path from doc location to drawio file
            drawio_from_doc = os.path.relpath(
                os.path.join(ROOT, "docs", drawio_path.replace("diagrams/", "diagrams/")),
                os.path.join(ROOT, doc_dir)
            )
            insert_text = f'\n\n!!! info "Draw.io Diagram: {label}"\n    📐 [Open in Draw.io]({drawio_from_doc}) — Download and open in [draw.io](https://app.diagrams.net) for interactive editing.\n'
            insertions[end_pos] = insert_text

    # Apply insertions from end to start (to preserve offsets)
    for pos in sorted(insertions.keys(), reverse=True):
        content = content[:pos] + insertions[pos] + content[pos:]

    with open(fpath, 'w') as f:
        f.write(content)

    print(f"  Updated: {rel_path} ({len(insertions)} diagram references added)")

if __name__ == "__main__":
    print("Updating documentation files with draw.io references...")
    for doc, maps in MAPPINGS.items():
        update_doc(doc, maps)
    print("\nDone! All documentation files updated.")
