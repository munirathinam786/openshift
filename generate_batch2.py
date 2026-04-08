#!/usr/bin/env python3
"""Batch 2: Architecture - Management, DR Failover, Connection Map, Pipeline Scope (6 diagrams)"""
import os, html

BASE = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs/docs/diagrams/architecture"
os.makedirs(BASE, exist_ok=True)

RH_RED="#EE0000";RH_DARK_RED="#CC0000";DC_GREEN="#2E7D32";DC_GREEN_BG="#E8F5E9"
DR_BLUE="#1565C0";DR_BLUE_BG="#E3F2FD";MGMT_ORANGE="#EF6C00";MGMT_ORANGE_BG="#FFF3E0"
WL_PURPLE="#7B1FA2";WL_PURPLE_BG="#F3E5F5";IR_BG="#FCE4EC";IR="#C62828"
WHITE="#FFFFFF";DARK="#333333";K8S_BLUE="#326CE5"

def esc(s): return html.escape(s)
def wrap(name, w, h, cells):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2026-04-07T00:00:00.000Z" agent="GitHub Copilot" version="24.0.0" type="device">
  <diagram id="d1" name="{esc(name)}">
    <mxGraphModel dx="1422" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{w}" pageHeight="{h}" math="0" shadow="1">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{cells}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

SITE_S = lambda color: f"rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=12 8;fillColor=none;fontSize=16;fontStyle=1;verticalAlign=top;align=left;spacingTop=8;spacingLeft=12;container=1;collapsible=0;strokeWidth=3;strokeColor={color};"
CLUSTER_S = lambda c,s=None: f"swimlane;startSize=35;fillColor={c};fontColor=#FFFFFF;strokeColor={s or c};rounded=1;shadow=1;fontSize=13;fontStyle=1;whiteSpace=wrap;html=1;container=1;collapsible=0;"
COMP_S = lambda f=WHITE,s=DARK,b=0,fc=DARK: f"rounded=1;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize=11;fontStyle={b};fontColor={fc};shadow=1;arcSize=10;"
RH_S = lambda: COMP_S(RH_RED, RH_DARK_RED, 1, WHITE)
EDGE_S = lambda c=DARK: f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={c};fontSize=10;fontColor={c};labelBackgroundColor=#FFFFFF;strokeWidth=2;"
DASH_S = lambda c=DARK: f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={c};fontSize=10;fontColor={c};dashed=1;dashPattern=8 4;labelBackgroundColor=#FFFFFF;strokeWidth=2;"
TITLE_S = "text;html=1;align=center;verticalAlign=middle;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"

def cell(id,val,x,y,w,h,style,parent="1"):
    return f'        <mxCell id="{id}" value="{esc(val)}" style="{style}" vertex="1" parent="{parent}">\n          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n        </mxCell>'
def edge(id,src,tgt,val="",style="",parent="1"):
    return f'        <mxCell id="{id}" value="{esc(val)}" style="{style if style else EDGE_S()}" edge="1" source="{src}" target="{tgt}" parent="{parent}">\n          <mxGeometry relative="1" as="geometry"/>\n        </mxCell>'
def save(fn, xml):
    p = os.path.join(BASE, fn)
    with open(p,'w') as f: f.write(xml)
    print(f"  Created: {p}")

