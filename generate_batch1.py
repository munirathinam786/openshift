#!/usr/bin/env python3
"""Batch 1: Architecture Overview Diagrams (6 diagrams)"""
import os, html

BASE = "/Users/sathishkumarmunirathinam/Downloads/Terraform-IaC-Docs/docs/diagrams/architecture"
os.makedirs(BASE, exist_ok=True)

# Red Hat Design Colors
RH_RED = "#EE0000"
RH_DARK_RED = "#CC0000"
DC_GREEN = "#2E7D32"
DC_GREEN_BG = "#E8F5E9"
DR_BLUE = "#1565C0"
DR_BLUE_BG = "#E3F2FD"
MGMT_ORANGE = "#EF6C00"
MGMT_ORANGE_BG = "#FFF3E0"
WORKLOAD_PURPLE = "#7B1FA2"
WORKLOAD_PURPLE_BG = "#F3E5F5"
INFRA_RED_BG = "#FCE4EC"
INFRA_RED = "#C62828"
WHITE = "#FFFFFF"
DARK = "#333333"
K8S_BLUE = "#326CE5"

def esc(s):
    return html.escape(s)

def wrap(name, width, height, cells_xml):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2026-04-07T00:00:00.000Z" agent="GitHub Copilot" version="24.0.0" type="device">
  <diagram id="d1" name="{esc(name)}">
    <mxGraphModel dx="1422" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{width}" pageHeight="{height}" math="0" shadow="1">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{cells_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

def save(filename, xml):
    path = os.path.join(BASE, filename)
    with open(path, 'w') as f:
        f.write(xml)
    print(f"  Created: {path}")

# ─── Styles ────────────────────────────────────────────────
SITE_STYLE = "rounded=1;whiteSpace=wrap;html=1;dashed=1;dashPattern=12 8;fillColor=none;fontSize=16;fontStyle=1;verticalAlign=top;align=left;spacingTop=8;spacingLeft=12;container=1;collapsible=0;strokeWidth=3;"
CLUSTER_STYLE = "swimlane;startSize=35;fillColor={color};fontColor=#FFFFFF;strokeColor={stroke};rounded=1;shadow=1;fontSize=13;fontStyle=1;whiteSpace=wrap;html=1;container=1;collapsible=0;"
COMPONENT_STYLE = "rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontSize=11;fontStyle={bold};fontColor={fontColor};shadow=1;arcSize=10;"
EDGE_STYLE = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={color};fontSize=10;fontColor={color};labelBackgroundColor=#FFFFFF;strokeWidth=2;"
DASHED_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor={color};fontSize=10;fontColor={color};dashed=1;dashPattern=8 4;labelBackgroundColor=#FFFFFF;strokeWidth=2;"
ICON_BOX = "shape=image;verticalLabelPosition=bottom;labelBackgroundColor=default;verticalAlign=top;aspect=fixed;imageAspect=0;image={url};"

def site_s(color): return SITE_STYLE + f"strokeColor={color};"
def cluster_s(color, stroke=None): return CLUSTER_STYLE.format(color=color, stroke=stroke or color)
def comp_s(fill=WHITE, stroke=DARK, bold=0, fc=DARK): return COMPONENT_STYLE.format(fill=fill, stroke=stroke, bold=bold, fontColor=fc)
def rh_comp(): return comp_s(RH_RED, RH_DARK_RED, 1, WHITE)
def edge_s(color=DARK): return EDGE_STYLE.format(color=color)
def dash_s(color=DARK): return DASHED_EDGE.format(color=color)

def cell(id, val, x, y, w, h, style, parent="1"):
    return f'        <mxCell id="{id}" value="{esc(val)}" style="{style}" vertex="1" parent="{parent}">\n          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n        </mxCell>'

def edge(id, src, tgt, val="", style="", parent="1"):
    s = style if style else edge_s()
    return f'        <mxCell id="{id}" value="{esc(val)}" style="{s}" edge="1" source="{src}" target="{tgt}" parent="{parent}">\n          <mxGeometry relative="1" as="geometry"/>\n        </mxCell>'


