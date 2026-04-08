#!/usr/bin/env python3
"""Batch 11: Generate draw.io files for ALL 18 remaining un-replaced mermaid diagrams."""
import os, html

ROOT = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs/docs/diagrams"

RH_RED="#EE0000";RH_DARK="#CC0000";DC_G="#2E7D32";DC_GB="#E8F5E9";DR_B="#1565C0";DR_BB="#E3F2FD"
MO="#EF6C00";MOB="#FFF3E0";WP="#7B1FA2";WPB="#F3E5F5";IR="#C62828";IRB="#FCE4EC"
W="#FFFFFF";D="#333333";KB="#326CE5"

def esc(s): return html.escape(s)
def wrap(n,w,h,cx):
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net" modified="2026-04-07T00:00:00.000Z" agent="GitHub Copilot" version="24.0.0" type="device">\n  <diagram id="d1" name="{esc(n)}">\n    <mxGraphModel dx="1422" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{w}" pageHeight="{h}" math="0" shadow="0">\n      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n{cx}\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>'
CL=lambda c,s=None:f"swimlane;startSize=35;fillColor={c};fontColor=#FFFFFF;strokeColor={s or c};rounded=1;fontSize=13;fontStyle=1;whiteSpace=wrap;html=1;container=1;collapsible=0;"
CS=lambda f=W,s=D,b=0,fc=D:f"rounded=1;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize=11;fontStyle={b};fontColor={fc};arcSize=10;"
RH=lambda:CS(RH_RED,RH_DARK,1,W)
ES=lambda c=D:f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={c};fontSize=10;fontColor={c};labelBackgroundColor=#FFFFFF;strokeWidth=2;"
DS=lambda c=D:f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={c};fontSize=10;fontColor={c};dashed=1;dashPattern=8 4;labelBackgroundColor=#FFFFFF;strokeWidth=2;"
TS="text;html=1;align=center;verticalAlign=middle;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"

def cell(id,v,x,y,w,h,st,p="1"):
    return f'        <mxCell id="{id}" value="{esc(v)}" style="{st}" vertex="1" parent="{p}">\n          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n        </mxCell>'
def edge(id,s,t,v="",st="",p="1"):
    return f'        <mxCell id="{id}" value="{esc(v)}" style="{st if st else ES()}" edge="1" source="{s}" target="{t}" parent="{p}">\n          <mxGeometry relative="1" as="geometry"/>\n        </mxCell>'
def save(cat,fn,xml):
    d=os.path.join(ROOT,cat);os.makedirs(d,exist_ok=True);p=os.path.join(d,fn);open(p,'w').write(xml);print(f"  {p}")

# ═══ 1: Multi-Cluster Protocol & Port Connectivity Map ═══
def proto_port_map():
    c = []
    c.append(cell("t","<b>Multi-Cluster Protocol &amp; Port Connectivity Map</b>",200,10,600,30,TS))
    # DC Site
    c.append(cell("dc_site","<b>DC Site</b>",20,60,440,340,f"rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=12 8;fillColor=none;fontSize=14;fontStyle=1;verticalAlign=top;align=left;spacingTop=5;spacingLeft=8;container=1;collapsible=0;strokeWidth=2;strokeColor={DC_G};"))
    c.append(cell("dc_wl","<b>DC Primary Workload</b>",15,35,195,175,CL(DC_G),"dc_site"))
    c.append(cell("dc_api","API Server :6443",10,45,175,25,CS(),"dc_wl"))
    c.append(cell("dc_brkr","Submariner Broker :8443",10,75,175,25,CS(),"dc_wl"))
    c.append(cell("dc_gw","Submariner GW :4500/UDP",10,105,175,25,CS(),"dc_wl"))
    c.append(cell("dc_odf","ODF Ceph RBD Mirror",10,135,175,25,CS(),"dc_wl"))
    c.append(cell("mgmt_dc","<b>Mgmt DC</b>",230,35,195,175,CL(MO),"dc_site"))
    c.append(cell("acm_api","ACM Hub API :443",10,45,175,25,CS(),"mgmt_dc"))
    c.append(cell("acs_cent","ACS Central :443 gRPC",10,75,175,25,CS(),"mgmt_dc"))
    c.append(cell("quay_p","Quay Enterprise :443",10,105,175,25,CS(),"mgmt_dc"))
    c.append(cell("acm_obs","ACM Observability :10902",10,135,175,25,CS(),"mgmt_dc"))
    # DR Site
    c.append(cell("dr_site","<b>DR Site</b>",520,60,440,340,f"rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=12 8;fillColor=none;fontSize=14;fontStyle=1;verticalAlign=top;align=left;spacingTop=5;spacingLeft=8;container=1;collapsible=0;strokeWidth=2;strokeColor={DR_B};"))
    c.append(cell("dr_wl","<b>DR Secondary Workload</b>",15,35,195,145,CL(DR_B),"dr_site"))
    c.append(cell("dr_api","API Server :6443",10,45,175,25,CS(),"dr_wl"))
    c.append(cell("dr_gw","Submariner GW :4500/UDP",10,75,175,25,CS(),"dr_wl"))
    c.append(cell("dr_odf","ODF Ceph RBD Mirror",10,105,175,25,CS(),"dr_wl"))
    c.append(cell("mgmt_dr","<b>Mgmt DR</b>",230,35,195,145,CL(MO),"dr_site"))
    c.append(cell("acm_s","ACM Standby :443",10,45,175,25,CS(),"mgmt_dr"))
    c.append(cell("acs_sc","ACS SecuredCluster :443",10,75,175,25,CS(),"mgmt_dr"))
    c.append(cell("quay_s","Quay Enterprise :443",10,105,175,25,CS(),"mgmt_dr"))
    # Edges
    c.append(edge("pe1","dc_gw","dr_gw","① IPsec UDP 4500+500",ES(KB)))
    c.append(edge("pe2","dc_odf","dr_odf","② RBD Mirroring TCP 6789",ES("#00695C")))
    c.append(edge("pe3","acm_api","dc_api","③ Klusterlet TCP 443",ES(MO)))
    c.append(edge("pe4","acm_api","dr_api","④ Klusterlet TCP 443",ES(MO)))
    c.append(edge("pe5","acs_sc","acs_cent","⑤ gRPC TCP 443",ES(IR)))
    c.append(edge("pe6","quay_p","quay_s","⑥ Geo-Repl S3 :443",DS(WP)))
    c.append(edge("pe7","acm_api","acm_s","⑦ Failover Promotion",DS(MO)))
    c.append(edge("pe8","dr_gw","dc_brkr","⑧ Broker Reg TCP 6443",ES(KB)))
    save("architecture","13-protocol-port-map.drawio",wrap("Protocol Port Map",1000,440,"\n".join(c)))