# ═══════════════════════════════════════
# DIAGRAM 7: Management Cluster Architecture
# ═══════════════════════════════════════
def diagram_7():
    c = []
    # Mgmt DC
    c.append(cell("mdc","<b>Management DC</b>",40,60,420,320,CLUSTER_S(MGMT_ORANGE)))
    c.append(cell("acm2","<b>ACM Hub</b><br>MultiClusterHub CR",20,50,180,55,RH_S(),"mdc"))
    c.append(cell("acs2","<b>ACS Central</b><br>Vulnerability Scanning<br>Policy Enforcement",215,50,180,70,COMP_S(IR_BG,IR,1),"mdc"))
    c.append(cell("quay2","<b>Quay Enterprise</b><br>Image Registry<br>Clair Scanning",20,125,180,65,COMP_S("#E8EAF6","#3F51B5",1),"mdc"))
    c.append(cell("obs2","ACM Observability<br><i>(optional)</i>",215,140,180,40,COMP_S("#FFF8E1","#F57F17",0),"mdc"))
    c.append(cell("odf_mdc","ODF Storage",20,210,120,35,COMP_S("#E0F2F1","#00695C",0),"mdc"))

    # Mgmt DR
    c.append(cell("mdr","<b>Management DR</b>",520,60,380,320,CLUSTER_S(MGMT_ORANGE)))
    c.append(cell("acm_s2","<b>ACM Standby</b><br>Passive Hub<br><i>Promotable on failover</i>",20,50,170,70,COMP_S(MGMT_ORANGE_BG,MGMT_ORANGE,1),"mdr"))
    c.append(cell("acs_s2","<b>ACS Secured</b><br>Sensor + Collector<br><i>Reports to DC</i>",205,50,155,70,COMP_S(IR_BG,IR,1),"mdr"))
    c.append(cell("quay_s2","<b>Quay Enterprise</b><br>Geo-Replicated",20,140,170,50,COMP_S("#E8EAF6","#3F51B5",1),"mdr"))

    # Workloads
    c.append(cell("wl","<b>Managed Workload Clusters</b>",200,430,540,100,CLUSTER_S(WL_PURPLE)))
    c.append(cell("w_dc","DC Primary",30,45,120,40,COMP_S(DC_GREEN_BG,DC_GREEN,1),"wl"))
    c.append(cell("w_dr","DR Secondary",180,45,120,40,COMP_S(DR_BLUE_BG,DR_BLUE,1),"wl"))

    c.append(edge("me1","acm2","w_dc","Cluster lifecycle\nPolicy, Governance",EDGE_S(MGMT_ORANGE)))
    c.append(edge("me2","acm2","w_dr","Cluster lifecycle",EDGE_S(MGMT_ORANGE)))
    c.append(edge("me3","acs2","w_dc","Security policies",EDGE_S(IR)))
    c.append(edge("me4","acs2","w_dr","Security policies",EDGE_S(IR)))
    c.append(edge("me5","acs2","acs_s2","Central endpoint",EDGE_S(IR)))
    c.append(edge("me6","acm2","acm_s2","DR failover\npromotion",DASH_S(MGMT_ORANGE)))
    c.append(edge("me7","quay2","quay_s2","Geo-replication",DASH_S("#3F51B5")))

    c.append(cell("t","<b>Management Cluster Architecture</b>",220,15,500,30,TITLE_S))
    save("07-management-cluster-architecture.drawio",wrap("Management Cluster Architecture",960,560,"\n".join(c)))

