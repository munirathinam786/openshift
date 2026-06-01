from openshift_sre_agent.architect import generate_architecture_diagram


def test_generate_architecture_diagram_returns_4_20_grounded_multi_page_pack():
    payload = generate_architecture_diagram(
        prompt=(
            "Design a disconnected multicluster OpenShift fleet with ACM governance, GitOps multitenancy, "
            "backup, DR failover, ODF storage, OADP, observability, and CNV workload support."
        ),
        openshift_state={
            "summary": "Managed fleet with DR posture and GitOps already present.",
            "resource_counts": {
                "managed_clusters": 4,
                "ingress_controllers": 2,
                "degraded_operators": 1,
                "argocd_instances": 2,
                "persistent_volume_claims": 24,
                "backup_locations": 2,
                "dr_policies": 2,
                "virtual_machines": 3,
            },
            "raw": {},
        },
        knowledge_context={"enabled": True, "used": True, "items": []},
    )

    assert payload["planning"]["architect_profile"] == "Senior Red Hat OpenShift architect"
    assert "4.20" in payload["planning"]["version_baseline"]
    expected_page_names = [
        "Holistic OpenShift architecture",
        "Architecture explanation and design narrative",
        "Component architecture and cluster topology",
        "DMZ, firewall, and bastion lanes",
        "ACM, ACS, Quay, ODF, and GitOps placement bands",
        "Rack, node, VLAN, and infrastructure topology",
        "Delivery, resilience, and recovery",
    ]
    assert len(payload["rendering"]["diagram_pages"]) >= len(expected_page_names)
    assert [page["page_name"] for page in payload["rendering"]["diagram_pages"][:7]] == expected_page_names
    assert payload["documents"]["hld"]["target_page_count"] == 50
    assert payload["documents"]["lld"]["target_page_count"] == 100
    assert payload["documents"]["hld"]["estimated_page_count"] >= payload["documents"]["hld"]["target_page_count"]
    assert payload["documents"]["lld"]["estimated_page_count"] >= payload["documents"]["lld"]["target_page_count"]
    assert payload["documents"]["hld"]["page_target_met"] is True
    assert payload["documents"]["lld"]["page_target_met"] is True
    assert payload["artifacts"]["drawio_xml"].count("<diagram") >= len(expected_page_names)
    assert len(payload["artifacts"]["page_previews"]) >= len(expected_page_names)
    assert [page["page_name"] for page in payload["artifacts"]["page_previews"][:7]] == expected_page_names
    assert "img/lib/mscae/OpenShift.svg" in payload["artifacts"]["drawio_xml"]
    assert "DMZ and edge ingress lane" in payload["artifacts"]["drawio_xml"]
    assert "ODF / OADP / data protection band" in payload["artifacts"]["drawio_xml"]
    assert "Architecture explanation and design narrative" in payload["artifacts"]["drawio_xml"]
    assert "OPENSHIFT 4.20+" in payload["artifacts"]["drawio_xml"]
    assert "Senior Red Hat OpenShift architect" in payload["artifacts"]["drawio_xml"]
    assert "Legend" in payload["artifacts"]["drawio_xml"]
    assert payload["artifacts"]["drawio_xml"].count("Legend") == 3
    assert "Trust boundary" in payload["artifacts"]["drawio_xml"]
    assert "Management VLAN switch fabric" in payload["artifacts"]["drawio_xml"]
    assert (
        "shape=mxgraph.kubernetes.icon;prIcon=pod" in payload["artifacts"]["drawio_xml"]
        or "mxgraph.networks.switch" in payload["artifacts"]["drawio_xml"]
        or "mxgraph.office.concepts.firewall" in payload["artifacts"]["drawio_xml"]
    )
    assert payload["artifacts"]["preview_page_name"] == "Holistic OpenShift architecture"


def test_generate_onprem_baremetal_architecture_includes_reference_style_prompt_and_pdf_ready_pages():
    payload = generate_architecture_diagram(
        prompt=(
            "Design an on-prem bare-metal OpenShift architecture with management VLAN, user VLAN, paired firewalls, "
            "console port access, Bond0 over ETH0 and ETH1, ODF Rook Ceph storage, and rack-aligned control plane and workers."
        ),
        openshift_state={
            "summary": "Bare-metal production estate with ODF and shared services.",
            "resource_counts": {
                "managed_clusters": 1,
                "ingress_controllers": 2,
                "degraded_operators": 0,
                "argocd_instances": 1,
                "persistent_volume_claims": 18,
                "backup_locations": 1,
                "dr_policies": 1,
                "virtual_machines": 0,
            },
            "raw": {},
        },
        knowledge_context={"enabled": True, "used": True, "items": []},
    )

    assert payload["planning"]["pattern_id"] == "onprem-baremetal"
    assert "management VLAN" in payload["planning"]["normalized_prompt"]
    assert "Bond0" in payload["planning"]["normalized_prompt"]
    assert payload["rendering"]["diagram_pages"][0]["layout_mode"] == "onprem-holistic"
    assert "Management VLAN switch fabric" in payload["artifacts"]["drawio_xml"]
    assert "User VLAN switch fabric" in payload["artifacts"]["drawio_xml"]
    assert "ODF / Rook-Ceph data path" in payload["artifacts"]["drawio_xml"]
    assert "shape=mxgraph.veeam2.network_card" in payload["artifacts"]["drawio_xml"]
    assert all("png_base64" in page for page in payload["artifacts"]["page_previews"])


def test_generate_architecture_diagram_preserves_exact_reference_drawio_when_requested():
    reference_drawio = (
        '<mxfile host="app.diagrams.net" version="29.0.3">'
        '<diagram id="page-1" name="Page-1">'
        '<mxGraphModel dx="1106" dy="812" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">'
        '<root>'
        '<mxCell id="0" />'
        '<mxCell id="1" parent="0" />'
        '<mxCell id="2" value="Exact replica" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">'
        '<mxGeometry x="160" y="120" width="240" height="80" as="geometry" />'
        '</mxCell>'
        '</root>'
        '</mxGraphModel>'
        '</diagram>'
        '</mxfile>'
    )

    payload = generate_architecture_diagram(
        prompt="Preserve the uploaded ocp.drawio without changing the diagram.",
        openshift_state={
            "summary": "Reference-driven bare-metal review run.",
            "resource_counts": {"managed_clusters": 1},
            "raw": {},
        },
        reference_diagrams=[
            {
                "filename": "ocp.drawio",
                "drawio_xml": reference_drawio,
                "use_as_canonical": True,
                "preserve_exact": True,
                "mode": "exact",
            }
        ],
        knowledge_context={"enabled": True, "used": False, "items": []},
    )

    assert payload["reference_diagrams_used"] == 1
    assert payload["artifacts"]["drawio_xml"] == reference_drawio
    assert payload["artifacts"]["preview_page_name"] == "Page-1"
    assert payload["artifacts"]["filenames"]["drawio"] == "ocp.drawio"
    assert payload["rendering"]["diagram_pages"][0]["layout_mode"] == "reference-exact"
    assert payload["artifacts"]["page_previews"][0]["page_name"] == "Page-1"
    assert payload["artifacts"]["page_previews"][0]["svg"]
