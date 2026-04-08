#!/usr/bin/env python3
"""Batch 3: DC Primary Cluster Diagrams (4 diagrams)"""
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

# ═══ DIAGRAM 1: DC Primary Deployment Overview ═══
def d1():
    c = []
    # Flow boxes
    flow = [
        ("dns","DNS\nValidation",40,100,100,50,CS("#ECEFF1","#455A64",1)),
        ("quay","Quay Mirror\nRegistry",180,100,110,50,CS("#E8EAF6","#3F51B5",1)),
        ("haproxy","HAProxy\nLB",330,100,100,50,CS(DR_BB,DR_B,1)),
        ("ocp","OCP Baremetal\nInstall",470,100,120,50,RH()),
        ("nfd","NFD\nOperator",630,60,100,40,CS(DC_GB,DC_G,0)),
        ("gpu","GPU\nOperator",630,120,100,40,CS("#E8F5E9","#1B5E20",1)),
        ("odf","ODF\nOperator",770,60,100,40,CS("#E0F2F1","#00695C",1)),
        ("sm","Service\nMesh",770,120,100,40,CS()),
        ("sl","Serverless",770,180,100,40,CS()),
        ("metallb","MetalLB",630,180,100,40,CS()),
        ("sriov","SR-IOV",630,240,100,40,CS()),
        ("rhoai","OpenShift AI\n(RHOAI)",920,120,120,50,RH()),
        ("gpumon","GPU\nMonitoring",920,60,110,40,CS("#E8F5E9","#1B5E20",0)),
        ("autoscaler","Cluster\nAutoscaler",920,190,110,40,CS()),
        ("etcd","etcd\nBackup",920,240,110,40,CS()),
        ("sub","Submariner\nBroker",1070,140,120,50,CS("#E3F2FD",KB,1,KB)),
        ("odfdr","ODF DR\nReplication",1070,210,120,50,CS("#E0F2F1","#00695C",1)),
    ]
    for fid,fl,fx,fy,fw,fh,fs in flow:
        c.append(cell(fid,fl,fx,fy,fw,fh,fs))

    edges = [("dns","quay"),("quay","haproxy"),("haproxy","ocp"),("ocp","nfd"),("nfd","gpu"),
             ("ocp","odf"),("ocp","sm"),("ocp","sl"),("ocp","metallb"),("ocp","sriov"),
             ("gpu","rhoai"),("odf","rhoai"),("sm","rhoai"),("sl","rhoai"),
             ("gpu","gpumon"),("ocp","autoscaler"),("ocp","etcd"),("ocp","sub"),("odf","odfdr"),("sub","odfdr")]
    for i,(s,t) in enumerate(edges):
        c.append(edge(f"fe{i}",s,t,"",ES(D)))

    c.append(cell("t","<b>DC Primary — Deployment Lifecycle (IPI)</b>",350,20,500,30,TS))
    save("01-dc-primary-deployment-overview.drawio",wrap("DC Primary Deployment",1240,320,"\n".join(c)))

# ═══ DIAGRAM 2: Cross-Cluster Connectivity — DC Primary ═══
def d2():
    c = []
    c.append(cell("dc","<b>DC Primary Workload Cluster</b>",40,60,350,280,CL(DC_G)))
    c.append(cell("ocp_dc","OCP 4.15 Baremetal",20,50,150,40,RH(),"dc"))
    c.append(cell("sb","Submariner Broker\n:6443 / :8443",20,105,160,45,CS("#E3F2FD",KB,1,KB),"dc"))
    c.append(cell("sgw","Submariner Gateway\n:4500 UDP",20,165,160,45,CS("#E3F2FD",KB,1,KB),"dc"))
    c.append(cell("odf_c","ODF Ceph Storage\nRBD Mirror\n:6789 / :3300",20,225,170,50,CS("#E0F2F1","#00695C",1),"dc"))

    c.append(cell("dr","<b>DR Secondary</b>",440,60,180,130,CL(DR_B)))
    c.append(cell("dr_gw","Submariner Agent\nGateway",15,45,150,40,CS("#E3F2FD",KB,1,KB),"dr"))
    c.append(cell("dr_odf","ODF Ceph\nRBD Mirror",15,95,150,35,CS("#E0F2F1","#00695C",1),"dr"))

    c.append(cell("mdc","<b>Mgmt DC</b>",440,220,180,110,CL(MO)))
    c.append(cell("acm","ACM Hub\nKlusterlet Agent",15,45,150,35,RH(),"mdc"))
    c.append(cell("acs","ACS Central\nSensor deployed",15,90,150,30,CS(IRB,IR,1),"mdc"))

    c.append(cell("mdr","<b>Mgmt DR</b>",440,360,180,60,CL(MO)))
    c.append(cell("acm_dr","ACM Standby",15,35,150,25,CS(MOB,MO,1),"mdr"))

    c.append(edge("ce1","dr_gw","sb","① Broker Registration\nTCP 6443",ES(KB)))
    c.append(edge("ce2","sgw","dr_gw","② IPsec Tunnel\nUDP 4500 + ESP",ES(KB)))
    c.append(edge("ce3","odf_c","dr_odf","③ RBD Mirroring\nTCP 6789, 3300",ES("#00695C")))
    c.append(edge("ce4","acm","ocp_dc","④ Klusterlet Import\nTCP 6443",ES(MO)))
    c.append(edge("ce5","acs","ocp_dc","⑤ SecuredCluster\nSensor deployed",ES(IR)))

    c.append(cell("t","<b>Cross-Cluster Connectivity — DC Primary</b>",120,15,500,30,TS))
    save("02-dc-primary-connectivity.drawio",wrap("DC Primary Connectivity",680,450,"\n".join(c)))