# ═══════════════════════════════════════
# DIAGRAM 8: ACM Cluster Import & DR App Management
# ═══════════════════════════════════════
def diagram_8():
    c = []
    c.append(cell("acm_ops","<b>ACM Hub Operations</b>",40,60,400,180,CLUSTER_S(MGMT_ORANGE)))
    c.append(cell("import","<b>ACM Cluster Import</b><br>ManagedCluster<br>KlusterletAddonConfig<br>ManagedClusterSet",15,45,180,90,COMP_S(MGMT_ORANGE_BG,MGMT_ORANGE,1),"acm_ops"))
    c.append(cell("dr_ops","<b>ACM DR Applications</b><br>DRPolicy<br>DRPlacementControl<br>ODR Hub Operator",210,45,175,90,COMP_S(MGMT_ORANGE_BG,MGMT_ORANGE,1),"acm_ops"))

    c.append(cell("pipes","<b>Dedicated Pipelines</b>",40,290,400,130,CLUSTER_S(DC_GREEN)))
    c.append(cell("p_imp","azure-pipelines-acm-import.yml<br><i>Import scope, feature toggles</i>",15,45,180,55,COMP_S(DC_GREEN_BG,DC_GREEN,0),"pipes"))
    c.append(cell("p_dr","azure-pipelines-acm-dr.yml<br><i>Configure / Failover / Failback</i>",210,45,175,55,COMP_S(DC_GREEN_BG,DC_GREEN,0),"pipes"))

    c.append(cell("targets","<b>Target Clusters</b>",500,150,180,130,CLUSTER_S(WL_PURPLE)))
    c.append(cell("dc_t","DC Primary",20,45,140,35,COMP_S(DC_GREEN_BG,DC_GREEN,1),"targets"))
    c.append(cell("dr_t","DR Secondary",20,90,140,35,COMP_S(DR_BLUE_BG,DR_BLUE,1),"targets"))

    c.append(edge("ae1","p_imp","import","terraform apply\n-var-file=acm-import.tfvars",EDGE_S(DC_GREEN)))
    c.append(edge("ae2","p_dr","dr_ops","terraform apply\n-var-file=acm-dr.tfvars",EDGE_S(DC_GREEN)))
    c.append(edge("ae3","import","dc_t","Import + Addons",EDGE_S(MGMT_ORANGE)))
    c.append(edge("ae4","import","dr_t","Import + Addons",EDGE_S(MGMT_ORANGE)))
    c.append(edge("ae5","dr_ops","dc_t","Failover / Failback",DASH_S(IR)))
    c.append(edge("ae6","dr_ops","dr_t","Failover / Failback",DASH_S(IR)))

    c.append(cell("t","<b>ACM Cluster Import & DR Application Management</b>",80,15,600,30,TITLE_S))
    save("08-acm-import-dr-management.drawio",wrap("ACM Import & DR",740,460,"\n".join(c)))

# ═══════════════════════════════════════
# DIAGRAM 9: DR Failover Workflow (Sequence-style)
# ═══════════════════════════════════════
def diagram_9():
    c = []
    # Actors
    actors = [
        ("op","Operations Team",40,40,140,40,"#1A237E"),
        ("ado","Azure DevOps",220,40,140,40,"#1A237E"),
        ("mdc_a","Mgmt DC",400,40,120,40,MGMT_ORANGE),
        ("mdr_a","Mgmt DR",560,40,120,40,MGMT_ORANGE),
        ("dc_a","DC Primary",720,40,120,40,DC_GREEN),
        ("dr_a","DR Secondary",880,40,120,40,DR_BLUE),
    ]
    for aid,albl,ax,ay,aw,ah,ac in actors:
        c.append(cell(aid,f"<b>{albl}</b>",ax,ay,aw,ah,COMP_S(ac,ac,1,WHITE)))

    # DC Failure
    c.append(cell("fail","❌ DC Site Failure",680,100,200,30,COMP_S(IR_BG,IR,1,IR)))

    # Phase 1
    c.append(cell("ph1","<b>Failover Actions</b>",180,150,780,120,f"rounded=1;whiteSpace=wrap;html=1;fillColor={IR_BG};strokeColor={IR};dashed=1;dashPattern=8 4;fontSize=12;fontStyle=1;fontColor={IR};verticalAlign=top;align=left;spacingTop=5;container=1;collapsible=0;"))
    c.append(cell("s1","Trigger DR failover pipeline",20,35,230,30,COMP_S(),"ph1"))
    c.append(cell("s2","Promote ACM Standby → Active Hub",280,35,240,30,COMP_S(MGMT_ORANGE_BG,MGMT_ORANGE,1),"ph1"))
    c.append(cell("s3","Activate DR workloads",550,35,180,30,COMP_S(DR_BLUE_BG,DR_BLUE,1),"ph1"))
    c.append(cell("s4","Switch ODF MirrorPeer to primary",280,75,240,30,COMP_S("#E0F2F1","#00695C",0),"ph1"))

    c.append(edge("fe1","op","s1","1",EDGE_S(DARK)))
    c.append(edge("fe2","s1","s2","2",EDGE_S(MGMT_ORANGE)))
    c.append(edge("fe3","s2","s3","3",EDGE_S(DR_BLUE)))

    # DR Active
    c.append(cell("active","✅ DR is now Active",780,290,180,30,COMP_S(DC_GREEN_BG,DC_GREEN,1,DC_GREEN)))

    # Phase 2 - Recovery
    c.append(cell("ph2","<b>DC Recovery</b>",180,340,780,100,f"rounded=1;whiteSpace=wrap;html=1;fillColor={DC_GREEN_BG};strokeColor={DC_GREEN};dashed=1;dashPattern=8 4;fontSize=12;fontStyle=1;fontColor={DC_GREEN};verticalAlign=top;align=left;spacingTop=5;container=1;collapsible=0;"))
    c.append(cell("r1","Trigger DC recovery pipeline",20,35,230,30,COMP_S(),"ph2"))
    c.append(cell("r2","Rebuild / Restore DC cluster",280,35,220,30,COMP_S(DC_GREEN_BG,DC_GREEN,0),"ph2"))
    c.append(cell("r3","Re-enable ODF mirroring (reverse)",280,75,230,30,COMP_S("#E0F2F1","#00695C",0),"ph2"))
    c.append(cell("r4","Restore ACM Hub as primary",550,35,200,30,COMP_S(MGMT_ORANGE_BG,MGMT_ORANGE,1),"ph2"))

    c.append(cell("t","<b>Disaster Recovery Failover Workflow</b>",280,5,500,30,TITLE_S))
    save("09-dr-failover-workflow.drawio",wrap("DR Failover Workflow",1080,470,"\n".join(c)))

