#!/usr/bin/env python3
"""Batch 7: Pipeline Diagrams - IPI (6 diagrams)"""
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

# ═══ DIAGRAM 1: IPI Pipeline Stage Execution ═══
def ipi_stages():
    c = []
    c.append(cell("trigger","ADO Pipeline\nTrigger",40,120,140,50,CS("#1A237E","#1A237E",1,W)))

    stages=[("s1","Stage 1:\nDC Primary",240,60,140,60,DC_G),("s2","Stage 2:\nDR Secondary",440,60,140,60,DR_B),
            ("s3","Stage 3:\nMgmt DC",640,60,140,60,MO),("s4","Stage 4:\nMgmt DR",840,60,140,60,MO),
            ("sum","Summary\nStage",1040,80,140,40,"#607D8B")]
    for sid,sl,sx,sy,sw,sh,sc in stages:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(sc,sc,1,W)))

    # Internal steps for each stage
    for s,sx in [("s1",240),("s2",440),("s3",640),("s4",840)]:
        c.append(cell(f"{s}_init","terraform init",sx,150,140,25,CS()))
        c.append(cell(f"{s}_plan","terraform plan",sx,185,140,25,CS()))
        c.append(cell(f"{s}_apply","terraform apply",sx,220,140,25,CS(DC_GB,DC_G,0)))
        c.append(edge(f"{s}_e1",s,f"{s}_init","",ES(D)))
        c.append(edge(f"{s}_e2",f"{s}_init",f"{s}_plan","",ES(D)))
        c.append(edge(f"{s}_e3",f"{s}_plan",f"{s}_apply","",ES(D)))

    c.append(edge("e1","trigger","s1","",ES(D)))
    c.append(edge("e2","s1","s2","depends_on",ES(D)))
    c.append(edge("e3","s2","s3","depends_on",ES(D)))
    c.append(edge("e4","s3","s4","depends_on",ES(D)))
    c.append(edge("e5","s4","sum","",ES(D)))

    c.append(cell("t","<b>IPI Pipeline — Stage Execution Order</b>",350,15,500,30,TS))
    save("01-ipi-pipeline-stages.drawio",wrap("IPI Pipeline Stages",1240,280,"\n".join(c)))

# ═══ DIAGRAM 2: IPI Pipeline Parameters ═══
def ipi_params():
    c = []
    params=[("p1","deploymentScope\ndc-only | dr-only |\ndc-and-dr | mgmt-dc-only |\nmgmt-dr-only | mgmt-clusters |\nall-dc | all-dr | all",40,60,260,100,MO),
            ("p2","enableSubmariner\ntrue / false",320,60,180,50,KB),
            ("p3","enableOdfReplication\ntrue / false",520,60,180,50,"#00695C"),
            ("p4","odfDrMode\nregional-dr / metro-dr",320,130,180,50,"#00695C"),
            ("p5","terraformAction\nplan / apply / destroy",520,130,180,50,IR)]
    for pid,pl,px,py,pw,ph,pc in params:
        c.append(cell(pid,pl,px,py,pw,ph,CS(W,pc,0,pc)))

    c.append(cell("t","<b>IPI ADO Pipeline — Parameters</b>",180,15,500,30,TS))
    save("02-ipi-pipeline-parameters.drawio",wrap("IPI Pipeline Parameters",740,220,"\n".join(c)))

