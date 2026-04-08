#!/usr/bin/env python3
"""Batch 9: Remaining Pipeline Diagrams - Day2 UPI, Submariner, ODF Replication (6 diagrams)"""
import os, html

BASE = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs/docs/diagrams/pipeline"
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

# ═══ DIAGRAM 1: Day-2 UPI Pipeline ═══
def day2_upi():
    c = []
    c.append(cell("trigger","Day-2 UPI\nPipeline",40,80,140,50,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("params","deploymentScope\n+ terraformAction",220,75,170,55,CS(MOB,MO,1)))
    c.append(cell("scope","Scope\nSelection",430,85,100,40,f"rhombus;whiteSpace=wrap;html=1;fillColor=#FF8F00;strokeColor=#FF8F00;fontColor=#FFFFFF;fontSize=11;fontStyle=1;"))

    targets=[("dc","DC Primary UPI\nday2-terraform.tfvars",260,180,180,45,DC_G),
             ("dr","DR Secondary UPI\nday2-terraform.tfvars",480,180,180,45,DR_B)]
    for tid,tl,tx,ty,tw,th,tc in targets:
        c.append(cell(tid,tl,tx,ty,tw,th,CS(W,tc,0,tc)))
        c.append(edge(f"se_{tid}","scope",tid,"",ES(tc)))

    c.append(cell("apply","terraform init + apply\n-var-file=day2-terraform.tfvars",340,270,220,50,CS(DC_GB,DC_G,1)))
    for tid in ["dc","dr"]:
        c.append(edge(f"ae_{tid}",tid,"apply","",ES(D)))

    c.append(edge("e1","trigger","params","",ES(D)))
    c.append(edge("e2","params","scope","",ES(D)))
    c.append(cell("t","<b>Day-2 Pipeline Flow — UPI</b>",250,15,350,30,TS))
    save("13-day2-upi-pipeline.drawio",wrap("Day-2 UPI Pipeline",720,350,"\n".join(c)))

# ═══ DIAGRAM 2: Submariner Pipeline ═══
def submariner_pipe():
    c = []
    c.append(cell("trigger","Submariner\nPipeline",40,80,140,50,CS("#1A237E","#1A237E",1,W)))

    c.append(cell("flow","<b>Submariner Deployment Flow</b>",40,170,780,170,CL(KB)))
    steps=[("s1","Broker Install\n(Mgmt DC Hub)",15,50,140,45),
           ("s2","SubmarinerConfig\nDC Primary",175,50,140,45),
           ("s3","SubmarinerConfig\nDR Secondary",335,50,140,45),
           ("s4","Gateway Node\nLabeling",495,50,130,45),
           ("s5","IPsec Tunnel\nEstablished",15,120,130,45),
           ("s6","Service Discovery\nEnabled",165,120,130,45),
           ("s7","Globalnet\nCIDR Assignment",315,120,130,45),
           ("s8","Cross-Cluster\nConnectivity ✓",465,120,130,45)]
    for sid,sl,sx,sy,sw,sh in steps:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(),"flow"))
    for i in range(3):
        c.append(edge(f"se{i}",steps[i][0],steps[i+1][0],"",ES(D),"flow"))
    c.append(edge("se3","s4","s5","",ES(D),"flow"))
    for i in range(4,7):
        c.append(edge(f"se{i}",steps[i][0],steps[i+1][0],"",ES(D),"flow"))

    c.append(edge("e1","trigger","flow","",ES(D)))
    c.append(cell("t","<b>Submariner Deployment Pipeline</b>",250,15,400,30,TS))
    save("14-submariner-pipeline.drawio",wrap("Submariner Pipeline",860,370,"\n".join(c)))

