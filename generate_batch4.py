#!/usr/bin/env python3
"""Batch 4: UPI Baremetal Cluster Diagrams (4 diagrams)"""
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

# ═══ DIAGRAM 1: UPI Deployment Overview ═══
def d1():
    c = []
    flow = [
        ("dns","DNS Records",40,100,100,40,CS("#ECEFF1","#455A64",1)),
        ("lb","HAProxy LB",170,100,100,40,CS(DR_BB,DR_B,1)),
        ("qm","Quay Mirror",300,100,110,40,CS("#E8EAF6","#3F51B5",1)),
        ("ic","install-config",440,100,110,40,CS(MOB,MO,1)),
        ("ign","Ignition\nConfigs",580,100,100,45,CS(MOB,MO,0)),
        ("http","HTTP Ignition\nServer :8080",710,100,120,45,CS(MOB,MO,0)),
        ("boot","Bootstrap\nNode",860,60,100,40,CS(IRB,IR,1,IR)),
        ("cp","Control Plane\nNodes",860,120,110,40,RH()),
        ("bc","Bootstrap\nComplete",1000,60,110,40,CS(DC_GB,DC_G,0)),
        ("bclean","Bootstrap\nCleanup",1000,120,110,45,CS(IRB,IR,1,IR)),
        ("wk","Worker\nNodes",1140,60,100,40,CS()),
        ("csr","CSR\nApproval",1140,120,100,40,CS()),
        ("cc","Cluster\nComplete",1270,90,100,45,CS(DC_GB,DC_G,1,DC_G)),
    ]
    for fid,fl,fx,fy,fw,fh,fs in flow:
        c.append(cell(fid,fl,fx,fy,fw,fh,fs))

    # Day-2 operators
    d2ops=[("nfd","NFD",1400,40,80,30),("gpu","GPU Op",1400,80,80,30),("odf","ODF",1400,120,80,30),
           ("sm","Svc Mesh",1400,160,80,30),("ai","RHOAI",1500,90,90,40)]
    for oid,ol,ox,oy,ow,oh in d2ops:
        c.append(cell(oid,ol,ox,oy,ow,oh,CS() if oid!="ai" else RH()))

    edges=[("dns","lb"),("lb","qm"),("qm","ic"),("ic","ign"),("ign","http"),("http","boot"),("http","cp"),
           ("boot","bc"),("cp","bc"),("bc","bclean"),("bclean","wk"),("wk","csr"),("csr","cc"),
           ("cc","nfd"),("nfd","gpu"),("gpu","ai"),("odf","ai"),("sm","ai")]
    for i,(s,t) in enumerate(edges):
        c.append(edge(f"e{i}",s,t,"",ES(D)))

    c.append(cell("t","<b>UPI Deployment Overview — Bastion-Driven Install</b>",400,15,550,30,TS))
    save("05-upi-deployment-overview.drawio",wrap("UPI Deployment Overview",1640,230,"\n".join(c)))

# ═══ DIAGRAM 2: UPI Deployment Phases (5 Phases) ═══
def d2():
    c = []
    phases = [
        ("p1","<b>Phase 1: Prerequisites</b>","#E3F2FD",DR_B,40,60,230,220,[
            ("dns","DNS Records",20,50,190,35),("lb","HAProxy Load Balancer",20,95,190,35),("qm","Quay Mirror Registry",20,140,190,35)]),
        ("p2","<b>Phase 2: Ignition</b>","#FFF3E0",MO,40,310,230,250,[
            ("ic","install-config.yaml\nplatform: none",20,50,190,45),("man","Manifests",20,105,190,35),
            ("ign","Ignition Configs\nbootstrap/master/worker.ign",20,150,190,50),("http","HTTP Server\nbastion:8080",20,210,190,40)]),
        ("p3","<b>Phase 3: Bootstrap</b>","#FCE4EC",IR,300,60,250,250,[
            ("boot","Bootstrap Node\nPXE/ISO boot",20,50,210,40),("cpn","Control Plane Nodes\nBoot 3 masters",20,100,210,40),
            ("bw","Wait: bootstrap-complete",20,150,210,35),("bclean","Bootstrap Cleanup\nRemove from LB + power off",20,195,210,45)]),
        ("p4","<b>Phase 4: Compute</b>","#E8F5E9",DC_G,300,340,250,200,[
            ("wrk","Worker Nodes\nBoot workers",20,50,210,40),("csr","Approve CSRs\noc adm certificate approve",20,100,210,45),
            ("cc","Wait: install-complete",20,155,210,35)]),
        ("p5","<b>Phase 5: Day-2 Operators</b>","#F3E5F5",WP,580,60,250,480,[
            ("nfd","NFD Operator",20,50,200,35),("gpu","GPU Operator",20,95,200,35),("odf","ODF Operator",20,140,200,35),
            ("sm","Service Mesh",20,185,200,35),("sl","Serverless",20,230,200,35),("ai","OpenShift AI",20,275,200,35),
            ("gpum","GPU Monitoring",20,320,200,35),("etcd","etcd Backup",20,365,200,35),("sub","Submariner",20,410,200,35)]),
    ]
    for pid,plbl,pbg,pstroke,px,py,pw,ph,items in phases:
        c.append(cell(pid,plbl,px,py,pw,ph,f"swimlane;startSize=40;fillColor={pbg};fontColor={pstroke};strokeColor={pstroke};rounded=1;shadow=1;fontSize=12;fontStyle=1;whiteSpace=wrap;html=1;container=1;collapsible=0;strokeWidth=2;"))
        for iid,il,ix,iy,iw,ih in items:
            sty = CS(IRB,IR,1,IR) if iid=="bclean" else (RH() if iid in ("ai",) else CS())
            c.append(cell(iid,il,ix,iy,iw,ih,sty,pid))

    c.append(edge("pe1","p1","p2","",ES(D)))
    c.append(edge("pe2","p2","p3","",ES(D)))
    c.append(edge("pe3","p3","p4","",ES(D)))
    c.append(edge("pe4","p3","p5","",ES(D)))
    c.append(edge("pe5","p4","p5","",ES(D)))

    c.append(cell("t","<b>UPI Deployment Phases — 5 Phase Breakdown</b>",200,15,500,30,TS))
    save("06-upi-deployment-phases.drawio",wrap("UPI Phases",880,580,"\n".join(c)))

