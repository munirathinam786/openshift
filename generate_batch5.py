#!/usr/bin/env python3
"""Batch 5: DR Secondary + Mgmt DC Diagrams (7 diagrams)"""
import os, html

BASE = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs/docs/diagrams/clusters"
os.makedirs(BASE, exist_ok=True)

RH_RED="#EE0000";RH_DARK="#CC0000";DC_G="#2E7D32";DC_GB="#E8F5E9";DR_B="#1565C0";DR_BB="#E3F2FD"
MO="#EF6C00";MOB="#FFF3E0";WP="#7B1FA2";WPB="#F3E5F5";IR="#C62828";IRB="#FCE4EC"
W="#FFFFFF";D="#333333";KB="#326CE5"

def esc(s): return html.escape(s)
def wrap(n,w,h,cx):
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net" modified="2026-04-07T00:00:00.000Z" agent="GitHub Copilot" version="24.0.0" type="device">\n  <diagram id="d1" name="{esc(n)}">\n    <mxGraphModel dx="1422" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{w}" pageHeight="{h}" math="0" shadow="1">\n      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n{cx}\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>'
CL=lambda c,s=None:f"swimlane;startSize=35;fillColor={c};fontColor=#FFFFFF;strokeColor={s or c};rounded=1;shadow=1;fontSize=13;fontStyle=1;whiteSpace=wrap;html=1;container=1;collapsible=0;"
CS=lambda f=W,s=D,b=0,fc=D:f"rounded=1;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize=11;fontStyle={b};fontColor={fc};shadow=1;arcSize=10;"
RH=lambda:CS(RH_RED,RH_DARK,1,W)
ES=lambda c=D:f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={c};fontSize=10;fontColor={c};labelBackgroundColor=#FFFFFF;strokeWidth=2;"
DS=lambda c=D:f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={c};fontSize=10;fontColor={c};dashed=1;dashPattern=8 4;labelBackgroundColor=#FFFFFF;strokeWidth=2;"
TS="text;html=1;align=center;verticalAlign=middle;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"
SS=lambda c:f"rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=12 8;fillColor=none;fontSize=16;fontStyle=1;verticalAlign=top;align=left;spacingTop=8;spacingLeft=12;container=1;collapsible=0;strokeWidth=3;strokeColor={c};"

def cell(id,v,x,y,w,h,st,p="1"):
    return f'        <mxCell id="{id}" value="{esc(v)}" style="{st}" vertex="1" parent="{p}">\n          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n        </mxCell>'
def edge(id,s,t,v="",st="",p="1"):
    return f'        <mxCell id="{id}" value="{esc(v)}" style="{st if st else ES()}" edge="1" source="{s}" target="{t}" parent="{p}">\n          <mxGeometry relative="1" as="geometry"/>\n        </mxCell>'
def save(fn,xml):
    p=os.path.join(BASE,fn);open(p,'w').write(xml);print(f"  Created: {p}")

# ═══ DR SECONDARY DIAGRAMS ═══