# ═══ DIAGRAM 3: Secrets Flow — IPI ═══
def d3():
    c = []
    c.append(cell("bastion","<b>Bastion Host (/home/kni/)</b>",40,60,250,280,CL(DC_G)))
    files=[("ps","pull-secret.json",15,50,220,30),("ssh","id_ed25519 / .pub",15,90,220,30),
           ("qca","quay-ca.crt",15,130,220,30),("nls","nls-client-token.tok",15,170,220,30),
           ("ent","entitlement.pem",15,210,220,30)]
    for fid,fl,fx,fy,fw,fh in files:
        c.append(cell(fid,fl,fx,fy,fw,fh,CS(DC_GB,DC_G,0),"bastion"))

    c.append(cell("ado","<b>ADO Variable Group</b><br>(ocp-baremetal-secrets)",40,380,250,250,CL(MO)))
    secrets=[("qp","quay-admin-password",15,50,220,30),("ngc","ngc-api-key",15,85,220,30),
             ("sbt","submariner-broker-token",15,120,220,30),("s3a","odf-dr-s3-access-key",15,155,220,30),
             ("s3s","odf-dr-s3-secret-key",15,190,220,30),("acsp","acs-central-admin-password",15,225,220,30)]
    for sid,sl,sx,sy,sw,sh in secrets:
        c.append(cell(sid,sl,sx,sy,sw,sh,CS(MOB,MO,0),"ado"))

    c.append(cell("tf","<b>Terraform</b>",440,200,200,180,CL("#1565C0")))
    c.append(cell("tfvars","terraform.tfvars\n(file paths)",20,50,160,45,CS(DR_BB,DR_B,0),"tf"))
    c.append(cell("vars","-var flags\n(pipeline injects)",20,110,160,45,CS(DR_BB,DR_B,0),"tf"))

    # Edges from bastion files to tfvars
    for fid in ["ps","ssh","qca","nls","ent"]:
        c.append(edge(f"e_{fid}",fid,"tfvars","",ES(DC_G)))
    # Edges from ADO secrets to vars
    for sid in ["qp","ngc","sbt","s3a","s3s","acsp"]:
        c.append(edge(f"e_{sid}",sid,"vars","",ES(MO)))

    c.append(cell("t","<b>Secrets Flow — How Secrets Reach Terraform (IPI)</b>",150,15,500,30,TS))
    save("03-dc-primary-secrets-flow-ipi.drawio",wrap("Secrets Flow IPI",700,660,"\n".join(c)))

# ═══ DIAGRAM 4: Quay Mirror Registry Distribution ═══
def d4():
    c = []
    c.append(cell("cdn","<b>Red Hat CDN</b><br>quay.io / cdn.redhat.com",40,120,180,60,CS(RH_RED,RH_DARK,1,W)))
    c.append(cell("lq","<b>Local Quay</b><br>(Internet-Facing)<br>:8443",300,120,160,60,CS(DR_BB,DR_B,1,DR_B)))
    c.append(cell("qe_dc","<b>Quay Enterprise</b><br>Mgmt DC",540,60,160,50,CS(DC_GB,DC_G,1,DC_G)))
    c.append(cell("qe_dr","<b>Quay Enterprise</b><br>Mgmt DR",540,180,160,50,CS(DR_BB,DR_B,1,DR_B)))
    c.append(cell("dc_wl","DC Workload\nCluster",780,60,130,45,CS(DC_GB,DC_G,0)))
    c.append(cell("dr_wl","DR Workload\nCluster",780,180,130,45,CS(DR_BB,DR_B,0)))

    c.append(edge("qe1","cdn","lq","oc mirror",ES(D)))
    c.append(edge("qe2","lq","qe_dc","quay-mirror\nreplicate",ES(DC_G)))
    c.append(edge("qe3","lq","qe_dr","quay-mirror\nreplicate",ES(DR_B)))
    c.append(edge("qe4","qe_dc","dc_wl","Image Pull",ES(DC_G)))
    c.append(edge("qe5","qe_dr","dr_wl","Image Pull",ES(DR_B)))

    c.append(cell("t","<b>Quay Mirror Registry Distribution — Air-Gapped Image Flow</b>",200,30,550,30,TS))
    save("04-quay-mirror-distribution.drawio",wrap("Quay Mirror Distribution",960,280,"\n".join(c)))

if __name__=="__main__":
    print("Batch 3: DC Primary Cluster Diagrams")
    d1();d2();d3();d4()
    print("Batch 3 complete! (4 diagrams)")