# ═══ 2: ACM Hub Cluster Import Topology ═══
def acm_import_topo():
    c = []
    c.append(cell("hub","ACM Hub\n(Mgmt DC)",40,80,160,50,CS(MOB,MO,1)))
    c.append(cell("dc","DC Primary\nManagedCluster",320,40,160,50,CS(DC_GB,DC_G,1,DC_G)))
    c.append(cell("dr","DR Secondary\nManagedCluster",320,130,160,50,CS(DR_BB,DR_B,1,DR_B)))
    c.append(cell("set","ManagedClusterSet\nocp-workload-clusters",320,220,180,40,CS(MOB,MO,0)))
    c.append(edge("e1","hub","dc","Import",ES(MO)))
    c.append(edge("e2","hub","dr","Import",ES(MO)))
    c.append(edge("e3","hub","set","",ES(D)))
    c.append(edge("e4","set","dc","",DS(DC_G)))
    c.append(edge("e5","set","dr","",DS(DR_B)))
    c.append(cell("t","<b>ACM Hub Cluster Import Topology</b>",120,10,350,30,TS))
    save("clusters","23-acm-import-topology.drawio",wrap("ACM Import Topology",540,290,"\n".join(c)))

# ═══ 3: ACM DR Application Failover ═══
def acm_dr_failover():
    c = []
    c.append(cell("hub","ACM Hub\n(Mgmt DC)",40,60,150,50,CS(MOB,MO,1)))
    c.append(cell("drp","DRPolicy\ndc-dr-policy",260,40,160,45,CS(DC_GB,DC_G,1)))
    c.append(cell("dc_cl","DRCluster\ndc-primary",260,110,140,40,CS(DC_GB,DC_G,0,DC_G)))
    c.append(cell("dr_cl","DRCluster\ndr-secondary",260,170,140,40,CS(DR_BB,DR_B,0,DR_B)))
    c.append(cell("drpc","DRPlacementControl\nper-application",500,60,180,50,CS(MOB,MO,1)))
    c.append(edge("e1","hub","drp","",ES(D)))
    c.append(edge("e2","drp","dc_cl","",ES(DC_G)))
    c.append(edge("e3","drp","dr_cl","",ES(DR_B)))
    c.append(edge("e4","hub","drpc","",ES(MO)))
    c.append(edge("e5","drpc","dc_cl","Normal: Active",ES(DC_G)))
    c.append(edge("e6","drpc","dr_cl","Failover: Promote",DS(DR_B)))
    c.append(cell("t","<b>ACM DR Application Failover</b>",180,5,350,30,TS))
    save("clusters","24-acm-dr-application-failover.drawio",wrap("ACM DR App Failover",720,240,"\n".join(c)))