# ═══ DIAGRAM 3: ODF Replication Pipeline ═══
def odf_replication_pipe():
    c = []
    c.append(cell("trigger","ODF Replication\nPipeline",40,80,160,50,CS("#1A237E","#1A237E",1,W)))

    c.append(cell("flow","<b>ODF Disaster Recovery Setup</b>",40,170,780,150,CL("#00695C")))
    steps=[("o1","ODF Operator\nInstall (DC+DR)",15,50,140,45),
           ("o2","StorageCluster\nCreation",175,50,130,45),
           ("o3","CephBlockPool\nMirroring Enable",325,50,140,45),
           ("o4","RBD Mirror\nDaemon Deploy",485,50,140,45),
           ("o5","Peer Token\nExchange",15,110,130,35),
           ("o6","DRPolicy\nCreation",170,110,130,35),
           ("o7","DRCluster\nRegistration",325,110,130,35),
           ("o8","Replication\nVerified ✓",480,110,130,35)]
    for oid,ol,ox,oy,ow,oh in steps:
        c.append(cell(oid,ol,ox,oy,ow,oh,CS(),"flow"))
    for i in range(3):
        c.append(edge(f"oe{i}",steps[i][0],steps[i+1][0],"",ES(D),"flow"))
    c.append(edge("oe3","o4","o5","",ES(D),"flow"))
    for i in range(4,7):
        c.append(edge(f"oe{i}",steps[i][0],steps[i+1][0],"",ES(D),"flow"))

    c.append(edge("e1","trigger","flow","",ES(D)))
    c.append(cell("t","<b>ODF Replication Pipeline</b>",250,15,400,30,TS))
    save("15-odf-replication-pipeline.drawio",wrap("ODF Replication Pipeline",860,350,"\n".join(c)))

# ═══ DIAGRAM 4: Complete IPI Pipeline Scope Diagram ═══
def ipi_pipeline_scope():
    c = []
    # deploymentScope values mapped to clusters
    c.append(cell("trig","ADO Pipeline\nSchedule/Manual",40,80,160,50,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("scope","deploymentScope\nParameter",260,80,160,50,CS(MOB,MO,1)))

    scopes=[("all","all",480,30,100,30,D),
            ("adc","all-dc",480,70,100,30,DC_G),
            ("adr","all-dr",480,110,100,30,DR_B),
            ("dco","dc-only",480,150,100,30,DC_G),
            ("dro","dr-only",480,190,100,30,DR_B),
            ("dcd","dc-and-dr",480,230,100,30,WP),
            ("mdo","mgmt-dc-only",480,270,100,30,MO),
            ("mro","mgmt-dr-only",480,310,100,30,MO),
            ("mc","mgmt-clusters",480,350,100,30,MO)]
    for sid,sl,sx,sy,sw,sh,sc in scopes:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(W,sc,0,sc)))
        c.append(edge(f"se_{sid}","scope",sid,"",DS(sc)))

    # Clusters
    clusters=[("dc","DC Primary",660,60,140,40,DC_G),("dr","DR Secondary",660,130,140,40,DR_B),
              ("mdc","Mgmt DC",660,240,140,40,MO),("mdr","Mgmt DR",660,310,140,40,MO)]
    for cid,cl,cx,cy,cw,ch,cc in clusters:
        c.append(cell(cid,cl,cx,cy,cw,ch,CS(cc,cc,1,W)))

    # Connect scopes to clusters
    scope_map=[("all",["dc","dr","mdc","mdr"]),("adc",["dc","mdc"]),("adr",["dr","mdr"]),
               ("dco",["dc"]),("dro",["dr"]),("dcd",["dc","dr"]),("mdo",["mdc"]),("mro",["mdr"]),("mc",["mdc","mdr"])]
    ei=0
    for sid,tids in scope_map:
        for tid in tids:
            c.append(edge(f"ce{ei}",sid,tid,"",ES(D)))
            ei+=1

    c.append(edge("e1","trig","scope","",ES(D)))
    c.append(cell("t","<b>IPI Pipeline — Deployment Scope Selection</b>",220,0,500,25,TS))
    save("16-ipi-pipeline-scope.drawio",wrap("IPI Pipeline Scope",860,420,"\n".join(c)))