# ═══════════════════════════════════════
# DIAGRAM 10: Complete Inter-Cluster Connection Map
# ═══════════════════════════════════════
def diagram_10():
    c = []
    # DC Site
    c.append(cell("dc_s","<b>DC Site</b>",20,50,650,500,SITE_S(DC_GREEN)))
    # DC Workload
    c.append(cell("dc_wl","<b>DC Primary Workload</b>",20,45,300,260,CLUSTER_S(DC_GREEN),"dc_s"))
    c.append(cell("dc_api","API Server\n:6443",15,45,130,40,COMP_S(),"dc_wl"))
    c.append(cell("dc_broker","Submariner Broker\n:8443",15,100,140,40,COMP_S("#E3F2FD",K8S_BLUE,1,K8S_BLUE),"dc_wl"))
    c.append(cell("dc_gw","Submariner Gateway\n:4500/UDP (IPsec)",15,155,160,40,COMP_S("#E3F2FD",K8S_BLUE,1,K8S_BLUE),"dc_wl"))
    c.append(cell("dc_odf_c","ODF Ceph\nRBD Mirror Daemon",15,210,150,40,COMP_S("#E0F2F1","#00695C",1),"dc_wl"))
    # DC Mgmt
    c.append(cell("mdc_c","<b>Mgmt DC</b>",340,45,280,260,CLUSTER_S(MGMT_ORANGE),"dc_s"))
    c.append(cell("acm_api","ACM Hub API\n:443",15,45,120,40,RH_S(),"mdc_c"))
    c.append(cell("acs_cent","ACS Central\n:443 gRPC",150,45,115,40,COMP_S(IR_BG,IR,1),"mdc_c"))
    c.append(cell("quay_p","Quay Enterprise\n:443",15,100,120,40,COMP_S("#E8EAF6","#3F51B5",1),"mdc_c"))
    c.append(cell("acm_obs2","ACM Observability\nThanos :10902",150,100,115,40,COMP_S("#FFF8E1","#F57F17",0),"mdc_c"))

    # DR Site
    c.append(cell("dr_s","<b>DR Site</b>",700,50,650,500,SITE_S(DR_BLUE)))
    # DR Workload
    c.append(cell("dr_wl","<b>DR Secondary Workload</b>",20,45,300,260,CLUSTER_S(DR_BLUE),"dr_s"))
    c.append(cell("dr_api","API Server\n:6443",15,45,130,40,COMP_S(),"dr_wl"))
    c.append(cell("dr_gw","Submariner Gateway\n:4500/UDP (IPsec)",15,100,160,40,COMP_S("#E3F2FD",K8S_BLUE,1,K8S_BLUE),"dr_wl"))
    c.append(cell("dr_odf_c","ODF Ceph\nRBD Mirror Daemon",15,155,150,40,COMP_S("#E0F2F1","#00695C",1),"dr_wl"))
    # DR Mgmt
    c.append(cell("mdr_c","<b>Mgmt DR</b>",340,45,280,200,CLUSTER_S(MGMT_ORANGE),"dr_s"))
    c.append(cell("acm_s3","ACM Standby\n:443",15,45,120,40,COMP_S(MGMT_ORANGE_BG,MGMT_ORANGE,1),"mdr_c"))
    c.append(cell("acs_sc","ACS SecuredCluster\nSensor :443",150,45,120,40,COMP_S(IR_BG,IR,1),"mdr_c"))
    c.append(cell("quay_s3","Quay Enterprise\n:443",15,100,120,40,COMP_S("#E8EAF6","#3F51B5",1),"mdr_c"))

    # 8 Connections
    c.append(edge("c1","dc_gw","dr_gw","① IPsec Tunnel\nUDP 4500 + 500 + ESP",EDGE_S(K8S_BLUE)))
    c.append(edge("c2","dc_odf_c","dr_odf_c","② RBD Mirroring\nTCP 6789, 3300",EDGE_S("#00695C")))
    c.append(edge("c3","acm_api","dc_api","③ Cluster Import\nTCP 443",EDGE_S(MGMT_ORANGE)))
    c.append(edge("c4","acm_api","dr_api","④ Cluster Import\nTCP 443",EDGE_S(MGMT_ORANGE)))
    c.append(edge("c5","acs_sc","acs_cent","⑤ gRPC Stream\nTCP 443",EDGE_S(IR)))
    c.append(edge("c6","quay_p","quay_s3","⑥ Geo-Replication\nTCP 443 (S3 API)",DASH_S("#3F51B5")))
    c.append(edge("c7","acm_api","acm_s3","⑦ Failover\nPromotion",DASH_S(MGMT_ORANGE)))
    c.append(edge("c8","dr_gw","dc_broker","⑧ Broker Registration\nTCP 6443",EDGE_S(K8S_BLUE)))

    c.append(cell("t","<b>Complete Inter-Cluster Connection Map — All 8 Connections</b>",350,10,680,30,TITLE_S))
    save("10-inter-cluster-connection-map.drawio",wrap("Inter-Cluster Connections",1400,600,"\n".join(c)))