# ═══ 4: Quay Geo-Replication Failover Behavior ═══
def quay_failover_behavior():
    c = []
    c.append(cell("gn","<b>Normal Operation</b>",30,60,300,120,CL(DC_G)))
    c.append(cell("dev1","CI/CD Pipeline",15,50,110,30,CS(),"gn"))
    c.append(cell("qdc1","Quay DC\nPrimary",150,40,120,40,CS(DC_GB,DC_G,1),"gn"))
    c.append(cell("qdr1","Quay DR\nReplica",150,85,120,30,CS(DR_BB,DR_B,0),"gn"))
    c.append(edge("ne1","dev1","qdc1","push",ES(D),"gn"))
    c.append(edge("ne2","qdc1","qdr1","geo-replicate",DS(DR_B),"gn"))

    c.append(cell("gf","<b>After DC Failure</b>",380,60,280,120,CL(MO)))
    c.append(cell("dev2","CI/CD Pipeline",15,50,110,30,CS(),"gf"))
    c.append(cell("qdr2","Quay DR\nPromoted",150,50,110,40,CS(MOB,MO,1),"gf"))
    c.append(edge("fe1","dev2","qdr2","push",ES(D),"gf"))
    c.append(edge("failarrow","gn","gf","DC Failure",DS(IR)))
    c.append(cell("t","<b>Quay Geo-Replication Failover Behavior</b>",150,10,400,30,TS))
    save("clusters","25-quay-failover-behavior.drawio",wrap("Quay Failover",700,220,"\n".join(c)))

# ═══ 5: ACM Hub Post-Failover Re-Import ═══
def acm_reimport():
    c = []
    c.append(cell("hub","ACM Hub\n(Mgmt DR — Promoted)",40,80,200,50,CS(MOB,MO,1)))
    c.append(cell("dc","DC Primary\nManagedCluster",340,50,160,50,CS(DC_GB,DC_G,1,DC_G)))
    c.append(cell("dr","DR Secondary\nManagedCluster",340,130,160,50,CS(DR_BB,DR_B,1,DR_B)))
    c.append(edge("e1","hub","dc","Re-Import",ES(MO)))
    c.append(edge("e2","hub","dr","Re-Import",ES(MO)))
    c.append(cell("t","<b>ACM Hub Post-Failover Re-Import</b>",120,15,350,30,TS))
    save("clusters","26-acm-post-failover-reimport.drawio",wrap("ACM Re-Import",540,210,"\n".join(c)))

# ═══ 6: ADO Pipeline Multi-Cluster Deployment Topology ═══
def ado_deploy_topo():
    c = []
    c.append(cell("pipe","azure-pipelines.yml\nterraform apply",300,40,200,45,CS(MO,MO,1,W)))
    # DC Site
    c.append(cell("dc_site","<b>DC Site</b>",40,140,340,200,f"rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=12 8;fillColor=none;fontSize=14;fontStyle=1;verticalAlign=top;align=left;spacingTop=5;container=1;collapsible=0;strokeWidth=2;strokeColor={DC_G};"))
    c.append(cell("dc","<b>DC Primary</b>",15,35,145,100,CL(DC_G),"dc_site"))
    c.append(cell("dc_ocp","OCP 4.15 + AI",10,40,125,20,CS(),"dc"))
    c.append(cell("dc_sub","Submariner Broker",10,65,125,20,CS(),"dc"))
    c.append(cell("dc_odf","ODF (RBD Source)",10,90,125,20,CS(),"dc"))
    c.append(cell("mdc","<b>Mgmt DC</b>",180,35,145,100,CL(MO),"dc_site"))
    c.append(cell("acm_h","ACM Hub",10,40,125,20,CS(),"mdc"))
    c.append(cell("acs_c","ACS Central",10,65,125,20,CS(),"mdc"))
    c.append(cell("quay_dc","Quay Enterprise",10,90,125,20,CS(),"mdc"))
    # DR Site
    c.append(cell("dr_site","<b>DR Site</b>",420,140,340,200,f"rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=12 8;fillColor=none;fontSize=14;fontStyle=1;verticalAlign=top;align=left;spacingTop=5;container=1;collapsible=0;strokeWidth=2;strokeColor={DR_B};"))
    c.append(cell("dr","<b>DR Secondary</b>",15,35,145,100,CL(DR_B),"dr_site"))
    c.append(cell("dr_ocp","OCP 4.15 + AI",10,40,125,20,CS(),"dr"))
    c.append(cell("dr_sub","Submariner Agent",10,65,125,20,CS(),"dr"))
    c.append(cell("dr_odf","ODF (RBD Target)",10,90,125,20,CS(),"dr"))
    c.append(cell("mdr","<b>Mgmt DR</b>",180,35,145,100,CL(MO),"dr_site"))
    c.append(cell("acm_s","ACM Standby",10,40,125,20,CS(),"mdr"))
    c.append(cell("acs_s","ACS Sensor",10,65,125,20,CS(),"mdr"))
    c.append(cell("quay_dr","Quay Enterprise",10,90,125,20,CS(),"mdr"))

    c.append(edge("ep1","pipe","dc","Stage 1",ES(DC_G)))
    c.append(edge("ep2","pipe","dr","Stage 2",ES(DR_B)))
    c.append(edge("ep3","pipe","mdc","Stage 3",ES(MO)))
    c.append(edge("ep4","pipe","mdr","Stage 4",ES(MO)))
    c.append(edge("sub","dc_sub","dr_sub","IPsec UDP 4500",ES(KB)))
    c.append(edge("odf","dc_odf","dr_odf","RBD TCP 6789",ES("#00695C")))
    c.append(edge("klst1","acm_h","dc_ocp","Klusterlet",DS(MO)))
    c.append(edge("klst2","acm_h","dr_ocp","Klusterlet",DS(MO)))
    c.append(edge("qgr","quay_dc","quay_dr","Geo-Repl",DS(WP)))
    c.append(cell("t","<b>ADO Pipeline Multi-Cluster Deployment Topology</b>",180,5,450,30,TS))
    save("pipeline","19-ado-deploy-topology.drawio",wrap("ADO Deploy Topology",800,380,"\n".join(c)))

