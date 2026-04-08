#!/usr/bin/env python3
"""Batch 6: Mgmt DR + Quay Diagrams (7 diagrams)"""
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

def cell(id,v,x,y,w,h,st,p="1"):
    return f'        <mxCell id="{id}" value="{esc(v)}" style="{st}" vertex="1" parent="{p}">\n          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n        </mxCell>'
def edge(id,s,t,v="",st="",p="1"):
    return f'        <mxCell id="{id}" value="{esc(v)}" style="{st if st else ES()}" edge="1" source="{s}" target="{t}" parent="{p}">\n          <mxGeometry relative="1" as="geometry"/>\n        </mxCell>'
def save(fn,xml):
    p=os.path.join(BASE,fn);open(p,'w').write(xml);print(f"  Created: {p}")

# ═══ DIAGRAM 1: Mgmt DR Architecture ═══
def mdr_arch():
    c = []
    c.append(cell("mdr","<b>Management Cluster — DR</b>",40,60,420,300,CL(MO)))
    items=[("dns","DNS",15,50,80,30),("qm","Quay Mirror",110,50,100,30),("lb","HAProxy LB",225,50,90,30),
           ("ocp","OCP Install",330,50,80,30),("odf","ODF Storage",15,100,120,35),("mlb","MetalLB",150,100,90,35),
           ("acm","ACM Standby\nPassive Hub",15,155,160,50),("acs","ACS SecuredCluster\nSensor + Collector",190,155,140,50),
           ("quay","Quay Enterprise\nGeo-Replicated",340,155,80,50),("etcd","etcd Backup",15,225,120,35)]
    for iid,il,ix,iy,iw,ih in items:
        sty = RH() if iid=="ocp" else (CS(MOB,MO,1) if iid=="acm" else (CS(IRB,IR,1) if iid=="acs" else (CS("#E8EAF6","#3F51B5",1) if iid=="quay" else CS())))
        c.append(cell(iid,il,ix,iy,iw,ih,sty,"mdr"))

    c.append(cell("mdc_ref","<b>Management DC (Active)</b>",520,100,200,160,CL(DC_G)))
    c.append(cell("acm_hub","ACM Hub",15,45,170,30,RH(),"mdc_ref"))
    c.append(cell("acs_c","ACS Central",15,85,170,30,CS(IRB,IR,1),"mdc_ref"))
    c.append(cell("quay_dc","Quay Enterprise",15,125,170,30,CS("#E8EAF6","#3F51B5",1),"mdc_ref"))

    c.append(edge("e1","acm_hub","acm","DR failover\npromotion",DS(MO)))
    c.append(edge("e2","acs","acs_c","Reports to",ES(IR)))
    c.append(edge("e3","quay_dc","quay","Geo-replication",DS("#3F51B5")))

    c.append(cell("t","<b>Management DR — Standby Operations Hub</b>",200,15,450,30,TS))
    save("16-mgmt-dr-architecture.drawio",wrap("Mgmt DR Architecture",780,400,"\n".join(c)))