# ═══════════════════════════════════════
# DIAGRAM 11: ADO Pipeline — Deployment Scope Selection
# ═══════════════════════════════════════
def diagram_11():
    c = []
    c.append(cell("start","ADO Pipeline Trigger",400,40,200,45,COMP_S("#1A237E","#1A237E",1,WHITE)))
    c.append(cell("scope","Deployment Scope?",430,120,140,50,f"rhombus;whiteSpace=wrap;html=1;fillColor=#FF8F00;strokeColor=#FF8F00;fontColor=#FFFFFF;fontSize=12;fontStyle=1;"))
    c.append(edge("se","start","scope","",EDGE_S(DARK)))

    scopes = [
        ("s_dc","dc-only",60,220),("s_dr","dr-only",200,220),("s_dcdr","dc-and-dr",340,220),
        ("s_mdc","mgmt-dc-only",480,220),("s_mdr","mgmt-dr-only",620,220),("s_mgmt","mgmt-clusters",760,220),
        ("s_adc","all-dc",200,310),("s_adr","all-dr",400,310),("s_all","all",600,310),
    ]
    for sid,slbl,sx,sy in scopes:
        c.append(cell(sid,slbl,sx,sy,120,35,COMP_S(DC_GREEN_BG,DC_GREEN,0)))
        c.append(edge(f"e_{sid}","scope",sid,"",EDGE_S(DARK)))

    # Toggles
    c.append(cell("opts","<b>Optional Toggles</b>",40,390,200,180,CLUSTER_S("#607D8B")))
    toggles = [("o1","☐ Enable Submariner",10,45,175,30),("o2","☐ Enable ODF Replication",10,85,180,30),
               ("o3","ODF DR Mode:\nregional-dr / metro-dr",10,125,180,40)]
    for oid,olbl,ox,oy,ow,oh in toggles:
        c.append(cell(oid,olbl,ox,oy,ow,oh,COMP_S(),"opts"))

    c.append(cell("action","Terraform Action:\nplan / apply / destroy",300,430,180,45,COMP_S("#FFF8E1","#F57F17",1,"#F57F17")))

    c.append(cell("t","<b>ADO Pipeline — Deployment Scope Selection</b>",250,5,500,30,TITLE_S))
    save("11-ado-pipeline-scope.drawio",wrap("ADO Pipeline Scope",960,600,"\n".join(c)))