# ═══ 7: Full Deployment Run Sequence ═══
def deploy_sequence():
    c = []
    # Sequence diagram as a visual flow
    actors=[("user","Engineer",40,60,120,35),("ado","Azure DevOps",200,60,120,35),
            ("s1","DC Primary",360,60,120,35),("s2","DR Secondary",520,60,120,35),
            ("s3","Mgmt DC",680,60,120,35),("s4","Mgmt DR",840,60,120,35)]
    colors=[D,"#1A237E",DC_G,DR_B,MO,MO]
    for (aid,al,ax,ay,aw,ah),clr in zip(actors,colors):
        c.append(cell(aid,al,ax,ay,aw,ah,CS(clr,clr,1,W)))
    # Lifelines
    for aid,_,ax,_,aw,_ in actors:
        mid=ax+aw//2
        c.append(cell(f"{aid}_ll","",mid-1,95,2,280,f"fillColor={D};strokeColor={D};"))

    # Plan phase
    c.append(cell("req","Run Pipeline\nscope=all, action=plan",40,120,200,40,CS("#FFF8E1","#F57F17",0,"#F57F17")))
    steps=[("sp1","terraform plan",s,150+i*50,120,25) for i,(s,_,_) in enumerate([("s1",0,0),("s2",0,0),("s3",0,0),("s4",0,0)])]
    yp=150
    for i,(sid,_,sx,_,sw,_) in enumerate(actors[2:]):
        c.append(cell(f"plan_{sid}","terraform plan ✅",sx,yp+i*40,sw,25,CS(DC_GB,DC_G,0)))

    # Apply note
    c.append(cell("review","Review all plans",40,310,200,30,CS("#FFF8E1","#F57F17",1,"#F57F17")))
    c.append(cell("rerun","Re-run action=apply\nApplies all 4 sequentially",40,350,200,40,CS(DC_GB,DC_G,1)))

    c.append(cell("t","<b>Full Deployment Run Sequence</b>",280,10,350,30,TS))
    save("pipeline","20-full-deployment-sequence.drawio",wrap("Deploy Sequence",1000,410,"\n".join(c)))

# ═══ 8: ACM Cluster Import Workflow ═══
def acm_import_wf():
    c = []
    actors=[("op","Operator",40,50,100,30),("ado","Azure DevOps",200,50,120,30),
            ("hub","ACM Hub\n(mgmt-dc)",380,45,120,40),("dc","DC Primary",560,50,110,30),("dr","DR Secondary",720,50,110,30)]
    colors=[D,"#1A237E",MO,DC_G,DR_B]
    for (aid,al,ax,ay,aw,ah),clr in zip(actors,colors):
        c.append(cell(aid,al,ax,ay,aw,ah,CS(clr,clr,1,W)))

    c.append(cell("s1","<b>Stage 1 — ACM Cluster Import</b>",180,100,660,140,CL(MO)))
    c.append(cell("s1a","terraform apply\n-var-file=acm-import.tfvars",15,45,200,35,CS(),"s1"))
    c.append(cell("s1b","Create ManagedClusterSet\n+ ManagedCluster CRs",250,45,200,35,CS(),"s1"))
    c.append(cell("s1c","Deploy Klusterlet",490,45,140,35,CS(DC_GB,DC_G,0),"s1"))
    c.append(cell("s1d","Klusterlet: Available ✅",350,95,200,30,CS(DC_GB,DC_G,1),"s1"))
    c.append(edge("s1e1","s1a","s1b","",ES(D),"s1"))
    c.append(edge("s1e2","s1b","s1c","",ES(D),"s1"))
    c.append(edge("s1e3","s1c","s1d","reports",ES(DC_G),"s1"))

    c.append(cell("s2","<b>Stage 2 — Validate Import</b>",180,260,660,60,CL("#607D8B")))
    c.append(cell("s2a","oc get managedclusters → Available ✅",15,30,320,25,CS(),"s2"))
    c.append(cell("s2b","ocp-workload-clusters: 2 clusters",370,30,250,25,CS(DC_GB,DC_G,0),"s2"))
    c.append(edge("s2e1","s2a","s2b","",ES(D),"s2"))
    c.append(cell("t","<b>ACM Cluster Import Workflow</b>",280,10,350,30,TS))
    save("pipeline","21-acm-import-workflow.drawio",wrap("ACM Import Workflow",880,350,"\n".join(c)))