# ═══ DIAGRAM 5: Pipeline Secrets Flow ═══
def secrets_flow():
    c = []
    c.append(cell("ado","Azure DevOps\nPipeline",40,80,160,50,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("lib","ADO Variable\nLibrary",40,180,160,50,CS(MOB,MO,1)))
    c.append(cell("akv","Azure Key Vault\n(Pipeline Secrets)",40,280,160,50,CS(DR_BB,DR_B,1)))

    c.append(cell("tf","<b>Terraform Variables</b>",280,60,300,280,CL("#607D8B")))
    vars=[("v1","pull_secret\n(from Key Vault)",15,50,260,25),
          ("v2","ssh_private_key\n(from Key Vault)",15,85,260,25),
          ("v3","api_vip / ingress_vip\n(from variables)",15,120,260,25),
          ("v4","cluster_name / base_domain\n(from tfvars)",15,155,260,25),
          ("v5","worker_count / master_count\n(from tfvars)",15,190,260,25),
          ("v6","storage_class / odf_nodes\n(from tfvars)",15,225,260,25)]
    for vid,vl,vx,vy,vw,vh in vars:
        c.append(cell(vid,vl,vx,vy,vw,vh,CS(),"tf"))

    c.append(cell("provider","Terraform Provider\nOpenShift/vSphere/BM",640,130,180,50,CS(DC_GB,DC_G,1)))
    c.append(cell("cluster","OCP Cluster\nDeployment",640,240,180,50,RH()))

    c.append(edge("e1","ado","lib","reads",ES(D)))
    c.append(edge("e2","lib","akv","fetches secrets",ES(DR_B)))
    c.append(edge("e3","ado","tf","injects vars",ES(MO)))
    c.append(edge("e4","akv","tf","secrets",DS(IR)))
    c.append(edge("e5","tf","provider","",ES(DC_G)))
    c.append(edge("e6","provider","cluster","deploys",ES(DC_G)))

    c.append(cell("t","<b>Pipeline Secrets Flow</b>",280,15,300,30,TS))
    save("17-pipeline-secrets-flow.drawio",wrap("Secrets Flow",880,380,"\n".join(c)))

# ═══ DIAGRAM 6: Pipeline Architecture Overview ═══
def pipeline_arch():
    c = []
    c.append(cell("ado","<b>Azure DevOps</b>",40,60,300,180,CL("#1A237E")))
    pipes=[("p1","azure-pipelines.yml\n(IPI Full Deploy)",15,50,260,35),
           ("p2","azure-pipelines-day2.yml\n(Day-2 Operations)",15,95,260,35),
           ("p3","azure-pipelines-acm-import.yml",15,140,260,25)]
    for pid,pl,px,py,pw,ph in pipes:
        c.append(cell(pid,pl,px,py,pw,ph,CS(),"ado"))

    c.append(cell("addon","<b>Add-on Pipelines</b>",40,280,300,140,CL("#607D8B")))
    apipes=[("a1","azure-pipelines-cnv.yml",15,50,260,25),
            ("a2","azure-pipelines-vm-migration.yml",15,80,260,25),
            ("a3","azure-pipelines-mtc.yml",15,110,260,25)]
    for aid,al,ax,ay,aw,ah in apipes:
        c.append(cell(aid,al,ax,ay,aw,ah,CS(),"addon"))

    c.append(cell("upi","<b>UPI Pipelines</b>",400,60,300,130,CL(DC_G)))
    upipes=[("u1","azure-pipelines-upi.yml\n(UPI Full Deploy)",15,50,260,35),
            ("u2","azure-pipelines-day2-upi.yml\n(UPI Day-2)",15,95,260,25)]
    for uid,ul,ux,uy,uw,uh in upipes:
        c.append(cell(uid,ul,ux,uy,uw,uh,CS(),"upi"))

    c.append(cell("dr","<b>DR Pipelines</b>",400,230,300,100,CL(IR)))
    dpipes=[("d1","azure-pipelines-acm-dr.yml\n(Failover/Failback)",15,50,260,35)]
    for did,dl,dx,dy,dw,dh in dpipes:
        c.append(cell(did,dl,dx,dy,dw,dh,CS(),"dr"))

    c.append(cell("tfvars","Terraform\n.tfvars files",760,120,120,50,CS(DC_GB,DC_G,1)))
    c.append(cell("cluster","OCP Clusters\n(4 clusters)",760,240,120,50,RH()))
    c.append(edge("e1","ado","tfvars","references",ES(D)))
    c.append(edge("e2","upi","tfvars","references",ES(D)))
    c.append(edge("e3","tfvars","cluster","deploys",ES(DC_G)))

    c.append(cell("t","<b>Pipeline Architecture Overview</b>",250,15,350,30,TS))
    save("18-pipeline-architecture-overview.drawio",wrap("Pipeline Architecture",940,460,"\n".join(c)))

if __name__=="__main__":
    print("Batch 9: Remaining Pipeline Diagrams")
    day2_upi();submariner_pipe();odf_replication_pipe();ipi_pipeline_scope();secrets_flow();pipeline_arch()
    print("Batch 9 complete! (6 diagrams)")
