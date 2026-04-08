#!/bin/bash
# Export 18 new batch 11 draw.io files to SVG
cd /Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs

DRAWIO="/Applications/draw.io.app/Contents/MacOS/draw.io"
OK=0
FAIL=0

FILES=(
  "docs/diagrams/architecture/13-protocol-port-map.drawio"
  "docs/diagrams/clusters/23-acm-import-topology.drawio"
  "docs/diagrams/clusters/24-acm-dr-application-failover.drawio"
  "docs/diagrams/clusters/25-quay-failover-behavior.drawio"
  "docs/diagrams/clusters/26-acm-post-failover-reimport.drawio"
  "docs/diagrams/pipeline/19-ado-deploy-topology.drawio"
  "docs/diagrams/pipeline/20-full-deployment-sequence.drawio"
  "docs/diagrams/pipeline/21-acm-import-workflow.drawio"
  "docs/diagrams/pipeline/22-acm-dr-stages.drawio"
  "docs/diagrams/pipeline/23-acm-dr-failover-workflow.drawio"
  "docs/diagrams/pipeline/24-cnv-deploy-workflow.drawio"
  "docs/diagrams/pipeline/25-vm-migration-workflow.drawio"
  "docs/diagrams/pipeline/26-upi-boot-gate.drawio"
  "docs/diagrams/code/07-ipi-dc-dep-chain.drawio"
  "docs/diagrams/code/08-ipi-dr-dep-chain.drawio"
  "docs/diagrams/code/09-ipi-pipeline-stage-order.drawio"
  "docs/diagrams/code/10-upi-dc-dep-chain.drawio"
  "docs/diagrams/code/11-upi-dr-dep-chain.drawio"
)

for f in "${FILES[@]}"; do
  svg="${f%.drawio}.svg"
  "$DRAWIO" --export --format svg --embed-svg-images -b 10 -o "$svg" "$f" 2>&1
  if [ -f "$svg" ]; then
    echo "OK: $svg"
    OK=$((OK+1))
  else  
    echo "FAIL: $f"
    FAIL=$((FAIL+1))
  fi
done

echo ""
echo "Done: $OK OK, $FAIL FAIL"