# DIAGRAM 1: DR Secondary Architecture
def dr_arch():
    c = []
    c.append(cell("dr_cl","<b>DR Secondary Workload Cluster</b>",40,60,560,330,CL(DR_B)))
    items=[("dns","DNS Validation",20,50,120,35),("qm","Quay Mirror",160,50,110,35),("lb","HAProxy LB",290,50,100,35),
           ("ocp","OCP Baremetal",420,50,120,40),("nfd","NFD Operator",20,105,110,35),("gpu","GPU Operator",150,105,110,35),
           ("odf","ODF Operator",280,105,110,35),("sm","Service Mesh",20,155,110,35),("sl","Serverless",150,155,110,35),
           ("metallb","MetalLB",280,155,100,35),("sriov","SR-IOV",400,155,100,35),
           ("ai","OpenShift AI",20,210,120,40),("gpum","GPU Monitoring",160,210,120,35),
           ("sub","Submariner\nAgent",20,265,130,45),("odfdr","ODF DR\nReplication",170,265,130,45)]
    for iid,il,ix,iy,iw,ih in items:
        sty = RH() if iid in ("ocp","ai") else (CS("#E3F2FD",KB,1,KB) if iid=="sub" else (CS("#E0F2F1","#00695C",1) if iid in ("odf","odfdr") else CS()))
        c.append(cell(iid,il,ix,iy,iw,ih,sty,"dr_cl"))

    c.append(cell("dc","<b>DC Primary</b>",660,100,180,130,CL(DC_G)))
    c.append(cell("broker","Submariner\nBroker",15,45,150,40,CS("#E3F2FD",KB,1,KB),"dc"))
    c.append(cell("odf_dc","ODF Storage",15,95,150,30,CS("#E0F2F1","#00695C",1),"dc"))

    c.append(edge("de1","sub","broker","IPsec Tunnel",ES(KB)))
    c.append(edge("de2","odfdr","odf_dc","RBD Mirroring",ES("#00695C")))

    edges=[("dns","qm"),("qm","lb"),("lb","ocp"),("ocp","nfd"),("nfd","gpu"),("gpu","ai"),("odf","ai"),("sm","ai")]
    for i,(s,t) in enumerate(edges):
        c.append(edge(f"fe{i}",s,t,"",ES(D)))

    c.append(cell("t","<b>DR Secondary Workload Cluster Architecture</b>",180,15,500,30,TS))
    save("09-dr-secondary-architecture.drawio",wrap("DR Secondary Architecture",880,430,"\n".join(c)))

# DIAGRAM 2: DR Secondary Connectivity
def dr_conn():
    c = []
    c.append(cell("dr_s","<b>DR Secondary Workload Cluster</b>",40,60,350,290,CL(DR_B)))
    c.append(cell("ocp_dr","OCP 4.15 Baremetal",20,50,150,40,RH(),"dr_s"))
    c.append(cell("sub_a","Submariner Agent+Gateway\n:4500 UDP",20,105,180,45,CS("#E3F2FD",KB,1,KB),"dr_s"))
    c.append(cell("odf_dr","ODF Ceph Storage\nRBD Mirror (Target)\n:6789 / :3300",20,165,190,55,CS("#E0F2F1","#00695C",1),"dr_s"))

    c.append(cell("dc_p","<b>DC Primary</b>",440,60,200,150,CL(DC_G)))
    c.append(cell("dc_bk","Submariner Broker\n:6443 / :8443",15,45,170,40,CS("#E3F2FD",KB,1,KB),"dc_p"))
    c.append(cell("dc_gw","Submariner Gateway",15,95,170,30,CS("#E3F2FD",KB,0,KB),"dc_p"))
    c.append(cell("dc_odf","ODF Ceph (Source)",15,135,170,25,CS("#E0F2F1","#00695C",1),"dc_p"))

    c.append(cell("mdc","<b>Mgmt DC</b>",440,240,200,100,CL(MO)))
    c.append(cell("acm","ACM Hub\nKlusterlet",15,45,90,40,RH(),"mdc"))
    c.append(cell("acs","ACS Central\nSensor",120,45,70,40,CS(IRB,IR,1),"mdc"))

    c.append(cell("mdr","<b>Mgmt DR</b>",440,370,200,60,CL(MO)))
    c.append(cell("acm_dr","ACM Standby\n(Failover Hub)",15,30,170,25,CS(MOB,MO,1),"mdr"))

    c.append(edge("e1","sub_a","dc_bk","① Broker Registration\nTCP 6443",ES(KB)))
    c.append(edge("e2","sub_a","dc_gw","② IPsec Tunnel\nUDP 4500 + ESP",ES(KB)))
    c.append(edge("e3","dc_odf","odf_dr","③ RBD Writes Replicated\nTCP 6789, 3300",ES("#00695C")))
    c.append(edge("e4","acm","ocp_dr","④ Klusterlet Import\nTCP 6443",ES(MO)))
    c.append(edge("e5","acs","ocp_dr","⑤ SecuredCluster Sensor",ES(IR)))
    c.append(edge("e6","acm_dr","ocp_dr","⑥ Failover: re-import",DS(MO)))

    c.append(cell("t","<b>Cross-Cluster Connectivity — DR Secondary</b>",140,15,500,30,TS))
    save("10-dr-secondary-connectivity.drawio",wrap("DR Secondary Connectivity",700,460,"\n".join(c)))

