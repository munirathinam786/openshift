#!/usr/bin/env python3
"""Batch 8: UPI Pipeline + CNV/VM/MTC Pipeline Diagrams (6 diagrams)"""
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

# ═══ DIAGRAM 1: UPI Pipeline Parameters ═══
def upi_params():
    c = []
    params=[("p1","bootMethod\npxe | iso | manual",40,60,180,50,MO),
            ("p2","deploymentPhase\nprerequisites | ignition |\nbootstrap | compute |\nday2-operators | full",240,60,220,80,KB),
            ("p3","terraformAction\nplan / apply / destroy",480,60,180,50,IR),
            ("p4","enableSubmariner\ntrue / false",40,150,180,50,KB),
            ("p5","enableOdfReplication\ntrue / false",240,150,200,50,"#00695C")]
    for pid,pl,px,py,pw,ph,pc in params:
        c.append(cell(pid,pl,px,py,pw,ph,CS(W,pc,0,pc)))
    c.append(cell("t","<b>UPI ADO Pipeline — Parameters</b>",180,15,400,25,TS))
    save("07-upi-pipeline-parameters.drawio",wrap("UPI Pipeline Parameters",720,230,"\n".join(c)))

# ═══ DIAGRAM 2: UPI Phase Selection ═══
def upi_phases():
    c = []
    phases=[("ph1","prerequisites",40,100,140,40),("ph2","ignition",200,100,120,40),
            ("ph3","bootstrap",340,100,120,40),("ph4","compute",480,100,120,40),
            ("ph5","day2-operators",620,100,140,40),("ph6","full\n(all phases)",780,100,120,45)]
    colors=[DR_B,MO,IR,DC_G,WP,"#455A64"]
    for (pid,pl,px,py,pw,ph),clr in zip(phases,colors):
        c.append(cell(pid,pl,px,py,pw,ph,CS(W,clr,1,clr)))

    for i in range(5):
        c.append(edge(f"pe{i}",phases[i][0],phases[i+1][0],"",ES(D)))

    c.append(cell("t","<b>UPI Deployment Phase Selection</b>",280,20,400,25,TS))
    save("08-upi-phase-selection.drawio",wrap("UPI Phase Selection",960,180,"\n".join(c)))

# ═══ DIAGRAM 3: UPI Pipeline Stages ═══
def upi_stages():
    c = []
    c.append(cell("trigger","UPI Pipeline\nTrigger",40,80,140,50,CS("#1A237E","#1A237E",1,W)))

    stages=[("s1","Stage 1:\nPrerequisites\nDNS+LB+Quay",220,60,160,65,DR_B),
            ("s2","Stage 2:\nIgnition\nConfigs + HTTP",420,60,160,65,MO),
            ("s3","Stage 3:\nBootstrap\n+ Control Plane",620,60,160,65,IR),
            ("s4","Stage 4:\nCompute\nWorkers + CSRs",820,60,160,65,DC_G),
            ("s5","Stage 5:\nDay-2\nOperators",1020,60,140,65,WP),
            ("sum","Summary",1200,75,100,40,"#607D8B")]
    for sid,sl,sx,sy,sw,sh,sc in stages:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(sc,sc,1,W)))

    c.append(edge("e0","trigger","s1","",ES(D)))
    for i in range(5):
        c.append(edge(f"e{i+1}",stages[i][0],stages[i+1][0],"",ES(D)))
    c.append(edge("e6","s5","sum","",ES(D)))

    # Gate between s3 and s4
    c.append(cell("gate","⏸ Manual Boot Gate\nOperator boots nodes\nwith RHCOS ISO/PXE",520,160,230,55,CS("#FFF8E1","#F57F17",1,"#F57F17")))
    c.append(edge("ge1","s3","gate","",DS("#F57F17")))
    c.append(edge("ge2","gate","s4","Approved",ES(DC_G)))

    c.append(cell("t","<b>UPI Pipeline — Stage Execution Order</b>",400,15,480,30,TS))
    save("09-upi-pipeline-stages.drawio",wrap("UPI Pipeline Stages",1340,250,"\n".join(c)))