# ═══ 9: ACM DR Pipeline Stages (simple 3-box) ═══
def acm_dr_stages():
    c = []
    c.append(cell("s1","Stage 1\nConfigure DR\nDRPolicy + DRPC",40,80,180,60,CS(MOB,MO,1)))
    c.append(cell("s2","Stage 2\nExecute DR Action\nFailover / Failback",280,80,200,60,CS(IRB,IR,1)))
    c.append(cell("s3","Stage 3\nValidate DR\nCheck placement",540,80,180,60,CS(DC_GB,DC_G,1)))
    c.append(edge("e1","s1","s2","",ES(D)))
    c.append(edge("e2","s2","s3","",ES(D)))
    c.append(edge("e3","s1","s3","",DS(D)))
    c.append(cell("t","<b>ACM DR Pipeline Stages</b>",210,20,350,30,TS))
    save("pipeline","22-acm-dr-stages.drawio",wrap("ACM DR Stages",780,190,"\n".join(c)))

# ═══ 10: ACM DR Failover/Failback Workflow ═══
def acm_dr_wf():
    c = []
    # Setup phase
    c.append(cell("ph1","<b>Initial Setup — Configure DR</b>",40,60,700,80,CL("#607D8B")))
    c.append(cell("ph1a","terraform apply\n-var-file=acm-dr.tfvars",15,45,180,30,CS(),"ph1"))
    c.append(cell("ph1b","Create DRPolicy\n+ DRPlacementControl",220,45,180,30,CS(MOB,MO,0),"ph1"))
    c.append(cell("ph1c","ODF replicating PVCs ✅",440,45,180,30,CS(DC_GB,DC_G,0),"ph1"))
    c.append(edge("pe1","ph1a","ph1b","",ES(D),"ph1"))
    c.append(edge("pe2","ph1b","ph1c","",ES(D),"ph1"))
    # Failover
    c.append(cell("ph2","<b>❌ DC Failure — Failover</b>",40,170,700,80,CL(IR)))
    c.append(cell("ph2a","drAction=failover",15,45,160,30,CS(IRB,IR,1),"ph2"))
    c.append(cell("ph2b","Update DRPC →\nFailover",210,45,140,30,CS(),"ph2"))
    c.append(cell("ph2c","Promote DR\nActivate Apps",390,45,140,30,CS(DR_BB,DR_B,1),"ph2"))
    c.append(cell("ph2d","Apps on DR ✅",560,45,120,30,CS(DC_GB,DC_G,0),"ph2"))
    c.append(edge("pe3","ph2a","ph2b","",ES(D),"ph2"))
    c.append(edge("pe4","ph2b","ph2c","",ES(D),"ph2"))
    c.append(edge("pe5","ph2c","ph2d","",ES(D),"ph2"))
    # Failback
    c.append(cell("ph3","<b>✅ DC Recovered — Failback</b>",40,280,700,80,CL(DC_G)))
    c.append(cell("ph3a","drAction=failback",15,45,160,30,CS(DC_GB,DC_G,1),"ph3"))
    c.append(cell("ph3b","Update DRPC →\nFailback",210,45,140,30,CS(),"ph3"))
    c.append(cell("ph3c","Restore to DC\nDemote DR",390,45,140,30,CS(DC_GB,DC_G,1),"ph3"))
    c.append(cell("ph3d","Apps on DC ✅",560,45,120,30,CS(DC_GB,DC_G,0),"ph3"))
    c.append(edge("pe6","ph3a","ph3b","",ES(D),"ph3"))
    c.append(edge("pe7","ph3b","ph3c","",ES(D),"ph3"))
    c.append(edge("pe8","ph3c","ph3d","",ES(D),"ph3"))

    c.append(cell("t","<b>ACM DR Failover / Failback Workflow</b>",200,15,400,30,TS))
    save("pipeline","23-acm-dr-failover-workflow.drawio",wrap("ACM DR Workflow",800,390,"\n".join(c)))