# ════════════════════════════════════════════════════════════
# DIAGRAM 1: High-Level Multi-Cluster Architecture (IPI)
# ════════════════════════════════════════════════════════════
def diagram_1_high_level_ipi():
    c = []
    # DC Site boundary
    c.append(cell("dc_site", "<b>Data Center (DC)</b>", 20, 20, 750, 700, site_s(DC_GREEN)))
    # DR Site boundary
    c.append(cell("dr_site", "<b>Disaster Recovery (DR)</b>", 830, 20, 750, 700, site_s(DR_BLUE)))

    # ── DC Management Cluster ──
    c.append(cell("mgmt_dc", "<b>Management Cluster — DC</b>", 20, 50, 340, 280, cluster_s(MGMT_ORANGE), "dc_site"))
    c.append(cell("acm_hub", "<b>ACM Hub</b><br><i>Multi-Cluster Manager</i>", 20, 45, 145, 55, rh_comp(), "mgmt_dc"))
    c.append(cell("acs_central", "<b>ACS Central</b><br><i>Security Policies</i>", 180, 45, 140, 55, comp_s(INFRA_RED_BG, INFRA_RED, 1), "mgmt_dc"))
    c.append(cell("quay_dc", "<b>Quay Enterprise</b><br><i>Container Registry</i>", 20, 115, 145, 55, comp_s("#E8EAF6", "#3F51B5", 1), "mgmt_dc"))
    c.append(cell("odf_mgmt_dc", "ODF Storage", 180, 115, 140, 55, comp_s("#E0F2F1", "#00695C", 0), "mgmt_dc"))
    c.append(cell("acm_obs", "ACM Observability<br><i>(Thanos + Grafana)</i>", 20, 185, 300, 45, comp_s("#FFF8E1", "#F57F17", 0), "mgmt_dc"))

    # ── DC Workload Cluster ──
    c.append(cell("prod_dc", "<b>Workload Cluster — DC Primary</b>", 20, 350, 710, 320, cluster_s(WORKLOAD_PURPLE), "dc_site"))
    c.append(cell("ocp_dc", "<b>OCP 4.15</b><br>Baremetal IPI", 20, 50, 130, 55, comp_s(RH_RED, RH_DARK_RED, 1, WHITE), "prod_dc"))
    c.append(cell("rhoai_dc", "<b>OpenShift AI</b><br><i>RHOAI</i>", 170, 50, 120, 55, rh_comp(), "prod_dc"))
    c.append(cell("gpu_dc", "<b>NVIDIA GPU</b><br><i>NFD → GPU Op</i>", 310, 50, 120, 55, comp_s("#E8F5E9", "#1B5E20", 1), "prod_dc"))
    c.append(cell("odf_dc", "<b>ODF Ceph</b><br><i>Block + File</i>", 450, 50, 120, 55, comp_s("#E0F2F1", "#00695C", 1), "prod_dc"))
    c.append(cell("sm_dc", "Service Mesh", 20, 125, 100, 40, comp_s(), "prod_dc"))
    c.append(cell("sl_dc", "Serverless", 140, 125, 100, 40, comp_s(), "prod_dc"))
    c.append(cell("metallb_dc", "MetalLB", 260, 125, 90, 40, comp_s(), "prod_dc"))
    c.append(cell("sriov_dc", "SR-IOV", 370, 125, 90, 40, comp_s(), "prod_dc"))
    c.append(cell("etcd_dc", "etcd Backup", 480, 125, 100, 40, comp_s(), "prod_dc"))
    c.append(cell("sub_broker", "<b>Submariner</b><br><b>BROKER</b>", 20, 190, 160, 60, comp_s("#E3F2FD", K8S_BLUE, 1, K8S_BLUE), "prod_dc"))
    c.append(cell("autoscaler_dc", "Cluster<br>Autoscaler", 200, 190, 100, 50, comp_s(), "prod_dc"))
    c.append(cell("gpu_mon_dc", "GPU<br>Monitoring", 320, 190, 100, 50, comp_s("#E8F5E9", "#1B5E20", 0), "prod_dc"))

    # ── DR Management Cluster ──
    c.append(cell("mgmt_dr", "<b>Management Cluster — DR</b>", 20, 50, 340, 280, cluster_s(MGMT_ORANGE), "dr_site"))
    c.append(cell("acm_standby", "<b>ACM Standby</b><br><i>Passive Hub</i>", 20, 45, 145, 55, comp_s(MGMT_ORANGE_BG, MGMT_ORANGE, 1), "mgmt_dr"))
    c.append(cell("acs_secured", "<b>ACS Secured</b><br><i>Sensor + Collector</i>", 180, 45, 140, 55, comp_s(INFRA_RED_BG, INFRA_RED, 1), "mgmt_dr"))
    c.append(cell("quay_dr", "<b>Quay Enterprise</b><br><i>Geo-Replicated</i>", 20, 115, 145, 55, comp_s("#E8EAF6", "#3F51B5", 1), "mgmt_dr"))
    c.append(cell("odf_mgmt_dr", "ODF Storage", 180, 115, 140, 55, comp_s("#E0F2F1", "#00695C", 0), "mgmt_dr"))

    # ── DR Workload Cluster ──
    c.append(cell("prod_dr", "<b>Workload Cluster — DR Secondary</b>", 20, 350, 710, 320, cluster_s(WORKLOAD_PURPLE), "dr_site"))
    c.append(cell("ocp_dr", "<b>OCP 4.15</b><br>Baremetal IPI", 20, 50, 130, 55, comp_s(RH_RED, RH_DARK_RED, 1, WHITE), "prod_dr"))
    c.append(cell("rhoai_dr", "<b>OpenShift AI</b><br><i>RHOAI</i>", 170, 50, 120, 55, rh_comp(), "prod_dr"))
    c.append(cell("gpu_dr", "<b>NVIDIA GPU</b><br><i>NFD → GPU Op</i>", 310, 50, 120, 55, comp_s("#E8F5E9", "#1B5E20", 1), "prod_dr"))
    c.append(cell("odf_dr", "<b>ODF Ceph</b><br><i>Block + File</i>", 450, 50, 120, 55, comp_s("#E0F2F1", "#00695C", 1), "prod_dr"))
    c.append(cell("sm_dr", "Service Mesh", 20, 125, 100, 40, comp_s(), "prod_dr"))
    c.append(cell("sl_dr", "Serverless", 140, 125, 100, 40, comp_s(), "prod_dr"))
    c.append(cell("metallb_dr", "MetalLB", 260, 125, 90, 40, comp_s(), "prod_dr"))
    c.append(cell("sriov_dr", "SR-IOV", 370, 125, 90, 40, comp_s(), "prod_dr"))
    c.append(cell("etcd_dr", "etcd Backup", 480, 125, 100, 40, comp_s(), "prod_dr"))
    c.append(cell("sub_agent", "<b>Submariner</b><br><b>AGENT</b>", 20, 190, 160, 60, comp_s("#E3F2FD", K8S_BLUE, 1, K8S_BLUE), "prod_dr"))
    c.append(cell("odf_dr_rep", "ODF DR<br>Replication", 200, 190, 110, 50, comp_s("#E0F2F1", "#00695C", 1), "prod_dr"))

    # ── Cross-site connections (at root level) ──
    c.append(edge("e1", "sub_broker", "sub_agent", "IPsec Tunnel\nService Discovery", edge_s(K8S_BLUE)))
    c.append(edge("e2", "odf_dc", "odf_dr", "RBD Mirroring\n(async / sync)", edge_s("#00695C")))
    c.append(edge("e3", "acm_hub", "ocp_dc", "Manages", edge_s(MGMT_ORANGE)))
    c.append(edge("e4", "acm_hub", "ocp_dr", "Manages", edge_s(MGMT_ORANGE)))
    c.append(edge("e5", "acm_hub", "acm_standby", "Failover", dash_s(MGMT_ORANGE)))
    c.append(edge("e6", "acs_central", "acs_secured", "Policies", edge_s(INFRA_RED)))
    c.append(edge("e7", "quay_dc", "quay_dr", "Geo-Replication", dash_s("#3F51B5")))

    # Title
    c.append(cell("title", "<b>Multi-Cluster OpenShift Architecture — IPI Method</b><br><i>4 Clusters across DC and DR Sites • Terraform IaC Automated</i>", 300, -40, 1000, 50, "text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];autosize=1;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"))

    xml = wrap("High-Level Architecture (IPI)", 1600, 780, "\n".join(c))
    save("01-high-level-architecture-ipi.drawio", xml)