# ═══ DIAGRAM 3: Post-Deployment Topology ═══
def post_deploy():
    c = []
    c.append(cell("dc_cl","<b>DC Primary</b>\nOCP + AI + GPU + ODF",40,60,200,80,CS(DC_GB,DC_G,1,DC_G)))
    c.append(cell("dr_cl","<b>DR Secondary</b>\nOCP + AI + GPU + ODF",560,60,200,80,CS(DR_BB,DR_B,1,DR_B)))
    c.append(cell("mdc_cl","<b>Mgmt DC</b>\nACM Hub + ACS + Quay",40,220,200,80,CS(MOB,MO,1,MO)))
    c.append(cell("mdr_cl","<b>Mgmt DR</b>\nACM Standby + ACS + Quay",560,220,200,80,CS(MOB,MO,1,MO)))

    c.append(edge("e1","dc_cl","dr_cl","① Submariner IPsec\nUDP 4500",ES(KB)))
    c.append(edge("e2","dc_cl","dr_cl","② ODF RBD Mirroring\nTCP 6789",ES("#00695C")))
    c.append(edge("e3","mdc_cl","dc_cl","③ ACM Klusterlet\nTCP 6443",ES(MO)))
    c.append(edge("e4","mdc_cl","dr_cl","④ ACM Klusterlet\nTCP 6443",ES(MO)))
    c.append(edge("e5","mdc_cl","mdr_cl","⑤ ACM Failover",DS(MO)))

    c.append(cell("t","<b>Post-Deployment Cluster Topology</b>",220,15,400,30,TS))
    save("03-post-deployment-topology.drawio",wrap("Post-Deploy Topology",820,340,"\n".join(c)))