# ═══ 11: CNV Deployment Workflow ═══
def cnv_deploy_wf():
    c = []
    actors=[("op","Operator",40,45,100,30),("ado","Azure DevOps",200,45,120,30),
            ("dc","DC Primary",380,45,120,30),("dr","DR Secondary",560,45,120,30)]
    colors=[D,"#1A237E",DC_G,DR_B]
    for (aid,al,ax,ay,aw,ah),clr in zip(actors,colors):
        c.append(cell(aid,al,ax,ay,aw,ah,CS(clr,clr,1,W)))

    c.append(cell("s1","<b>Stage 1 — DC Primary CNV</b>",180,100,510,140,CL(DC_G)))
    steps1=[("s1a","terraform apply\n-var-file=openshift-virtualization.tfvars",15,45,240,30),
            ("s1b","Subscribe kubevirt-hyperconverged",15,80,200,25),
            ("s1c","Create HyperConverged CR",230,80,170,25),
            ("s1d","Label worker nodes",15,110,150,25),("s1e","Deploy PrometheusRule",180,110,170,25)]
    for sid,sl,sx,sy,sw,sh in steps1:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(),"s1"))

    c.append(cell("s2","<b>Stage 2 — DR Secondary CNV</b>",180,260,510,100,CL(DR_B)))
    steps2=[("s2a","terraform apply\n-var-file=openshift-virtualization.tfvars",15,45,240,30),
            ("s2b","Subscribe + HyperConverged CR",280,45,200,30)]
    for sid,sl,sx,sy,sw,sh in steps2:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(),"s2"))

    c.append(cell("t","<b>CNV Deployment Workflow</b>",240,10,300,25,TS))
    save("pipeline","24-cnv-deploy-workflow.drawio",wrap("CNV Workflow",740,390,"\n".join(c)))

# ═══ 12: VM Migration (MTV) Workflow ═══
def vm_migration_wf():
    c = []
    c.append(cell("s1","<b>Stage 1 — VM Migration</b>",40,60,680,240,CL(WP)))
    steps=[("m1","Install MTV\nOperator",15,50,120,40),("m2","Create\nForkliftController",155,50,120,40),
           ("m3","Register Source\nProvider (vSphere)",295,50,140,40),("m4","Register Dest\nProvider (host)",455,50,130,40),
           ("m5","Create\nNetworkMap",15,120,120,40),("m6","Create\nStorageMap",155,120,120,40),
           ("m7","Create\nMigration Plan",295,120,120,40),("m8","Execute Migration\nsnapshot → transfer",435,120,160,40),
           ("m9","Create KubeVirt VMs\nMigration Complete ✅",240,185,220,40)]
    for mid,ml,mx,my,mw,mh in steps:
        c.append(cell(mid,ml,mx,my,mw,mh,CS(),"s1"))
    for i in range(3):
        c.append(edge(f"me{i}",steps[i][0],steps[i+1][0],"",ES(D),"s1"))
    c.append(edge("me3","m4","m5","",ES(D),"s1"))
    for i in range(4,7):
        c.append(edge(f"me{i}",steps[i][0],steps[i+1][0],"",ES(D),"s1"))
    c.append(edge("me7","m8","m9","",ES(DC_G),"s1"))
    c.append(cell("t","<b>VM Migration (MTV) Workflow</b>",220,15,350,30,TS))
    save("pipeline","25-vm-migration-workflow.drawio",wrap("VM Migration Workflow",780,340,"\n".join(c)))

# ═══ 13: UPI Manual Boot Validation Gate ═══
def upi_boot_gate():
    c = []
    c.append(cell("pipe","Pipeline",40,50,100,30,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("op","Operator",200,50,100,30,CS(D,D,1,W)))
    c.append(cell("nodes","Bare Metal Nodes",360,50,140,30,CS(DC_G,DC_G,1,W)))

    steps=[("s1","Generate ignition configs",40,120,180,30),
           ("s2","Start HTTP ignition server",40,170,180,30),
           ("s3","ManualValidation gate\n\"Boot control plane nodes\"",40,220,220,40),
           ("s4","Boot nodes with\nRHCOS ISO + ignition URL",200,290,200,40),
           ("s5","Install RHCOS",420,290,140,30),
           ("s6","Approve gate",200,350,120,30),
           ("s7","Continue with\ncompute nodes",40,350,150,30)]
    for sid,sl,sx,sy,sw,sh in steps:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS()))

    c.append(edge("e1","pipe","s1","",ES(D)))
    c.append(edge("e2","s1","s2","",ES(D)))
    c.append(edge("e3","s2","s3","",ES(D)))
    c.append(edge("e4","s3","s4","notify",ES(MO)))
    c.append(edge("e5","s4","s5","",ES(DC_G)))
    c.append(edge("e6","s5","s6","",ES(DC_G)))
    c.append(edge("e7","s6","s7","",ES(DC_G)))
    c.append(cell("t","<b>UPI Manual Boot Validation Gate</b>",120,10,350,25,TS))
    save("pipeline","26-upi-boot-gate.drawio",wrap("UPI Boot Gate",600,410,"\n".join(c)))