# ═══ MGMT DC DIAGRAMS ═══

# DIAGRAM 3: Mgmt DC Architecture
def mdc_arch():
    c = []
    c.append(cell("mdc","<b>Management Cluster — DC</b>",40,60,420,320,CL(MO)))
    items=[("dns","DNS",15,50,80,30),("qm","Quay Mirror",110,50,100,30),("lb","HAProxy LB",225,50,90,30),
           ("ocp","OCP Install",330,50,80,30),("odf","ODF Storage",15,100,120,35),("metallb","MetalLB",150,100,90,35),
           ("acm","ACM Hub\nMultiClusterHub",15,155,160,50),("acs","ACS Central\nVulnerability Scanning",190,155,130,50),
           ("quay","Quay Enterprise\nContainer Registry",330,155,80,50),("etcd","etcd Backup",15,225,120,35)]
    for iid,il,ix,iy,iw,ih in items:
        sty = RH() if iid in ("ocp","acm") else (CS(IRB,IR,1) if iid=="acs" else (CS("#E8EAF6","#3F51B5",1) if iid=="quay" else CS()))
        c.append(cell(iid,il,ix,iy,iw,ih,sty,"mdc"))

    c.append(cell("managed","<b>Managed Clusters</b>",520,150,180,130,CL(WP)))
    c.append(cell("dc_cl","DC Primary\n(Workload)",15,45,150,35,CS(DC_GB,DC_G,1),"managed"))
    c.append(cell("dr_cl","DR Secondary\n(Workload)",15,90,150,35,CS(DR_BB,DR_B,1),"managed"))

    c.append(cell("mdr_ref","Mgmt DR\n(Standby)",520,320,180,40,CS(MOB,MO,1)))

    c.append(edge("me1","acm","dc_cl","Import & Manage",ES(MO)))
    c.append(edge("me2","acm","dr_cl","Import & Manage",ES(MO)))
    c.append(edge("me3","acm","mdr_ref","Failover",DS(MO)))
    c.append(edge("me4","acs","dc_cl","Security Policies",ES(IR)))
    c.append(edge("me5","acs","dr_cl","Security Policies",ES(IR)))

    c.append(cell("t","<b>Management DC — Architecture</b>",200,15,400,30,TS))
    save("11-mgmt-dc-architecture.drawio",wrap("Mgmt DC Architecture",760,400,"\n".join(c)))