# ═══════════════════════════════════════
# DIAGRAM 12: IPI vs UPI Infrastructure Comparison
# ═══════════════════════════════════════
def diagram_12():
    c = []
    # IPI Side
    c.append(cell("ipi_box","<b>IPI Method</b><br><i>Installer Provisioned Infrastructure</i>",40,60,380,350,CLUSTER_S(DC_GREEN)))
    ipi_items = [
        ("ipi1","Bastion Host: Optional",20,50,340,35),
        ("ipi2","Bootstrap: Managed by installer, auto-removed",20,95,340,35),
        ("ipi3","Load Balancer: Installer-managed keepalived VIPs",20,140,340,35),
        ("ipi4","Node Boot: Automated via BMC/iDRAC virtual media",20,185,340,35),
        ("ipi5","CSR Approval: Automatic",20,230,340,35),
        ("ipi6","install-config: platform: baremetal + BMC creds",20,275,340,35),
    ]
    for iid,ilbl,ix,iy,iw,ih in ipi_items:
        c.append(cell(iid,ilbl,ix,iy,iw,ih,COMP_S(DC_GREEN_BG,DC_GREEN,0),"ipi_box"))

    # UPI Side
    c.append(cell("upi_box","<b>UPI Method</b><br><i>User Provisioned Infrastructure</i>",480,60,380,350,CLUSTER_S(DR_BLUE)))
    upi_items = [
        ("upi1","Bastion Host: REQUIRED — runs installer, serves ignition",20,50,340,35),
        ("upi2","Bootstrap: Operator-provisioned, explicit cleanup",20,95,340,35),
        ("upi3","Load Balancer: External HAProxy — must be pre-configured",20,140,340,35),
        ("upi4","Node Boot: Manual: PXE, ISO, or operator-driven",20,185,340,35),
        ("upi5","CSR Approval: Explicit — oc adm certificate approve",20,230,340,35),
        ("upi6","install-config: platform: none — no hardware mgmt",20,275,340,35),
    ]
    for uid,ulbl,ux,uy,uw,uh in upi_items:
        c.append(cell(uid,ulbl,ux,uy,uw,uh,COMP_S(DR_BLUE_BG,DR_BLUE,0),"upi_box"))

    c.append(cell("t","<b>IPI vs UPI — Infrastructure Comparison</b>",220,15,500,30,TITLE_S))
    save("12-ipi-vs-upi-comparison.drawio",wrap("IPI vs UPI",900,440,"\n".join(c)))

if __name__ == "__main__":
    print("Batch 2: Architecture Extended Diagrams")
    diagram_7(); diagram_8(); diagram_9(); diagram_10(); diagram_11(); diagram_12()
    print("Batch 2 complete! (6 diagrams)")