# ════════════════════════════════════════════════════════════
# DIAGRAM 2: UPI Architecture Variant
# ════════════════════════════════════════════════════════════
def diagram_2_upi_variant():
    c = []
    # DC Site
    c.append(cell("dc_upi", "<b>Data Center (DC) — UPI</b>", 20, 20, 780, 780, site_s(DC_GREEN)))

    # Infrastructure Layer
    c.append(cell("infra_dc", "<b>Infrastructure Layer</b>", 20, 50, 350, 200, cluster_s(INFRA_RED, INFRA_RED), "dc_upi"))
    c.append(cell("bastion_dc", "<b>Bastion Host</b><br><i>openshift-install</i><br><i>HTTP ignition :8080</i><br><i>PXE/TFTP (optional)</i>", 15, 45, 155, 90, comp_s("#FFF3E0", MGMT_ORANGE, 1), "infra_dc"))
    c.append(cell("haproxy_dc", "<b>HAProxy LB</b><br><i>api:6443 → masters</i><br><i>*.apps:443 → workers</i>", 185, 45, 145, 90, comp_s("#E3F2FD", DR_BLUE, 1), "infra_dc"))
    c.append(cell("boot_dc", "<b>Bootstrap VM</b><br><i>Temporary</i><br><i>Removed after CP up</i>", 65, 145, 145, 45, comp_s(INFRA_RED_BG, INFRA_RED, 1, INFRA_RED), "infra_dc"))

    # DC Workload
    c.append(cell("prod_dc_upi", "<b>Workload Cluster — DC Primary</b>", 20, 270, 350, 200, cluster_s(WORKLOAD_PURPLE), "dc_upi"))
    c.append(cell("cp_dc", "3× Control Plane<br><i>PXE/ISO boot</i>", 15, 45, 150, 50, comp_s(RH_RED, RH_DARK_RED, 1, WHITE), "prod_dc_upi"))
    c.append(cell("wk_dc", "N× Workers<br><i>GPU + ODF + AI</i>", 180, 45, 150, 50, comp_s(), "prod_dc_upi"))
    c.append(cell("sub_b_upi", "<b>Submariner</b><br><b>Broker</b>", 15, 110, 150, 50, comp_s("#E3F2FD", K8S_BLUE, 1, K8S_BLUE), "prod_dc_upi"))

    # DC Management
    c.append(cell("mgmt_dc_upi", "<b>Management Cluster — DC</b>", 20, 490, 350, 160, cluster_s(MGMT_ORANGE), "dc_upi"))
    c.append(cell("acm_h_upi", "ACM Hub", 15, 45, 95, 40, rh_comp(), "mgmt_dc_upi"))
    c.append(cell("acs_c_upi", "ACS Central", 125, 45, 95, 40, comp_s(INFRA_RED_BG, INFRA_RED, 1), "mgmt_dc_upi"))
    c.append(cell("quay_dc_upi", "Quay Enterprise", 235, 45, 95, 40, comp_s("#E8EAF6", "#3F51B5", 1), "mgmt_dc_upi"))

    # DR Site
    c.append(cell("dr_upi", "<b>Disaster Recovery (DR) — UPI</b>", 860, 20, 780, 780, site_s(DR_BLUE)))

    # DR Infra
    c.append(cell("infra_dr", "<b>Infrastructure Layer</b>", 20, 50, 350, 200, cluster_s(INFRA_RED, INFRA_RED), "dr_upi"))
    c.append(cell("bastion_dr", "<b>Bastion Host</b><br><i>openshift-install</i><br><i>HTTP ignition :8080</i>", 15, 45, 155, 90, comp_s("#FFF3E0", MGMT_ORANGE, 1), "infra_dr"))
    c.append(cell("haproxy_dr", "<b>HAProxy LB</b><br><i>api:6443 → masters</i><br><i>*.apps:443 → workers</i>", 185, 45, 145, 90, comp_s("#E3F2FD", DR_BLUE, 1), "infra_dr"))
    c.append(cell("boot_dr", "<b>Bootstrap VM</b><br><i>Temporary</i><br><i>Removed after CP up</i>", 65, 145, 145, 45, comp_s(INFRA_RED_BG, INFRA_RED, 1, INFRA_RED), "infra_dr"))

    # DR Workload
    c.append(cell("prod_dr_upi", "<b>Workload Cluster — DR Secondary</b>", 20, 270, 350, 200, cluster_s(WORKLOAD_PURPLE), "dr_upi"))
    c.append(cell("cp_dr", "3× Control Plane<br><i>PXE/ISO boot</i>", 15, 45, 150, 50, comp_s(RH_RED, RH_DARK_RED, 1, WHITE), "prod_dr_upi"))
    c.append(cell("wk_dr", "N× Workers<br><i>GPU + ODF + AI</i>", 180, 45, 150, 50, comp_s(), "prod_dr_upi"))
    c.append(cell("sub_a_upi", "<b>Submariner</b><br><b>Agent</b>", 15, 110, 150, 50, comp_s("#E3F2FD", K8S_BLUE, 1, K8S_BLUE), "prod_dr_upi"))

    # DR Management
    c.append(cell("mgmt_dr_upi", "<b>Management Cluster — DR</b>", 20, 490, 350, 160, cluster_s(MGMT_ORANGE), "dr_upi"))
    c.append(cell("acm_s_upi", "ACM Standby", 15, 45, 95, 40, comp_s(MGMT_ORANGE_BG, MGMT_ORANGE, 1), "mgmt_dr_upi"))
    c.append(cell("acs_s_upi", "ACS SecuredCluster", 125, 45, 115, 40, comp_s(INFRA_RED_BG, INFRA_RED, 1), "mgmt_dr_upi"))
    c.append(cell("quay_dr_upi", "Quay Enterprise", 255, 45, 95, 40, comp_s("#E8EAF6", "#3F51B5", 1), "mgmt_dr_upi"))

    # Edges
    c.append(edge("ue1", "bastion_dc", "cp_dc", "Ignition configs\nHTTP :8080", edge_s(MGMT_ORANGE)))
    c.append(edge("ue2", "bastion_dc", "wk_dc", "Ignition configs", edge_s(MGMT_ORANGE)))
    c.append(edge("ue3", "bastion_dc", "boot_dc", "bootstrap.ign", edge_s(INFRA_RED)))
    c.append(edge("ue4", "haproxy_dc", "cp_dc", "LB traffic", edge_s(DR_BLUE)))
    c.append(edge("ue5", "haproxy_dc", "wk_dc", "LB traffic", edge_s(DR_BLUE)))
    c.append(edge("ue6", "sub_b_upi", "sub_a_upi", "IPsec Tunnel", edge_s(K8S_BLUE)))
    c.append(edge("ue7", "acm_h_upi", "acm_s_upi", "Failover", dash_s(MGMT_ORANGE)))
    c.append(edge("ue8", "acs_c_upi", "acs_s_upi", "Policies", edge_s(INFRA_RED)))
    c.append(edge("ue9", "quay_dc_upi", "quay_dr_upi", "Geo-Replication", dash_s("#3F51B5")))

    c.append(cell("title2", "<b>Multi-Cluster OpenShift Architecture — UPI Method</b><br><i>Bastion-driven install with HAProxy LB and Bootstrap VMs</i>", 350, -40, 1000, 50, "text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];autosize=1;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"))
    save("02-upi-architecture-variant.drawio", wrap("UPI Architecture Variant", 1700, 860, "\n".join(c)))