# DIAGRAM 4: Mgmt DC Inter-Cluster Connectivity (11 connections)
def mdc_conn():
    c = []
    c.append(cell("mdc_f","<b>Mgmt DC — Central Operations Hub</b>",40,60,380,200,CL(MO)))
    c.append(cell("acm_h","ACM Hub\nKlusterlet Controller",15,50,160,40,RH(),"mdc_f"))
    c.append(cell("acs_c","ACS Central\n:443 gRPC",190,50,130,40,CS(IRB,IR,1),"mdc_f"))
    c.append(cell("quay_c","Quay Enterprise\n:443",15,105,130,40,CS("#E8EAF6","#3F51B5",1),"mdc_f"))
    c.append(cell("obs","ACM Observability\nThanos :10902",190,105,150,40,CS("#FFF8E1","#F57F17",0),"mdc_f"))

    c.append(cell("dc_wl","<b>DC Primary Workload</b>",480,60,220,160,CL(DC_G)))
    c.append(cell("dc_api","API Server :6443",15,45,130,30,CS(),"dc_wl"))
    c.append(cell("dc_kl","Klusterlet Agent",15,85,130,25,CS(),"dc_wl"))
    c.append(cell("dc_sens","ACS Sensor",15,120,100,25,CS(IRB,IR,0),"dc_wl"))

    c.append(cell("dr_wl","<b>DR Secondary Workload</b>",480,250,220,160,CL(DR_B)))
    c.append(cell("dr_api","API Server :6443",15,45,130,30,CS(),"dr_wl"))
    c.append(cell("dr_kl","Klusterlet Agent",15,85,130,25,CS(),"dr_wl"))
    c.append(cell("dr_sens","ACS Sensor",15,120,100,25,CS(IRB,IR,0),"dr_wl"))

    c.append(cell("mdr_b","<b>Mgmt DR (Standby)</b>",40,310,380,130,CL(IR)))
    c.append(cell("acm_s","ACM Standby",15,45,120,30,CS(MOB,MO,1),"mdr_b"))
    c.append(cell("acs_sc","ACS SecuredCluster\nSensor :443",150,45,140,35,CS(IRB,IR,1),"mdr_b"))
    c.append(cell("quay_s","Quay Enterprise\n(Geo-Replicated)",15,90,160,30,CS("#E8EAF6","#3F51B5",1),"mdr_b"))

    c.append(edge("c1","acm_h","dc_api","① Import+Policies TCP 6443",ES(MO)))
    c.append(edge("c2","acm_h","dr_api","② Import+Policies TCP 6443",ES(MO)))
    c.append(edge("c3","dc_kl","acm_h","③ Status Reports TCP 443",ES(D)))
    c.append(edge("c4","dr_kl","acm_h","④ Status Reports",ES(D)))
    c.append(edge("c7","dc_sens","acs_c","⑦ gRPC Telemetry TCP 443",ES(IR)))
    c.append(edge("c8","dr_sens","acs_c","⑧ gRPC Telemetry",ES(IR)))
    c.append(edge("c9","acs_sc","acs_c","⑨ gRPC Telemetry",ES(IR)))
    c.append(edge("c10","quay_c","quay_s","⑩ Geo-Replication S3 :443",DS("#3F51B5")))
    c.append(edge("c11","acm_h","acm_s","⑪ DR Failover Promotion",DS(MO)))

    c.append(cell("t","<b>Inter-Cluster Connectivity — Mgmt DC (11 Connections)</b>",150,15,550,30,TS))
    save("12-mgmt-dc-connectivity.drawio",wrap("Mgmt DC Connectivity",760,480,"\n".join(c)))

# DIAGRAM 5: ACM Observability Data Flow
def acm_obs():
    c = []
    c.append(cell("managed","<b>Managed Clusters</b>",40,80,200,120,CL(WP)))
    c.append(cell("p1","DC Prometheus",15,50,170,30,CS(DC_GB,DC_G,0),"managed"))
    c.append(cell("p2","DR Prometheus",15,90,170,30,CS(DR_BB,DR_B,0),"managed"))

    c.append(cell("obs_stack","<b>ACM Observability Stack (Mgmt DC)</b>",320,40,460,200,CL(DC_G)))
    c.append(cell("collect","Metrics Collector\nremote-write",15,50,140,45,CS(),"obs_stack"))
    c.append(cell("thanos_r","Thanos Receive",175,50,130,40,CS(),"obs_stack"))
    c.append(cell("thanos_s","Thanos Store",175,110,130,40,CS(),"obs_stack"))
    c.append(cell("s3_b","S3 Bucket\n(ODF RGW)",330,110,120,40,CS("#E0F2F1","#00695C",0),"obs_stack"))
    c.append(cell("grafana","Grafana\nDashboards",330,50,120,40,CS("#FFF8E1","#F57F17",1),"obs_stack"))

    c.append(edge("oe1","p1","collect","remote-write",ES(DC_G)))
    c.append(edge("oe2","p2","collect","remote-write",ES(DR_B)))
    c.append(edge("oe3","collect","thanos_r","",ES(D)))
    c.append(edge("oe4","thanos_r","thanos_s","",ES(D)))
    c.append(edge("oe5","thanos_s","s3_b","",ES(D)))
    c.append(edge("oe6","thanos_r","grafana","",ES("#F57F17")))

    c.append(cell("t","<b>ACM Observability Data Flow</b>",280,10,350,25,TS))
    save("13-acm-observability-flow.drawio",wrap("ACM Observability",840,280,"\n".join(c)))