# ═══ DIAGRAM 2: Mgmt DR Inter-Cluster Connectivity ═══
def mdr_conn():
    c = []
    c.append(cell("mdr_f","<b>Mgmt DR — Standby Operations Hub</b>",40,60,350,160,CL(MO)))
    c.append(cell("acm_s","ACM Standby\nPassive MultiClusterHub",15,50,170,45,CS(MOB,MO,1),"mdr_f"))
    c.append(cell("acs_sens","ACS SecuredCluster\nSensor + Collector",200,50,135,45,CS(IRB,IR,1),"mdr_f"))
    c.append(cell("quay_r","Quay Enterprise\nGeo-Replicated",15,110,170,40,CS("#E8EAF6","#3F51B5",1),"mdr_f"))

    c.append(cell("mdc_b","<b>Mgmt DC (Active Hub)</b>",40,270,350,120,CL(DC_G)))
    c.append(cell("acm_a","ACM Hub Active",15,45,140,30,RH(),"mdc_b"))
    c.append(cell("acs_cdc","ACS Central\n:443 gRPC",170,45,140,35,CS(IRB,IR,1),"mdc_b"))
    c.append(cell("quay_p","Quay Enterprise\nPrimary",15,85,140,30,CS("#E8EAF6","#3F51B5",1),"mdc_b"))

    c.append(cell("wl","<b>Workload Clusters</b>",440,120,170,130,CL(WP)))
    c.append(cell("dc_cl","DC Primary",15,45,140,35,CS(DC_GB,DC_G,1),"wl"))
    c.append(cell("dr_cl","DR Secondary",15,90,140,35,CS(DR_BB,DR_B,1),"wl"))

    c.append(edge("c1","acs_sens","acs_cdc","① gRPC Sensor Stream\nTCP 443",ES(IR)))
    c.append(edge("c2","quay_p","quay_r","② Geo-Replication\nS3 API TCP 443",DS("#3F51B5")))
    c.append(edge("c3","acm_a","acm_s","③ Failover Promotion\n(manual trigger)",DS(MO)))
    c.append(edge("c4","acm_s","dc_cl","④ After failover:\nImport + manage",DS(MO)))
    c.append(edge("c5","acm_s","dr_cl","⑤ After failover:\nImport + manage",DS(MO)))

    c.append(cell("t","<b>Inter-Cluster Connectivity — Mgmt DR</b>",130,15,500,30,TS))
    save("17-mgmt-dr-connectivity.drawio",wrap("Mgmt DR Connectivity",680,430,"\n".join(c)))

# ═══ DIAGRAM 3: ACS SecuredCluster Components ═══
def acs_sc():
    c = []
    c.append(cell("dr_acs","<b>Mgmt DR — ACS</b>",40,60,300,150,CL(DR_B)))
    c.append(cell("sensor","Sensor\nWatches K8s API",15,50,130,40,CS(IRB,IR,1),"dr_acs"))
    c.append(cell("collector","Collector\neBPF per-node",160,50,120,40,CS(IRB,IR,0),"dr_acs"))
    c.append(cell("admission","Admission Controller\nPolicy enforcement",60,105,180,35,CS(IRB,IR,0),"dr_acs"))

    c.append(cell("dc_acs","<b>Mgmt DC — ACS Central</b>",420,80,200,80,CL(IR)))
    c.append(cell("central","Central Server",20,50,160,30,CS(IRB,IR,1),"dc_acs"))

    c.append(edge("e1","sensor","central","gRPC",ES(IR)))
    c.append(edge("e2","collector","sensor","",ES(D)))
    c.append(edge("e3","admission","sensor","",ES(D)))

    c.append(cell("t","<b>ACS SecuredCluster Components</b>",150,15,400,25,TS))
    save("18-acs-secured-cluster-components.drawio",wrap("ACS SecuredCluster",680,250,"\n".join(c)))