# ════════════════════════════════════════════════════════════
# DIAGRAM 3: UPI Install Flow Per Cluster (5 Phases)
# ════════════════════════════════════════════════════════════
def diagram_3_upi_install_flow():
    c = []
    phases = [
        ("p1", "Phase 1: Prerequisites", "#E3F2FD", DR_BLUE, 20, [
            ("dns", "DNS Records", 20, 50, 160, 40),
            ("lb", "HAProxy LB Config\n(Bootstrap backend incl.)", 20, 100, 200, 50),
            ("qm", "Quay Mirror\n(disconnected only)", 20, 160, 180, 45),
        ]),
        ("p2", "Phase 2: Ignition", "#FFF3E0", MGMT_ORANGE, 280, [
            ("ic", "install-config.yaml\nplatform: none", 20, 50, 180, 45),
            ("ign", "openshift-install\ncreate ignition-configs", 20, 105, 200, 45),
            ("http", "Bastion HTTP Server\nServe *.ign on :8080", 20, 160, 200, 45),
        ]),
        ("p3", "Phase 3: Bootstrap + Control Plane", "#FCE4EC", INFRA_RED, 540, [
            ("boot", "Boot Bootstrap VM\nFetch bootstrap.ign", 20, 50, 180, 45),
            ("cpn", "Boot 3 Masters\nFetch master.ign", 20, 105, 180, 45),
            ("bw", "bootstrap_complete\nControl plane self-hosted", 20, 160, 210, 45),
            ("bc", "bootstrap_cleanup\nRemove from LB, Power off", 20, 215, 210, 50),
        ]),
        ("p4", "Phase 4: Workers + CSRs", "#E8F5E9", DC_GREEN, 800, [
            ("wk", "Boot Workers\nFetch worker.ign", 20, 50, 180, 45),
            ("csr", "Approve CSRs\noc adm certificate approve", 20, 105, 210, 45),
            ("cc", "cluster_complete", 20, 160, 140, 40),
        ]),
        ("p5", "Phase 5: Day-2 Operators", "#F3E5F5", WORKLOAD_PURPLE, 1060, [
            ("d2", "NFD, GPU, ODF, AI,\nServiceMesh, Serverless,\nSubmariner, ACM, ACS, Quay\n(per cluster role)", 20, 50, 230, 80),
        ]),
    ]
    for pid, label, bg, stroke, x, items in phases:
        h = max(220, 60 + max(iy + ih for _, _, _, iy, _, ih in items) if items else 220)
        c.append(cell(pid, f"<b>{esc(label)}</b>", x, 60, 250, h, f"swimlane;startSize=35;fillColor={bg};fontColor={stroke};strokeColor={stroke};rounded=1;shadow=1;fontSize=12;fontStyle=1;whiteSpace=wrap;html=1;container=1;collapsible=0;strokeWidth=2;"))
        for iid, ilabel, ix, iy, iw, ih in items:
            sty = comp_s(INFRA_RED_BG, INFRA_RED, 1, INFRA_RED) if iid == "bc" else comp_s()
            c.append(cell(iid, ilabel, ix, iy, iw, ih, sty, pid))

    # Arrows between phases
    c.append(edge("pa1", "p1", "p2", "", edge_s(DARK)))
    c.append(edge("pa2", "p2", "p3", "", edge_s(DARK)))
    c.append(edge("pa3", "p3", "p4", "", edge_s(DARK)))
    c.append(edge("pa4", "p4", "p5", "", edge_s(DARK)))

    c.append(cell("t3", "<b>UPI Install Flow Per Cluster — 5 Phases</b>", 350, 10, 700, 35, "text;html=1;align=center;verticalAlign=middle;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"))
    save("03-upi-install-flow.drawio", wrap("UPI Install Flow", 1350, 420, "\n".join(c)))


