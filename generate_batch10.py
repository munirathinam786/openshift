#!/usr/bin/env python3
"""Batch 10: Code Module Dependency Diagrams (6 diagrams)"""
import os, html

BASEC = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs/docs/diagrams/code"
os.makedirs(BASEC, exist_ok=True)

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
    p=os.path.join(BASEC,fn);open(p,'w').write(xml);print(f"  Created: {p}")

# ═══ DIAGRAM 1: IPI Module Dependency - DC Primary ═══
def ipi_dc_modules():
    c = []
    c.append(cell("main","main.tf\n(DC Primary)",40,80,140,50,CS(DC_G,DC_G,1,W)))
    c.append(cell("vars","variables.tf\n+ terraform.tfvars",40,180,160,50,CS(DC_GB,DC_G,0)))
    c.append(cell("vers","versions.tf\nOpenShift Provider",40,280,160,50,CS(DC_GB,DC_G,0)))

    modules=[("m1","openshift-cluster\nIPI Install",280,40,180,50,RH_RED),
             ("m2","machine-config\nWorker Pools",280,110,180,50,MO),
             ("m3","gpu-operator\nNVIDIA GPU",280,180,180,50,WP),
             ("m4","odf-storage\nOpenShift Data Foundation",280,250,180,50,"#00695C"),
             ("m5","submariner\nCross-Cluster",280,320,180,50,KB),
             ("m6","day2-operators\nRegistry + Monitoring",280,390,180,50,"#607D8B")]
    for mid,ml,mx,my,mw,mh,mc in modules:
        c.append(cell(mid,ml,mx,my,mw,mh,CS(W,mc,0,mc)))
        c.append(edge(f"me_{mid}","main",mid,"module",ES(mc)))

    c.append(cell("out","outputs.tf\ncluster_api_url\ncluster_console_url\nkubeconfig",520,150,180,80,CS(DC_GB,DC_G,0)))
    for mid in ["m1","m2","m3","m4","m5","m6"]:
        c.append(edge(f"oe_{mid}",mid,"out","",DS(D)))

    c.append(edge("ev","vars","main","",ES(D)))
    c.append(edge("evr","vers","main","",ES(D)))
    c.append(cell("t","<b>IPI Module Dependencies — DC Primary</b>",200,10,400,30,TS))
    save("01-ipi-dc-module-deps.drawio",wrap("IPI DC Modules",760,480,"\n".join(c)))

# ═══ DIAGRAM 2: IPI Module Dependency - DR Secondary ═══
def ipi_dr_modules():
    c = []
    c.append(cell("main","main.tf\n(DR Secondary)",40,80,140,50,CS(DR_B,DR_B,1,W)))
    c.append(cell("vars","variables.tf\n+ terraform.tfvars",40,180,160,50,CS(DR_BB,DR_B,0)))
    c.append(cell("vers","versions.tf\nOpenShift Provider",40,280,160,50,CS(DR_BB,DR_B,0)))

    modules=[("m1","openshift-cluster\nIPI Install",280,40,180,50,RH_RED),
             ("m2","machine-config\nWorker Pools",280,110,180,50,MO),
             ("m3","gpu-operator\nNVIDIA GPU",280,180,180,50,WP),
             ("m4","odf-storage\nODF + DR Mirroring",280,250,180,50,"#00695C"),
             ("m5","submariner\nCross-Cluster Link",280,320,180,50,KB),
             ("m6","mtc-operator\nMigration Toolkit",280,390,180,50,IR)]
    for mid,ml,mx,my,mw,mh,mc in modules:
        c.append(cell(mid,ml,mx,my,mw,mh,CS(W,mc,0,mc)))
        c.append(edge(f"me_{mid}","main",mid,"module",ES(mc)))

    c.append(cell("out","outputs.tf\ncluster_api_url\ncluster_console_url\ndr_status",520,150,180,80,CS(DR_BB,DR_B,0)))
    for mid in ["m1","m2","m3","m4","m5","m6"]:
        c.append(edge(f"oe_{mid}",mid,"out","",DS(D)))

    c.append(edge("ev","vars","main","",ES(D)))
    c.append(edge("evr","vers","main","",ES(D)))
    c.append(cell("t","<b>IPI Module Dependencies — DR Secondary</b>",200,10,400,30,TS))
    save("02-ipi-dr-module-deps.drawio",wrap("IPI DR Modules",760,480,"\n".join(c)))