# DIAGRAM 6: ACS Central Security Stack
def acs_stack():
    c = []
    c.append(cell("acs_d","<b>ACS Central — Security Stack</b>",40,60,320,180,CL(IR)))
    c.append(cell("central","Central Server",15,50,130,40,CS(IRB,IR,1),"acs_d"))
    c.append(cell("scanner","Scanner\n2-5 replicas",160,50,140,40,CS(IRB,IR,0),"acs_d"))
    c.append(cell("db","Central DB\n100Gi PVC",15,110,130,40,CS(),"acs_d"))

    c.append(cell("remotes","<b>Remote Clusters</b>",420,60,200,180,CL(DR_B)))
    c.append(cell("s1","DC Primary\nSecuredCluster",15,50,170,35,CS(DC_GB,DC_G,0),"remotes"))
    c.append(cell("s2","DR Secondary\nSecuredCluster",15,95,170,35,CS(DR_BB,DR_B,0),"remotes"))
    c.append(cell("s3","Mgmt DR\nSecuredCluster",15,140,170,35,CS(MOB,MO,0),"remotes"))

    c.append(edge("ae1","central","scanner","",ES(IR)))
    c.append(edge("ae2","central","db","",ES(D)))
    c.append(edge("ae3","s1","central","Reports",ES(DC_G)))
    c.append(edge("ae4","s2","central","Reports",ES(DR_B)))
    c.append(edge("ae5","s3","central","Reports",ES(MO)))

    c.append(cell("t","<b>ACS Central Security Stack</b>",180,15,350,25,TS))
    save("14-acs-central-security-stack.drawio",wrap("ACS Central Stack",680,280,"\n".join(c)))

# DIAGRAM 7: ACM Hub Components
def acm_hub():
    c = []
    c.append(cell("acm_d","<b>ACM Hub Components</b>",40,60,450,160,CL(RH_RED)))
    c.append(cell("mch","MultiClusterHub CR",15,50,160,40,RH(),"acm_d"))
    c.append(cell("gov","Governance\nPolicy Engine",190,50,120,40,CS(DC_GB,DC_G,0),"acm_d"))
    c.append(cell("app","App Lifecycle\nGitOps",15,105,120,40,CS(DR_BB,DR_B,0),"acm_d"))
    c.append(cell("obs","Observability\n(optional)",150,105,120,40,CS("#FFF8E1","#F57F17",0),"acm_d"))
    c.append(cell("search","Search\nCross-Cluster",290,105,130,40,CS(WPB,WP,0),"acm_d"))

    c.append(edge("he1","mch","gov","",ES(D)))
    c.append(edge("he2","mch","app","",ES(D)))
    c.append(edge("he3","mch","obs","",ES(D)))
    c.append(edge("he4","mch","search","",ES(D)))

    c.append(cell("t","<b>ACM Hub — Internal Components</b>",120,15,350,25,TS))
    save("15-acm-hub-components.drawio",wrap("ACM Hub Components",550,260,"\n".join(c)))

if __name__=="__main__":
    print("Batch 5: DR Secondary + Mgmt DC Diagrams")
    dr_arch();dr_conn();mdc_arch();mdc_conn();acm_obs();acs_stack();acm_hub()
    print("Batch 5 complete! (7 diagrams)")