# ═══ 14-18: Code module dependency chains ═══
def code_ipi_dc():
    c = []
    mods=[("dns","dns",150,50),("qm","quay_mirror",350,50),("ocp","ocp_baremetal",250,120),
          ("nfd","nfd_operator",80,200),("gpu","gpu_operator",80,270),("metallb","metallb_operator",220,200),
          ("sriov","sriov_operator",360,200),("odf","odf_operator",500,200),("sm","servicemesh",220,270),
          ("sl","serverless",360,270),("oaai","openshift_ai",220,340),("gpum","gpu_monitoring",80,340),
          ("ca","cluster_autoscaler",500,270),("etcd","etcd_backup",500,340),("sub","submariner",650,200),
          ("odfdr","odf_dr",650,270)]
    for mid,ml,mx,my in mods:
        c.append(cell(mid,ml,mx,my,130,30,CS()))
    deps=[("dns","ocp"),("qm","ocp"),("ocp","nfd"),("nfd","gpu"),("ocp","metallb"),("ocp","sriov"),
          ("ocp","odf"),("ocp","sm"),("ocp","sl"),("gpu","oaai"),("odf","oaai"),("sm","oaai"),("sl","oaai"),
          ("gpu","gpum"),("ocp","ca"),("ocp","etcd"),("ocp","sub"),("odf","odfdr"),("sub","odfdr")]
    for i,(s,t) in enumerate(deps):
        c.append(edge(f"de{i}",s,t,"",ES(D)))
    c.append(cell("t","<b>IPI DC Primary — Module Dependency Chain</b>",180,5,400,30,TS))
    save("code","07-ipi-dc-dep-chain.drawio",wrap("IPI DC Dep Chain",820,400,"\n".join(c)))

def code_ipi_dr():
    c = []
    mods=[("dns","dns",150,50),("qm","quay_mirror",350,50),("ocp","ocp_baremetal",250,120),
          ("nfd","nfd_operator",80,200),("gpu","gpu_operator",80,270),("metallb","metallb_operator",220,200),
          ("sriov","sriov_operator",360,200),("odf","odf_operator",500,200),("sm","servicemesh",220,270),
          ("sl","serverless",360,270),("oaai","openshift_ai",220,340),("gpum","gpu_monitoring",80,340),
          ("ca","cluster_autoscaler",500,270),("etcd","etcd_backup",500,340),("sub","submariner (agent)",650,200),
          ("odfdr","odf_dr",650,270)]
    for mid,ml,mx,my in mods:
        c.append(cell(mid,ml,mx,my,130,30,CS()))
    deps=[("dns","ocp"),("qm","ocp"),("ocp","nfd"),("nfd","gpu"),("ocp","metallb"),("ocp","sriov"),
          ("ocp","odf"),("ocp","sm"),("ocp","sl"),("gpu","oaai"),("odf","oaai"),("sm","oaai"),("sl","oaai"),
          ("gpu","gpum"),("ocp","ca"),("ocp","etcd"),("ocp","sub"),("odf","odfdr")]
    for i,(s,t) in enumerate(deps):
        c.append(edge(f"de{i}",s,t,"",ES(D)))
    c.append(cell("t","<b>IPI DR Secondary — Module Dependency Chain</b>",180,5,400,30,TS))
    save("code","08-ipi-dr-dep-chain.drawio",wrap("IPI DR Dep Chain",820,400,"\n".join(c)))

def code_pipeline_stages():
    c = []
    stages=[("dc","DC Primary",40,80,120,35,DC_G),("dr","DR Secondary",200,80,130,35,DR_B),
            ("mdc","Mgmt DC",360,80,110,35,MO),("mdr","Mgmt DR",510,80,110,35,MO),
            ("sum","Summary",660,80,100,35,"#607D8B")]
    for sid,sl,sx,sy,sw,sh,sc in stages:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(sc,sc,1,W)))
    c.append(edge("e1","dc","dr","",ES(D)))
    c.append(edge("e2","dc","mdc","",ES(D)))
    c.append(edge("e3","dr","mdr","",ES(D)))
    c.append(edge("e4","mdc","mdr","",ES(D)))
    c.append(edge("e5","mdr","sum","",ES(D)))
    c.append(cell("t","<b>IPI Pipeline Stage Execution Order</b>",200,20,400,30,TS))
    save("code","09-ipi-pipeline-stage-order.drawio",wrap("Pipeline Stage Order",800,160,"\n".join(c)))