# ═══ DIAGRAM 3: UPI Module Dependency - DC Primary ═══
def upi_dc_modules():
    c = []
    c.append(cell("main","main.tf\n(UPI DC Primary)",40,80,140,50,CS(DC_G,DC_G,1,W)))
    c.append(cell("vars","variables.tf\n+ terraform.tfvars",40,180,160,50,CS(DC_GB,DC_G,0)))

    modules=[("m1","dns-records\nAPI + Ingress + Nodes",280,30,200,45,KB),
             ("m2","load-balancer\nHAProxy Config",280,90,200,45,MO),
             ("m3","ignition-configs\nopenshift-install",280,150,200,45,IR),
             ("m4","pxe-boot\nRHCOS + Matchbox",280,210,200,45,WP),
             ("m5","bootstrap\nBootstrap Node",280,270,200,45,"#607D8B"),
             ("m6","control-plane\n3x Masters",280,330,200,45,DC_G),
             ("m7","compute-nodes\nWorkers + GPU",280,390,200,45,"#00695C"),
             ("m8","day2-operators\nCSR Approve + ODF",280,450,200,45,"#455A64")]
    for mid,ml,mx,my,mw,mh,mc in modules:
        c.append(cell(mid,ml,mx,my,mw,mh,CS(W,mc,0,mc)))
        c.append(edge(f"me_{mid}","main",mid,"module",ES(mc)))

    # Phase arrows
    c.append(edge("ph1","m1","m2","Phase 1→2",ES(D)))
    c.append(edge("ph2","m2","m3","Phase 2→3",ES(D)))
    c.append(edge("ph3","m3","m4","Phase 3→4",ES(D)))
    c.append(edge("ph4","m5","m6","boots",ES(D)))
    c.append(edge("ph5","m6","m7","",ES(D)))
    c.append(edge("ph6","m7","m8","",ES(D)))

    c.append(edge("ev","vars","main","",ES(D)))
    c.append(cell("t","<b>UPI Module Dependencies — DC Primary</b>",200,0,400,25,TS))
    save("03-upi-dc-module-deps.drawio",wrap("UPI DC Modules",540,520,"\n".join(c)))

# ═══ DIAGRAM 4: UPI Module Dependency - DR Secondary ═══
def upi_dr_modules():
    c = []
    c.append(cell("main","main.tf\n(UPI DR Secondary)",40,80,140,50,CS(DR_B,DR_B,1,W)))
    c.append(cell("vars","variables.tf\n+ terraform.tfvars",40,180,160,50,CS(DR_BB,DR_B,0)))

    modules=[("m1","dns-records\nAPI + Ingress + Nodes",280,30,200,45,KB),
             ("m2","load-balancer\nHAProxy Config",280,90,200,45,MO),
             ("m3","ignition-configs\nopenshift-install",280,150,200,45,IR),
             ("m4","pxe-boot\nRHCOS + Matchbox",280,210,200,45,WP),
             ("m5","bootstrap\nBootstrap Node",280,270,200,45,"#607D8B"),
             ("m6","control-plane\n3x Masters",280,330,200,45,DC_G),
             ("m7","compute-nodes\nWorkers + GPU",280,390,200,45,"#00695C"),
             ("m8","day2-operators\nCSR + ODF + Submariner",280,450,200,45,"#455A64")]
    for mid,ml,mx,my,mw,mh,mc in modules:
        c.append(cell(mid,ml,mx,my,mw,mh,CS(W,mc,0,mc)))
        c.append(edge(f"me_{mid}","main",mid,"module",ES(mc)))

    c.append(edge("ph1","m1","m2","Phase 1→2",ES(D)))
    c.append(edge("ph2","m2","m3","Phase 2→3",ES(D)))
    c.append(edge("ph3","m3","m4","Phase 3→4",ES(D)))
    c.append(edge("ph4","m5","m6","boots",ES(D)))
    c.append(edge("ph5","m6","m7","",ES(D)))
    c.append(edge("ph6","m7","m8","",ES(D)))

    c.append(edge("ev","vars","main","",ES(D)))
    c.append(cell("t","<b>UPI Module Dependencies — DR Secondary</b>",200,0,400,25,TS))
    save("04-upi-dr-module-deps.drawio",wrap("UPI DR Modules",540,520,"\n".join(c)))