# ═══ DIAGRAM 4: DR Failover — ACM Promotion Sequence ═══
def dr_failover():
    c = []
    # Actors
    actors=[("op","Operations Team",40,40,140,40,D),("dc_a","Mgmt DC (down)",230,40,140,40,IR),
            ("dr_a","Mgmt DR",420,40,140,40,MO),("wl_dc","DC Primary",610,40,130,40,DC_G),("wl_dr","DR Secondary",790,40,130,40,DR_B)]
    for aid,al,ax,ay,aw,ah,ac in actors:
        c.append(cell(aid,f"<b>{al}</b>",ax,ay,aw,ah,CS(ac,ac,1,W)))

    c.append(cell("fail","❌ DC site failure detected",200,100,200,30,CS(IRB,IR,1,IR)))

    # Phase 1
    c.append(cell("ph1","<b>Phase 1 — ACM Failover</b>",100,150,800,80,f"rounded=1;whiteSpace=wrap;html=1;fillColor={IRB};strokeColor={IR};dashed=1;dashPattern=8 4;fontSize=12;fontStyle=1;fontColor={IR};verticalAlign=top;align=left;spacingTop=5;container=1;collapsible=0;"))
    c.append(cell("s1","Promote ACM Standby → Active Hub",20,35,250,35,CS(MOB,MO,1),"ph1"))
    c.append(cell("s2","Start MultiClusterHub controllers",300,35,250,35,CS(),"ph1"))

    # Phase 2
    c.append(cell("ph2","<b>Phase 2 — Re-Import Clusters</b>",100,250,800,80,f"rounded=1;whiteSpace=wrap;html=1;fillColor={DR_BB};strokeColor={DR_B};dashed=1;dashPattern=8 4;fontSize=12;fontStyle=1;fontColor={DR_B};verticalAlign=top;align=left;spacingTop=5;container=1;collapsible=0;"))
    c.append(cell("s3","Import DR workload (Klusterlet)",20,35,230,35,CS(DR_BB,DR_B,0),"ph2"))
    c.append(cell("s4","Re-import DC workload (if reachable)",280,35,250,35,CS(DC_GB,DC_G,0),"ph2"))

    # Phase 3
    c.append(cell("ph3","<b>Phase 3 — Restore Services</b>",100,350,800,80,f"rounded=1;whiteSpace=wrap;html=1;fillColor={DC_GB};strokeColor={DC_G};dashed=1;dashPattern=8 4;fontSize=12;fontStyle=1;fontColor={DC_G};verticalAlign=top;align=left;spacingTop=5;container=1;collapsible=0;"))
    c.append(cell("s5","ACS Sensor continues locally",20,35,200,35,CS(IRB,IR,0),"ph3"))
    c.append(cell("s6","Quay serves from geo-replica",240,35,200,35,CS("#E8EAF6","#3F51B5",0),"ph3"))
    c.append(cell("s7","Re-apply governance policies",460,35,200,35,CS(MOB,MO,0),"ph3"))

    c.append(cell("done","✅ Mgmt DR is now the active ACM Hub",300,460,380,35,CS(DC_GB,DC_G,1,DC_G)))

    c.append(cell("t","<b>DR Failover — ACM Promotion Sequence</b>",250,5,500,30,TS))
    save("19-dr-failover-acm-promotion.drawio",wrap("DR Failover Sequence",980,520,"\n".join(c)))

# ═══ DIAGRAM 5: Quay Geo-Replication Failover Behavior ═══
def quay_failover():
    c = []
    c.append(cell("normal","<b>Normal Operation</b>",40,60,380,150,CL(DC_G)))
    c.append(cell("dev1","CI/CD Pipeline",15,50,130,35,CS(),"normal"))
    c.append(cell("qdc1","Quay DC\nPrimary",170,50,100,40,CS(DC_GB,DC_G,1),"normal"))
    c.append(cell("qdr1","Quay DR\nReplica",170,100,100,40,CS(DR_BB,DR_B,1),"normal"))
    c.append(cell("node1","DR Workers",290,100,80,35,CS(),"normal"))
    c.append(edge("ne1","dev1","qdc1","push",ES(D),"normal"))
    c.append(edge("ne2","qdc1","qdr1","geo-replicate",ES(DR_B),"normal"))
    c.append(edge("ne3","qdr1","node1","pull local",ES(DR_B),"normal"))

    c.append(cell("failover","<b>After DC Failure</b>",480,60,300,150,CL(MO)))
    c.append(cell("dev2","CI/CD Pipeline",15,50,130,35,CS(),"failover"))
    c.append(cell("qdr2","Quay DR\nPromoted",170,50,110,40,CS(MOB,MO,1),"failover"))
    c.append(cell("node2","All Workers",170,105,110,35,CS(),"failover"))
    c.append(edge("fe1","dev2","qdr2","push",ES(D),"failover"))
    c.append(edge("fe2","qdr2","node2","serve locally",ES(MO),"failover"))

    c.append(edge("trans","normal","failover","DC Failure",DS(IR)))

    c.append(cell("t","<b>Quay Geo-Replication — Normal vs Failover</b>",180,15,500,30,TS))
    save("20-quay-geo-replication-failover.drawio",wrap("Quay Failover",840,250,"\n".join(c)))