def code_upi_dc():
    c = []
    mods=[("dns","dns",40,50),("haproxy","haproxy",200,50),("ic","install_config",350,50),
          ("qm","quay_mirror",500,50),("ign","ignition",350,120),("ignsrv","ignition_server",350,180),
          ("boot","bootstrap",350,240),("cp","control_plane",350,300),("bc","bootstrap_complete",350,360),
          ("cleanup","bootstrap_cleanup",350,420),("compute","compute_nodes",350,480),("cc","cluster_complete",350,540),
          ("nfd","nfd_operator",80,600),("gpu","gpu_operator",80,660),("metallb","metallb_operator",220,600),
          ("sriov","sriov_operator",360,600),("odf","odf_operator",500,600),("sm","servicemesh",220,660),
          ("sl","serverless",360,660),("oaai","openshift_ai",220,720),("gpum","gpu_monitoring",80,720),
          ("ca","cluster_autoscaler",500,660),("etcd","etcd_backup",500,720),("sub","submariner",650,600),
          ("odfdr","odf_dr",650,660)]
    for mid,ml,mx,my in mods:
        st = CS(IRB,IR,0,IR) if mid=="cleanup" else CS()
        c.append(cell(mid,ml,mx,my,140,30,st))
    deps=[("dns","haproxy"),("dns","ic"),("haproxy","ic"),("qm","ic"),("ic","ign"),("ign","ignsrv"),
          ("ignsrv","boot"),("boot","cp"),("cp","bc"),("bc","cleanup"),("cleanup","compute"),("compute","cc"),
          ("cc","nfd"),("nfd","gpu"),("cc","metallb"),("cc","sriov"),("cc","odf"),("cc","sm"),("cc","sl"),
          ("gpu","oaai"),("odf","oaai"),("sm","oaai"),("sl","oaai"),("gpu","gpum"),("cc","ca"),("cc","etcd"),
          ("cc","sub"),("odf","odfdr"),("sub","odfdr")]
    for i,(s,t) in enumerate(deps):
        c.append(edge(f"de{i}",s,t,"",ES(D)))
    c.append(cell("t","<b>UPI DC Primary — Module Dependency Chain</b>",180,5,400,30,TS))
    save("code","10-upi-dc-dep-chain.drawio",wrap("UPI DC Dep Chain",830,780,"\n".join(c)))

def code_upi_dr():
    c = []
    mods=[("dns","dns",40,50),("haproxy","haproxy",200,50),("ic","install_config",350,50),
          ("qm","quay_mirror",500,50),("ign","ignition",350,120),("ignsrv","ignition_server",350,180),
          ("boot","bootstrap",350,240),("cp","control_plane",350,300),("bc","bootstrap_complete",350,360),
          ("cleanup","bootstrap_cleanup",350,420),("compute","compute_nodes",350,480),("cc","cluster_complete",350,540),
          ("nfd","nfd_operator",80,600),("gpu","gpu_operator",80,660),("metallb","metallb_operator",220,600),
          ("sriov","sriov_operator",360,600),("odf","odf_operator",500,600),("sm","servicemesh",220,660),
          ("sl","serverless",360,660),("oaai","openshift_ai",220,720),("gpum","gpu_monitoring",80,720),
          ("etcd","etcd_backup",500,660),("ca","cluster_autoscaler",500,720),
          ("sub","submariner (Agent)",650,600),("odfdr","odf_dr (Replication)",650,660)]
    for mid,ml,mx,my in mods:
        clr = IRB if mid=="cleanup" else (DR_BB if mid in ("sub","odfdr") else W)
        st_c = IR if mid=="cleanup" else (DR_B if mid in ("sub","odfdr") else D)
        c.append(cell(mid,ml,mx,my,150,30,CS(clr,st_c,0)))
    deps=[("dns","haproxy"),("dns","ic"),("haproxy","ic"),("qm","ic"),("ic","ign"),("ign","ignsrv"),
          ("ignsrv","boot"),("boot","cp"),("cp","bc"),("bc","cleanup"),("cleanup","compute"),("compute","cc"),
          ("cc","nfd"),("nfd","gpu"),("cc","metallb"),("cc","sriov"),("cc","odf"),("cc","sm"),("sm","sl"),("sl","oaai"),
          ("gpu","oaai"),("gpu","gpum"),("cc","etcd"),("cc","ca"),("cc","sub"),("odf","odfdr")]
    for i,(s,t) in enumerate(deps):
        c.append(edge(f"de{i}",s,t,"",ES(D)))
    c.append(cell("t","<b>UPI DR Secondary — Module Dependency Chain</b>",180,5,420,30,TS))
    save("code","11-upi-dr-dep-chain.drawio",wrap("UPI DR Dep Chain",850,780,"\n".join(c)))

if __name__=="__main__":
    print("Batch 11: 18 remaining diagrams")
    proto_port_map()        # 1
    acm_import_topo()       # 2
    acm_dr_failover()       # 3
    quay_failover_behavior()# 4
    acm_reimport()          # 5
    ado_deploy_topo()       # 6
    deploy_sequence()       # 7
    acm_import_wf()         # 8
    acm_dr_stages()         # 9
    acm_dr_wf()             # 10
    cnv_deploy_wf()         # 11
    vm_migration_wf()       # 12
    upi_boot_gate()         # 13
    code_ipi_dc()           # 14
    code_ipi_dr()           # 15
    code_pipeline_stages()  # 16
    code_upi_dc()           # 17
    code_upi_dr()           # 18
    print("Batch 11 complete! (18 diagrams)")