# ═══ DIAGRAM 5: Mgmt Cluster Module Deps ═══
def mgmt_modules():
    c = []
    c.append(cell("main","main.tf\n(Mgmt DC)",40,80,140,50,CS(MO,MO,1,W)))
    c.append(cell("vars","variables.tf\n+ terraform.tfvars",40,180,160,50,CS(MOB,MO,0)))

    modules=[("m1","acm-hub\nAdvanced Cluster Mgmt",280,30,200,50,RH_RED),
             ("m2","acs-central\nAdv Cluster Security",280,100,200,50,IR),
             ("m3","quay-registry\nImage Registry",280,170,200,50,WP),
             ("m4","acm-import\nManagedCluster CRs",280,240,200,50,MO),
             ("m5","acm-dr\nDRPolicy + DRPC",280,310,200,50,DR_B),
             ("m6","submariner-broker\nBroker Install",280,380,200,50,KB)]
    for mid,ml,mx,my,mw,mh,mc in modules:
        c.append(cell(mid,ml,mx,my,mw,mh,CS(W,mc,0,mc)))
        c.append(edge(f"me_{mid}","main",mid,"module",ES(mc)))

    c.append(edge("dep1","m4","m1","depends_on",DS(MO)))
    c.append(edge("dep2","m5","m4","depends_on",DS(DR_B)))
    c.append(edge("dep3","m6","m4","depends_on",DS(KB)))

    c.append(edge("ev","vars","main","",ES(D)))
    c.append(cell("t","<b>Management Cluster Module Dependencies</b>",200,0,400,25,TS))
    save("05-mgmt-module-deps.drawio",wrap("Mgmt Modules",540,460,"\n".join(c)))

# ═══ DIAGRAM 6: Terraform File Structure ═══
def tf_structure():
    c = []
    c.append(cell("root","<b>Terraform-IaC Project Structure</b>",40,60,600,400,CL("#455A64")))

    c.append(cell("ipi","ipi-method/",15,50,260,215,CL(DC_G),"root"))
    dirs=[("id1","openshiftbaremetal/\n(DC Primary)",15,50,220,30),
          ("id2","openshiftbaremetal-dr/\n(DR Secondary)",15,90,220,30),
          ("id3","mgmt-dc/\n(Management DC)",15,130,220,30),
          ("id4","mgmt-dr/\n(Management DR)",15,170,220,30)]
    for did,dl,dx,dy,dw,dh in dirs:
        c.append(cell(did,dl,dx,dy,dw,dh,CS(DC_GB,DC_G,0),"ipi"))

    c.append(cell("upi","upi-method/",300,50,260,215,CL(DR_B),"root"))
    udirs=[("ud1","openshiftbaremetal/\n(DC Primary UPI)",15,50,220,30),
           ("ud2","openshiftbaremetal-dr/\n(DR Secondary UPI)",15,90,220,30),
           ("ud3","mgmt-dc/\n(Management DC)",15,130,220,30),
           ("ud4","mgmt-dr/\n(Management DR)",15,170,220,30)]
    for did,dl,dx,dy,dw,dh in udirs:
        c.append(cell(did,dl,dx,dy,dw,dh,CS(DR_BB,DR_B,0),"upi"))

    # Common files
    c.append(cell("files","Each directory contains:",15,285,560,90,CL("#607D8B"),"root"))
    flist=[("f1","main.tf",15,50,80,25),("f2","variables.tf",105,50,90,25),("f3","outputs.tf",205,50,80,25),
           ("f4","versions.tf",295,50,85,25),("f5","terraform.tfvars",395,50,110,25),
           ("f6","day2-terraform.tfvars",15,30,130,15),("f7","acm-import.tfvars",160,30,110,15),
           ("f8","acm-dr.tfvars",285,30,100,15)]
    for fid,fl,fx,fy,fw,fh in flist:
        c.append(cell(fid,fl,fx,fy,fw,fh,CS(),"files"))

    c.append(cell("t","<b>Terraform Project File Structure</b>",200,15,350,30,TS))
    save("06-terraform-file-structure.drawio",wrap("File Structure",700,510,"\n".join(c)))

if __name__=="__main__":
    print("Batch 10: Code Module Dependency Diagrams")
    ipi_dc_modules();ipi_dr_modules();upi_dc_modules();upi_dr_modules();mgmt_modules();tf_structure()
    print("Batch 10 complete! (6 diagrams)")