# ════════════════════════════════════════════════════════════
# DIAGRAM 4: Network Architecture (CIDRs)
# ════════════════════════════════════════════════════════════
def diagram_4_network_architecture():
    c = []
    # DC Networks
    c.append(cell("dc_nets", "<b>DC Site Networks</b>", 40, 40, 440, 360, site_s(DC_GREEN)))
    nets_dc = [
        ("dc_m", "<b>DC Primary</b><br>Machine: 10.142.41.0/24", 25, 50, 190, 50, DC_GREEN),
        ("dc_p", "<b>DC Primary</b><br>Pod: 10.128.0.0/14", 25, 115, 190, 50, DC_GREEN),
        ("dc_s", "<b>DC Primary</b><br>Service: 172.30.0.0/16", 25, 180, 190, 50, DC_GREEN),
        ("mgmt_dc_m", "<b>Mgmt DC</b><br>Machine: 10.142.42.0/24", 230, 50, 190, 50, MGMT_ORANGE),
        ("mgmt_dc_p", "<b>Mgmt DC</b><br>Pod: 10.136.0.0/14", 230, 115, 190, 50, MGMT_ORANGE),
        ("mgmt_dc_s", "<b>Mgmt DC</b><br>Service: 172.28.0.0/16", 230, 180, 190, 50, MGMT_ORANGE),
    ]
    for nid, nlabel, nx, ny, nw, nh, ncolor in nets_dc:
        c.append(cell(nid, nlabel, nx, ny, nw, nh, comp_s(WHITE, ncolor, 0), "dc_nets"))

    # DR Networks
    c.append(cell("dr_nets", "<b>DR Site Networks</b>", 580, 40, 440, 360, site_s(DR_BLUE)))
    nets_dr = [
        ("dr_m", "<b>DR Secondary</b><br>Machine: 10.143.41.0/24", 25, 50, 190, 50, DR_BLUE),
        ("dr_p", "<b>DR Secondary</b><br>Pod: 10.132.0.0/14", 25, 115, 190, 50, DR_BLUE),
        ("dr_s", "<b>DR Secondary</b><br>Service: 172.31.0.0/16", 25, 180, 190, 50, DR_BLUE),
        ("mgmt_dr_m", "<b>Mgmt DR</b><br>Machine: 10.143.42.0/24", 230, 50, 190, 50, MGMT_ORANGE),
        ("mgmt_dr_p", "<b>Mgmt DR</b><br>Pod: 10.140.0.0/14", 230, 115, 190, 50, MGMT_ORANGE),
        ("mgmt_dr_s", "<b>Mgmt DR</b><br>Service: 172.29.0.0/16", 230, 180, 190, 50, MGMT_ORANGE),
    ]
    for nid, nlabel, nx, ny, nw, nh, ncolor in nets_dr:
        c.append(cell(nid, nlabel, nx, ny, nw, nh, comp_s(WHITE, ncolor, 0), "dr_nets"))

    # WAN link
    c.append(cell("wan", "<b>L3 / WAN Link</b>", 490, 180, 80, 40, comp_s("#FFF8E1", "#F57F17", 1, "#F57F17")))
    c.append(edge("nw1", "dc_nets", "wan", "", edge_s("#F57F17")))
    c.append(edge("nw2", "wan", "dr_nets", "", edge_s("#F57F17")))

    # Note about non-overlapping
    c.append(cell("note", "<b>Non-overlapping CIDRs</b> — Required for Submariner cross-cluster routing without Globalnet", 200, 300, 660, 35, comp_s("#FFF8E1", "#F57F17", 0, "#F57F17"), "dc_nets"))

    c.append(cell("t4", "<b>Network Architecture — Non-Overlapping CIDRs</b>", 250, 5, 600, 30, "text;html=1;align=center;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"))
    save("04-network-architecture.drawio", wrap("Network Architecture", 1080, 430, "\n".join(c)))