# ═══ DIAGRAM 3: PXE Boot Sequence ═══
def d3():
    c = []
    # Actors
    c.append(cell("bastion","<b>Bastion</b><br>(DHCP+TFTP)",40,40,150,50,CS(MOB,MO,1,MO)))
    c.append(cell("node","<b>Bare Metal Node</b>",280,40,160,50,CS("#ECEFF1","#455A64",1)))
    c.append(cell("http","<b>HTTP Ignition Server</b>",540,40,180,50,CS(DR_BB,DR_B,1,DR_B)))

    # Sequence steps
    steps = [
        ("s1","① PXE DHCP Request (MAC address)",180,120,280,35,"node","bastion",D),
        ("s2","② IP + TFTP boot file",180,170,280,35,"bastion","node",MO),
        ("s3","③ Download kernel + initramfs",180,220,280,35,"node","bastion",D),
        ("s4","④ Fetch ignition config\n(bootstrap/master/worker.ign)",350,270,260,45,"node","http",DR_B),
        ("s5","⑤ Install RHCOS to disk",280,340,160,35,"node","node",DC_G),
        ("s6","⑥ Reboot into RHCOS",280,390,160,35,"node","node",DC_G),
    ]
    for sid,sl,sx,sy,sw,sh,src,tgt,clr in steps:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(W,clr,0,clr)))

    # Arrows
    c.append(edge("pe1","node","bastion","①",ES(D)))
    c.append(edge("pe2","bastion","node","②",ES(MO)))
    c.append(edge("pe3","node","http","④",ES(DR_B)))

    c.append(cell("t","<b>PXE Boot Sequence — UPI Node Provisioning</b>",150,5,500,25,TS))
    save("07-pxe-boot-sequence.drawio",wrap("PXE Boot Sequence",780,450,"\n".join(c)))

# ═══ DIAGRAM 4: Secrets Flow — UPI ═══
def d4():
    c = []
    c.append(cell("bastion","<b>Bastion Host (/home/kni/)</b>",40,60,250,250,CL(DC_G)))
    files=[("ps","pull-secret.json",15,50,220,30),("ssh","id_ed25519 / .pub",15,85,220,30),
           ("qca","quay-ca.crt",15,120,220,30),("nls","nls-client-token.tok",15,155,220,30),
           ("ent","entitlement.pem",15,190,220,30)]
    for fid,fl,fx,fy,fw,fh in files:
        c.append(cell(fid,fl,fx,fy,fw,fh,CS(DC_GB,DC_G,0),"bastion"))

    c.append(cell("ado","<b>ADO Variable Group</b><br>(ocp-baremetal-upi-secrets)",40,340,250,190,CL(MO)))
    secrets=[("qp","quay-admin-password",15,50,220,30),("ngc","ngc-api-key",15,85,220,30),
             ("s3a","odf-dr-s3-access-key",15,120,220,30),("s3s","odf-dr-s3-secret-key",15,155,220,30)]
    for sid,sl,sx,sy,sw,sh in secrets:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(MOB,MO,0),"ado"))

    c.append(cell("tf","<b>Terraform</b>",420,180,200,150,CL("#1565C0")))
    c.append(cell("tfvars","terraform.tfvars\n(file paths + mgmt secrets)",20,50,160,50,CS(DR_BB,DR_B,0),"tf"))
    c.append(cell("vars","-var flags\n(pipeline injects)",20,110,160,40,CS(DR_BB,DR_B,0),"tf"))

    for fid in ["ps","ssh","qca","nls","ent"]:
        c.append(edge(f"e_{fid}",fid,"tfvars","",ES(DC_G)))
    for sid in ["qp","ngc","s3a","s3s"]:
        c.append(edge(f"e_{sid}",sid,"vars","",ES(MO)))

    c.append(cell("t","<b>Secrets Flow — How Secrets Reach Terraform (UPI)</b>",130,15,500,30,TS))
    save("08-upi-secrets-flow.drawio",wrap("Secrets Flow UPI",680,560,"\n".join(c)))

if __name__=="__main__":
    print("Batch 4: UPI Baremetal Cluster Diagrams")
    d1();d2();d3();d4()
    print("Batch 4 complete! (4 diagrams)")