# ═══ DIAGRAM 6: Quay Geo-Replication Flow (Sequence) ═══
def quay_geo_seq():
    c = []
    actors=[("dev","Developer /\nCI Pipeline",40,50,120,50,"#455A64"),("qdc","Quay DC\n(Primary)",220,50,120,50,DC_G),
            ("s3","Shared S3\nStorage",400,50,120,50,"#00695C"),("qdr","Quay DR\n(Replica)",580,50,120,50,DR_B),
            ("node","DR Worker\nNode",760,50,120,50,D)]
    for aid,al,ax,ay,aw,ah,ac in actors:
        c.append(cell(aid,f"<b>{al}</b>",ax,ay,aw,ah,CS(ac,ac,1,W)))

    steps=[("st1","① docker push image:tag",80,130,220,30,D),("st2","② Clair vulnerability scan",220,170,180,30,IR),
           ("st3","③ Store image layers + manifest",280,210,200,30,"#00695C"),("st4","④ Geo-replication sync",440,250,200,30,DR_B),
           ("st5","⑤ Update local metadata",580,290,180,30,DR_B),("st6","⑥ docker pull image:tag",660,330,200,30,D)]
    for sid,sl,sx,sy,sw,sh,sc in steps:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(W,sc,0,sc)))

    c.append(cell("note","Image available in DR\nNo WAN traffic for pulls",580,370,200,40,CS("#FFF8E1","#F57F17",0,"#F57F17")))

    c.append(cell("t","<b>Quay Enterprise Geo-Replication Flow</b>",250,10,450,30,TS))
    save("21-quay-geo-replication-flow.drawio",wrap("Quay Geo-Rep Flow",940,430,"\n".join(c)))

# ═══ DIAGRAM 7: ACM DR Applications (DRPolicy) ═══
def acm_dr_apps():
    c = []
    c.append(cell("hub","<b>ACM Hub</b>\n(Mgmt DC)",40,60,160,50,CS(MOB,MO,1,MO)))
    c.append(cell("drp","DRPolicy\ndc-dr-policy",260,40,150,45,CS(DC_GB,DC_G,1)))
    c.append(cell("dc_cl","DRCluster\ndc-primary",260,110,150,40,CS(DC_GB,DC_G,0)))
    c.append(cell("dr_cl","DRCluster\ndr-secondary",260,170,150,40,CS(DR_BB,DR_B,0)))
    c.append(cell("drpc","DRPlacementControl\nper-application",460,90,180,50,CS(WPB,WP,1)))

    c.append(edge("e1","hub","drp","",ES(MO)))
    c.append(edge("e2","drp","dc_cl","",ES(DC_G)))
    c.append(edge("e3","drp","dr_cl","",ES(DR_B)))
    c.append(edge("e4","hub","drpc","",ES(MO)))
    c.append(edge("e5","drpc","dc_cl","Normal: Active",ES(DC_G)))
    c.append(edge("e6","drpc","dr_cl","Failover: Promote",DS(DR_B)))

    c.append(cell("t","<b>ACM DR Applications — DRPolicy & DRPlacementControl</b>",120,5,500,25,TS))
    save("22-acm-dr-applications.drawio",wrap("ACM DR Applications",700,250,"\n".join(c)))

if __name__=="__main__":
    print("Batch 6: Mgmt DR + Quay Diagrams")
    mdr_arch();mdr_conn();acs_sc();dr_failover();quay_failover();quay_geo_seq();acm_dr_apps()
    print("Batch 6 complete! (7 diagrams)")