# ════════════════════════════════════════════════════════════
# DIAGRAM 5: Submariner Cross-Cluster Networking
# ════════════════════════════════════════════════════════════
def diagram_5_submariner():
    c = []
    # DC Cluster
    c.append(cell("dc_cl", "<b>DC Primary</b>", 40, 60, 380, 280, cluster_s(DC_GREEN)))
    c.append(cell("gw_dc", "<b>Gateway Node</b><br><i>submariner.io/gateway=true</i>", 20, 50, 200, 55, comp_s("#E3F2FD", K8S_BLUE, 1, K8S_BLUE), "dc_cl"))
    c.append(cell("pod_dc", "AI Workload Pod<br>10.128.x.x", 20, 125, 160, 45, comp_s(), "dc_cl"))
    c.append(cell("svc_dc", "ClusterIP Service", 200, 125, 150, 45, comp_s(), "dc_cl"))
    c.append(cell("broker_info", "<b>Broker API :8443</b><br>ServiceDiscovery CR", 20, 190, 200, 50, comp_s("#E8F5E9", DC_GREEN, 1), "dc_cl"))

    # DR Cluster
    c.append(cell("dr_cl", "<b>DR Secondary</b>", 580, 60, 380, 280, cluster_s(DR_BLUE)))
    c.append(cell("gw_dr", "<b>Gateway Node</b><br><i>submariner.io/gateway=true</i>", 20, 50, 200, 55, comp_s("#E3F2FD", K8S_BLUE, 1, K8S_BLUE), "dr_cl"))
    c.append(cell("pod_dr", "AI Workload Pod<br>10.132.x.x", 20, 125, 160, 45, comp_s(), "dr_cl"))
    c.append(cell("svc_dr", "ClusterIP Service", 200, 125, 150, 45, comp_s(), "dr_cl"))

    # IPsec Tunnel (central)
    c.append(cell("ipsec", "<b>IPsec / Libreswan</b><br>Cable Driver<br>UDP 4500 + ESP", 430, 120, 140, 70, comp_s("#E8EAF6", "#3F51B5", 1, "#3F51B5")))

    # Edges
    c.append(edge("se1", "pod_dc", "svc_dc", "", edge_s(DARK)))
    c.append(edge("se2", "svc_dc", "gw_dc", "", edge_s(K8S_BLUE)))
    c.append(edge("se3", "gw_dc", "ipsec", "", edge_s(K8S_BLUE)))
    c.append(edge("se4", "ipsec", "gw_dr", "", edge_s(K8S_BLUE)))
    c.append(edge("se5", "gw_dr", "svc_dr", "", edge_s(K8S_BLUE)))
    c.append(edge("se6", "svc_dr", "pod_dr", "", edge_s(DARK)))

    # Service discovery note
    c.append(cell("sd_note", "<i>&lt;svc&gt;.&lt;ns&gt;.svc.clusterset.local</i><br>DNS-based cross-cluster service resolution", 280, 370, 440, 40, comp_s("#FFF8E1", "#F57F17", 0, "#F57F17")))

    c.append(cell("t5", "<b>Submariner Cross-Cluster Networking</b>", 250, 10, 500, 30, "text;html=1;align=center;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"))
    save("05-submariner-networking.drawio", wrap("Submariner Networking", 1020, 430, "\n".join(c)))