# ═══ DIAGRAM 4: ACM Import Pipeline ═══  
def acm_import_pipe():
    c = []
    c.append(cell("trigger","Pipeline Trigger\nazure-pipelines-acm-import.yml",40,60,240,50,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("scope","Import Scope\ndc-only | dr-only | both",320,60,180,50,CS(MOB,MO,1)))
    c.append(cell("init","terraform init\n-var-file=acm-import.tfvars",320,150,200,50,CS()))
    c.append(cell("apply","terraform apply\nManagedCluster + KlusterletAddonConfig",320,230,280,50,CS(DC_GB,DC_G,1)))

    c.append(cell("hub","ACM Hub\n(Mgmt DC)",680,60,140,50,RH()))
    c.append(cell("set","ManagedClusterSet\nocp-workload-clusters",680,140,180,45,CS(MOB,MO,0)))
    c.append(cell("dc_mc","DC Primary\nManagedCluster",680,210,140,40,CS(DC_GB,DC_G,1)))
    c.append(cell("dr_mc","DR Secondary\nManagedCluster",680,265,140,40,CS(DR_BB,DR_B,1)))

    c.append(edge("e1","trigger","scope","",ES(D)))
    c.append(edge("e2","scope","init","",ES(D)))
    c.append(edge("e3","init","apply","",ES(D)))
    c.append(edge("e4","apply","hub","Import",ES(MO)))
    c.append(edge("e5","hub","set","",ES(D)))
    c.append(edge("e6","set","dc_mc","",DS(DC_G)))
    c.append(edge("e7","set","dr_mc","",DS(DR_B)))

    c.append(cell("t","<b>ACM Cluster Import Pipeline</b>",280,15,400,30,TS))
    save("04-acm-import-pipeline.drawio",wrap("ACM Import Pipeline",900,340,"\n".join(c)))

# ═══ DIAGRAM 5: ACM DR Pipeline ═══
def acm_dr_pipe():
    c = []
    # Three states
    c.append(cell("normal","<b>Normal Operation</b>",40,80,200,100,CL(DC_G)))
    c.append(cell("n_dc","DC Primary: ACTIVE",15,50,170,20,CS(DC_GB,DC_G,1,DC_G),"normal"))
    c.append(cell("n_dr","DR Secondary: STANDBY",15,75,170,20,CS(DR_BB,DR_B,0),"normal"))

    c.append(cell("failover_s","<b>After Failover</b>",320,80,200,100,CL(IR)))
    c.append(cell("f_dc","DC Primary: DOWN",15,50,170,20,CS(IRB,IR,1,IR),"failover_s"))
    c.append(cell("f_dr","DR Secondary: ACTIVE",15,75,170,20,CS(DR_BB,DR_B,1,DR_B),"failover_s"))

    c.append(cell("failback_s","<b>After Failback</b>",600,80,200,100,CL(DC_G)))
    c.append(cell("b_dc","DC Primary: ACTIVE (restored)",15,50,180,20,CS(DC_GB,DC_G,1,DC_G),"failback_s"))
    c.append(cell("b_dr","DR Secondary: STANDBY",15,75,170,20,CS(DR_BB,DR_B,0),"failback_s"))

    c.append(edge("e1","normal","failover_s","Failover",ES(IR)))
    c.append(edge("e2","failover_s","failback_s","Failback",ES(DC_G)))

    # Pipeline stages
    c.append(cell("ps","<b>Pipeline Stages</b>",40,230,760,110,CL("#607D8B")))
    c.append(cell("ps1","Stage 1:\nConfigure DR\n(DRPolicy + DRPC)",15,45,220,55,CS(MOB,MO,1),"ps"))
    c.append(cell("ps2","Stage 2:\nExecute DR Action\n(Failover/Failback/Relocate)",260,45,230,55,CS(IRB,IR,1),"ps"))
    c.append(cell("ps3","Stage 3:\nValidate DR\n(Check status)",520,45,210,55,CS(DC_GB,DC_G,1),"ps"))
    c.append(edge("pe1","ps1","ps2","",ES(D),"ps"))
    c.append(edge("pe2","ps2","ps3","",ES(D),"ps"))

    c.append(cell("t","<b>ACM DR Failover/Failback Pipeline</b>",220,15,500,30,TS))
    save("05-acm-dr-pipeline.drawio",wrap("ACM DR Pipeline",860,370,"\n".join(c)))

# ═══ DIAGRAM 6: Day-2 Pipeline Flow ═══
def day2_pipe():
    c = []
    c.append(cell("trigger","Day-2 Pipeline\nTrigger",40,100,140,50,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("params","Parameters\ndeploymentScope\nterraformAction",220,80,160,60,CS(MOB,MO,1)))
    c.append(cell("scope","Scope Selection",420,85,140,50,f"rhombus;whiteSpace=wrap;html=1;fillColor=#FF8F00;strokeColor=#FF8F00;fontColor=#FFFFFF;fontSize=11;fontStyle=1;"))

    targets=[("dc","DC Primary\nday2-terraform.tfvars",280,200,180,45,DC_G),
             ("dr","DR Secondary\nday2-terraform.tfvars",480,200,180,45,DR_B),
             ("mdc","Mgmt DC\nday2-terraform.tfvars",280,270,180,45,MO),
             ("mdr","Mgmt DR\nday2-terraform.tfvars",480,270,180,45,MO)]
    for tid,tl,tx,ty,tw,th,tc in targets:
        c.append(cell(tid,tl,tx,ty,tw,th,CS(W,tc,0,tc)))
        c.append(edge(f"te_{tid}","scope",tid,"",ES(tc)))

    c.append(cell("apply","terraform init\nterraform apply\n-var-file=day2-terraform.tfvars",700,220,220,60,CS(DC_GB,DC_G,1)))
    for tid in ["dc","dr","mdc","mdr"]:
        c.append(edge(f"ae_{tid}",tid,"apply","",ES(D)))

    c.append(edge("e1","trigger","params","",ES(D)))
    c.append(edge("e2","params","scope","",ES(D)))

    c.append(cell("t","<b>Day-2 Pipeline Flow — IPI</b>",300,15,350,30,TS))
    save("06-day2-pipeline-flow.drawio",wrap("Day-2 Pipeline",980,360,"\n".join(c)))

if __name__=="__main__":
    print("Batch 7: Pipeline Diagrams - IPI")
    ipi_stages();ipi_params();post_deploy();acm_import_pipe();acm_dr_pipe();day2_pipe()
    print("Batch 7 complete! (6 diagrams)")