# ═══ DIAGRAM 4: CNV Pipeline ═══
def cnv_pipe():
    c = []
    c.append(cell("trigger","CNV Pipeline\nTrigger",40,80,140,50,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("s1","Stage 1:\nDC Primary CNV",240,60,180,80,CS(DC_G,DC_G,1,W)))
    c.append(cell("s2","Stage 2:\nDR Secondary CNV",480,60,180,80,CS(DR_B,DR_B,1,W)))
    c.append(cell("sum","Stage 3:\nSummary",720,75,140,50,CS("#607D8B","#607D8B",1,W)))

    # CNV workflow
    c.append(cell("wf","<b>OpenShift Virtualization Workflow</b>",40,180,820,140,CL(WP)))
    steps=[("w1","Operator\nSubscription",15,50,120,45),("w2","HyperConverged\nCR Creation",155,50,130,45),
           ("w3","Node Labeling\nkubevirt.io/schedulable",305,50,140,45),("w4","Live Migration\nConfig",465,50,120,45),
           ("w5","PrometheusRule\nAlerts",605,50,120,45)]
    for wid,wl,wx,wy,ww,wh in steps:
        c.append(cell(wid,wl,wx,wy,ww,wh,CS(),"wf"))
    for i in range(4):
        c.append(edge(f"we{i}",steps[i][0],steps[i+1][0],"",ES(D),"wf"))

    c.append(edge("e1","trigger","s1","",ES(D)))
    c.append(edge("e2","s1","s2","",ES(D)))
    c.append(edge("e3","s2","sum","",ES(D)))

    c.append(cell("t","<b>OpenShift Virtualization (CNV) Pipeline</b>",250,15,480,25,TS))
    save("10-cnv-pipeline.drawio",wrap("CNV Pipeline",920,350,"\n".join(c)))

# ═══ DIAGRAM 5: VM Migration Pipeline ═══
def vm_migration():
    c = []
    c.append(cell("trigger","VM Migration\nPipeline Trigger",40,80,160,50,CS("#1A237E","#1A237E",1,W)))
    c.append(cell("s1","Stage 1:\nDC or DR VM Migration",260,60,200,80,CS(WP,WP,1,W)))
    c.append(cell("sum","Stage 2:\nSummary",520,75,140,50,CS("#607D8B","#607D8B",1,W)))

    c.append(cell("wf","<b>VM Migration Workflow (MTV)</b>",40,180,620,180,CL(WP)))
    steps=[("m1","MTV Operator\nInstall",15,50,120,45),("m2","Source Provider\nRegistration",155,50,130,45),
           ("m3","Network + Storage\nMapping",305,50,130,45),("m4","Migration Plan\nCreation",455,50,130,45),
           ("m5","Execute\nMigration",255,120,130,45)]
    for mid,ml,mx,my,mw,mh in steps:
        c.append(cell(mid,ml,mx,my,mw,mh,CS(),"wf"))
    for i in range(3):
        c.append(edge(f"me{i}",steps[i][0],steps[i+1][0],"",ES(D),"wf"))
    c.append(edge("me3","m4","m5","",ES(D),"wf"))

    c.append(edge("e1","trigger","s1","",ES(D)))
    c.append(edge("e2","s1","sum","",ES(D)))

    c.append(cell("t","<b>VM Migration (MTV) Pipeline</b>",180,15,400,25,TS))
    save("11-vm-migration-pipeline.drawio",wrap("VM Migration Pipeline",720,390,"\n".join(c)))

# ═══ DIAGRAM 6: MTC Pipeline ═══
def mtc_pipe():
    c = []
    c.append(cell("trigger","MTC Pipeline\nTrigger",40,80,140,50,CS("#1A237E","#1A237E",1,W)))

    c.append(cell("wf","<b>MTC Workload Migration Workflow</b>",40,170,820,200,CL(WP)))
    steps=[("t1","MTC Operator\nInstall",15,50,130,45),("t2","Cluster\nRegistration",165,50,120,45),
           ("t3","MigStorage\nSetup",305,50,120,45),("t4","MigPlan\nCreation",445,50,120,45),
           ("t5","Quiesce\nSource Pods",15,120,120,45),("t6","Backup\nPVs + State",155,120,120,45),
           ("t7","Restore on\nTarget",295,120,120,45),("t8","DVM/DIM\nOperations",435,120,120,45),
           ("t9","Cutover\nComplete",575,120,120,45)]
    for tid,tl,tx,ty,tw,th in steps:
        c.append(cell(tid,tl,tx,ty,tw,th,CS(),"wf"))
    for i in range(3):
        c.append(edge(f"te{i}",steps[i][0],steps[i+1][0],"",ES(D),"wf"))
    c.append(edge("te3","t4","t5","Execute",ES(IR),"wf"))
    for i in range(4,8):
        c.append(edge(f"te{i}",steps[i][0],steps[i+1][0],"",ES(D),"wf"))

    c.append(edge("e1","trigger","wf","",ES(D)))

    c.append(cell("t","<b>MTC Container Migration Pipeline</b>",250,15,400,25,TS))
    save("12-mtc-pipeline.drawio",wrap("MTC Pipeline",920,400,"\n".join(c)))

if __name__=="__main__":
    print("Batch 8: UPI + CNV/VM/MTC Pipeline Diagrams")
    upi_params();upi_phases();upi_stages();cnv_pipe();vm_migration();mtc_pipe()
    print("Batch 8 complete! (6 diagrams)")