# ════════════════════════════════════════════════════════════
# DIAGRAM 6: ODF Disaster Recovery Replication
# ════════════════════════════════════════════════════════════
def diagram_6_odf_dr():
    c = []
    # DC Storage
    c.append(cell("dc_st", "<b>DC Primary — ODF</b>", 40, 60, 320, 240, cluster_s(DC_GREEN)))
    c.append(cell("sc_dc", "StorageCluster<br>ocs-storagecluster", 20, 50, 180, 45, comp_s("#E0F2F1", "#00695C", 1), "dc_st"))
    c.append(cell("pool_dc", "CephBlockPool<br><i>mirroring: enabled</i>", 20, 110, 180, 45, comp_s("#E0F2F1", "#00695C", 0), "dc_st"))
    c.append(cell("pvc_dc", "PVCs<br>(AI Models, Datasets)", 20, 170, 180, 45, comp_s(), "dc_st"))

    # DR Storage
    c.append(cell("dr_st", "<b>DR Secondary — ODF</b>", 640, 60, 320, 240, cluster_s(DR_BLUE)))
    c.append(cell("sc_dr", "StorageCluster<br>ocs-storagecluster", 20, 50, 180, 45, comp_s("#E0F2F1", "#00695C", 1), "dr_st"))
    c.append(cell("pool_dr", "CephBlockPool<br><i>mirroring: enabled</i>", 20, 110, 180, 45, comp_s("#E0F2F1", "#00695C", 0), "dr_st"))
    c.append(cell("pvc_dr", "PVCs<br>(Replicated Data)", 20, 170, 180, 45, comp_s(), "dr_st"))

    # Control Plane
    c.append(cell("ctrl", "<b>DR Control Plane</b>", 300, 340, 400, 140, cluster_s(MGMT_ORANGE)))
    c.append(cell("odr_op", "ODF DR Operator", 20, 45, 160, 40, comp_s(MGMT_ORANGE_BG, MGMT_ORANGE, 1), "ctrl"))
    c.append(cell("mirror_peer", "MirrorPeer CR", 200, 45, 160, 40, comp_s(MGMT_ORANGE_BG, MGMT_ORANGE, 0), "ctrl"))
    c.append(cell("s3_meta", "S3 Metadata Store", 100, 95, 160, 35, comp_s(), "ctrl"))

    # Edges
    c.append(edge("oe1", "pvc_dc", "pool_dc", "Write", edge_s(DARK)))
    c.append(edge("oe2", "pool_dc", "pool_dr", "RBD Mirror Daemon\nasync: */5 * * * *\nsync: real-time", edge_s("#00695C")))
    c.append(edge("oe3", "pool_dr", "pvc_dr", "", edge_s(DARK)))
    c.append(edge("oe4", "odr_op", "mirror_peer", "", edge_s(MGMT_ORANGE)))
    c.append(edge("oe5", "mirror_peer", "pool_dc", "", dash_s(MGMT_ORANGE)))
    c.append(edge("oe6", "mirror_peer", "pool_dr", "", dash_s(MGMT_ORANGE)))
    c.append(edge("oe7", "odr_op", "s3_meta", "", edge_s(MGMT_ORANGE)))

    # Mode table
    c.append(cell("mode_tbl", "<b>Regional DR</b> (async) — RPO: Minutes — Cross-DC WAN\n<b>Metro DR</b> (sync) — RPO: Zero — &lt; 10ms RTT", 200, 505, 580, 50, comp_s("#FFF8E1", "#F57F17", 0, "#F57F17")))

    c.append(cell("t6", "<b>ODF Disaster Recovery Replication</b>", 280, 10, 450, 30, "text;html=1;align=center;strokeColor=none;fillColor=none;fontSize=18;fontColor=#333333;"))
    save("06-odf-dr-replication.drawio", wrap("ODF DR Replication", 1020, 580, "\n".join(c)))


# ══════════════════════════════════════════
# RUN BATCH 1
# ══════════════════════════════════════════
if __name__ == "__main__":
    print("Batch 1: Architecture Overview Diagrams")
    diagram_1_high_level_ipi()
    diagram_2_upi_variant()
    diagram_3_upi_install_flow()
    diagram_4_network_architecture()
    diagram_5_submariner()
    diagram_6_odf_dr()
    print("Batch 1 complete! (6 diagrams)")
