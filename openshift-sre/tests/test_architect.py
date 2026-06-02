from openshift_sre_agent.architect import generate_architecture_diagram, get_architect_diagram_templates, get_official_red_hat_drawio_assets


def test_architect_template_catalog_includes_cloud_and_platform_variants():
    template_ids = {item["id"] for item in get_architect_diagram_templates()}

    assert "rosa-aws" in template_ids
    assert "aro-azure" in template_ids
    assert "openshift-openstack" in template_ids
    assert "ibm-z-linuxone" in template_ids


def test_architect_template_catalog_includes_portfolio_derived_openshift_skills():
    template_ids = {item["id"] for item in get_architect_diagram_templates()}

    assert "openshift-external-auth" in template_ids
    assert "openshift-sap-clean-core-rosa" in template_ids
    assert "openshift-cloud-sovereignty" in template_ids
    assert "openshift-cloud-native-apps" in template_ids
    assert "openshift-telco-5g" in template_ids
    assert "openshift-event-driven-automation" in template_ids
    assert "openshift-model-as-a-service" in template_ids
    assert "openshift-ai-self-service" in template_ids
    assert "openshift-virtualization-portworx" in template_ids
    assert "openshift-virtualization-trilio" in template_ids


def test_official_red_hat_drawio_assets_include_offline_bundle_paths():
    assets = get_official_red_hat_drawio_assets()

    assert assets["source_url"] == "https://www.redhat.com/architect/portfolio/tool/index.html"
    assert assets["offline_bundle_repo_path"] == "docs/assets/redhat-drawio"
    assert assets["offline_bundle_container_path"] == "/app/redhat-drawio"
    assert assets["offline_bundle_guide_path"] == "/guide/assets/redhat-drawio"
    assert any(item["guide_url"] == "/guide/assets/redhat-drawio/application-icons.mxlibrary" for item in assets["offline_libraries"])
    assert any(item["id"] == "rh-logical-diagrams" and item["preload_by_default"] is True for item in assets["offline_libraries"])
    assert any(item["label"] == "Schematic Diagram" for item in assets["template_families"])
    assert any(item["label"] == "Infrastructure Icons" for item in assets["icon_libraries"])


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
    assert "fillColor=#ECFDF5;strokeColor=#005F4B" in payload["artifacts"]["drawio_xml"]
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


def test_generate_architecture_diagram_uses_reference_as_holistic_quality_floor_when_not_exact():
    reference_drawio = (
        '<mxfile host="app.diagrams.net" version="29.0.3">'
        '<diagram id="page-1" name="Page-1">'
        '<mxGraphModel dx="1106" dy="812" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">'
        '<root>'
        '<mxCell id="0" />'
        '<mxCell id="1" parent="0" />'
        '<mxCell id="2" value="Reference holistic baseline" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">'
        '<mxGeometry x="160" y="120" width="320" height="80" as="geometry" />'
        '</mxCell>'
        '</root>'
        '</mxGraphModel>'
        '</diagram>'
        '</mxfile>'
    )

    payload = generate_architecture_diagram(
        prompt=(
            "Design an on-prem bare-metal OpenShift architecture with management VLAN, user VLAN, paired firewalls, "
            "console port access, Bond0 over ETH0 and ETH1, ODF Rook Ceph storage, and rack-aligned control plane and workers."
        ),
        openshift_state={
            "summary": "Reference-guided bare-metal review run.",
            "resource_counts": {"managed_clusters": 1, "ingress_controllers": 2, "persistent_volume_claims": 18},
            "raw": {},
        },
        reference_diagrams=[
            {
                "filename": "ocp.drawio",
                "drawio_xml": reference_drawio,
                "mode": "reference",
            }
        ],
        knowledge_context={"enabled": True, "used": False, "items": []},
    )

    assert payload["reference_diagrams_used"] == 1
    assert payload["rendering"]["diagram_pages"][0]["layout_mode"] == "reference-guided-holistic"
    assert payload["rendering"]["diagram_pages"][0]["page_name"] == "Holistic OpenShift architecture"
    assert payload["artifacts"]["page_previews"][0]["page_name"] == "Holistic OpenShift architecture"
    assert "Reference holistic baseline" in payload["artifacts"]["drawio_xml"]
    assert "Architecture explanation and design narrative" in payload["artifacts"]["drawio_xml"]


def test_generate_architecture_diagram_detects_platform_specific_openshift_patterns():
    scenarios = [
        {
            "prompt": "Design a ROSA on AWS platform with STS, customer-owned VPC, Route 53, VPC endpoints, and ALB-backed ingress.",
            "expected_pattern": "rosa-aws",
            "expected_prompt_fragment": "customer-owned VPCs",
            "expected_diagram_fragment": "ROSA service and OCM",
        },
        {
            "prompt": "Create an Azure Red Hat OpenShift architecture with Microsoft Entra, Azure RBAC, private API exposure, and Azure Monitor.",
            "expected_pattern": "aro-azure",
            "expected_prompt_fragment": "landing-zone-aware networking",
            "expected_diagram_fragment": "Microsoft Entra and service identity",
        },
        {
            "prompt": "Build OpenShift on OpenStack with Neutron networks, Octavia load balancing, API VIP, ingress VIP, and Cinder storage.",
            "expected_pattern": "openshift-openstack",
            "expected_prompt_fragment": "Neutron network boundaries",
            "expected_diagram_fragment": "Neutron networks and VIP model",
        },
        {
            "prompt": "Design OpenShift on IBM Z LinuxONE with s390x nodes, z/VM hosting, mirrored registry paths, and agent-based install.",
            "expected_pattern": "ibm-z-linuxone",
            "expected_prompt_fragment": "s390x topology",
            "expected_diagram_fragment": "OpenShift s390x cluster",
        },
    ]

    for scenario in scenarios:
        payload = generate_architecture_diagram(
            prompt=scenario["prompt"],
            openshift_state={
                "summary": "Platform-specific OpenShift architecture validation run.",
                "resource_counts": {"managed_clusters": 1, "ingress_controllers": 1},
                "raw": {},
            },
            knowledge_context={"enabled": True, "used": False, "items": []},
        )

        assert payload["planning"]["pattern_id"] == scenario["expected_pattern"]
        assert scenario["expected_prompt_fragment"] in payload["planning"]["normalized_prompt"]
        assert scenario["expected_diagram_fragment"] in payload["artifacts"]["drawio_xml"]
        assert payload["rendering"]["diagram_pages"][0]["page_name"] == "Holistic OpenShift architecture"


def test_generate_architecture_diagram_detects_portfolio_derived_openshift_patterns():
    scenarios = [
        {
            "prompt": "Design OpenShift external authentication with Keycloak OIDC, CLI and web-console access, RBAC mapping, and coverage for ROSA HCP and self-managed clusters.",
            "expected_pattern": "openshift-external-auth",
            "expected_prompt_fragment": "OIDC token issuance",
            "expected_diagram_fragment": "External OIDC provider",
        },
        {
            "prompt": "Create a sovereign cloud on OpenShift Platform Plus with separated management and workload clusters, zero trust, GitOps, and workload identity manager.",
            "expected_pattern": "openshift-cloud-sovereignty",
            "expected_prompt_fragment": "digital-sovereignty control objectives",
            "expected_diagram_fragment": "Management sovereignty cluster",
        },
        {
            "prompt": "Build a cloud-native application platform on OpenShift with local and remote containers, source-to-image, Quay image promotion, and dev test prod lanes.",
            "expected_pattern": "openshift-cloud-native-apps",
            "expected_prompt_fragment": "Quay image promotion",
            "expected_diagram_fragment": "Enterprise image registry",
        },
        {
            "prompt": "Design a telco 5G core on OpenShift with CNFs including UPF AMF SMF NRF, plus AMQ, Service Mesh, ACM, and ODF.",
            "expected_pattern": "openshift-telco-5g",
            "expected_prompt_fragment": "CNF-based OpenShift pattern",
            "expected_diagram_fragment": "5G CNF workload domain",
        },
        {
            "prompt": "Create event-driven automation on OpenShift with AMQ broker, decision services, task creation, and Ansible automation execution.",
            "expected_pattern": "openshift-event-driven-automation",
            "expected_prompt_fragment": "event-driven automation end to end",
            "expected_diagram_fragment": "Message broker and event bus",
        },
        {
            "prompt": "Create Model as a Service on OpenShift AI with 3scale, SSO, vLLM inference servers, multiple models, governance, and chargeback.",
            "expected_pattern": "openshift-model-as-a-service",
            "expected_prompt_fragment": "Model as a Service on OpenShift AI",
            "expected_diagram_fragment": "Inference servers and model catalog",
        },
        {
            "prompt": "Design self-service AI on OpenShift with Developer Hub, OpenShift AI, golden paths for data scientists, model training, and model serving.",
            "expected_pattern": "openshift-ai-self-service",
            "expected_prompt_fragment": "self-service AI platform engineering",
            "expected_diagram_fragment": "Developer Hub self-service portal",
        },
        {
            "prompt": "Design SAP clean core on ROSA with S/4HANA extensions, API-first integration, Application Foundations, and DevOps delivery.",
            "expected_pattern": "openshift-sap-clean-core-rosa",
            "expected_prompt_fragment": "SAP clean-core modernization on ROSA",
            "expected_diagram_fragment": "API-first integration layer",
        },
    ]

    for scenario in scenarios:
        payload = generate_architecture_diagram(
            prompt=scenario["prompt"],
            openshift_state={
                "summary": "Portfolio-derived OpenShift architecture validation run.",
                "resource_counts": {"managed_clusters": 1, "ingress_controllers": 1},
                "raw": {},
            },
            knowledge_context={"enabled": True, "used": False, "items": []},
        )

        assert payload["planning"]["pattern_id"] == scenario["expected_pattern"]
        assert scenario["expected_prompt_fragment"] in payload["planning"]["normalized_prompt"]
        assert scenario["expected_diagram_fragment"] in payload["artifacts"]["drawio_xml"]


def test_generate_architecture_diagram_renders_portfolio_source_aligned_diagram_elements():
    scenarios = [
        {
            "prompt": "Design OpenShift external authentication with Keycloak OIDC, CLI and web-console access, RBAC mapping, and coverage for ROSA HCP, ARO HCP, and self-managed clusters.",
            "expected_fragments": [
                "ROSA HCP, ARO HCP, and self-managed paths",
                "Bootstrap access and admin credentials",
                "deployment path",
            ],
        },
        {
            "prompt": "Build a cloud-native application platform on OpenShift with local and remote containers, source-to-image, Quay image promotion, and dev test prod lanes.",
            "expected_fragments": [
                "Git source and trigger path",
                "Transient build registry",
                "Dev, test, and prod promotion lanes",
            ],
        },
        {
            "prompt": "Design a telco 5G core on OpenShift with CNFs including UPF AMF SMF NRF, plus AMQ, Service Mesh, ACM, and ODF.",
            "expected_fragments": [
                "External services and network infrastructure",
                "Supplementary 5G services",
                "SBA / exposure flow",
            ],
        },
        {
            "prompt": "Create event-driven automation on OpenShift with AMQ broker, decision services, task creation, and Ansible automation execution.",
            "expected_fragments": [
                "Task and ticket workflow store",
                "Execution and results stores",
                "audit / feedback",
            ],
        },
    ]

    for scenario in scenarios:
        payload = generate_architecture_diagram(
            prompt=scenario["prompt"],
            openshift_state={
                "summary": "Portfolio diagram fidelity validation run.",
                "resource_counts": {"managed_clusters": 1, "ingress_controllers": 1},
                "raw": {},
            },
            knowledge_context={"enabled": True, "used": False, "items": []},
        )

        for expected_fragment in scenario["expected_fragments"]:
            assert expected_fragment in payload["artifacts"]["drawio_xml"]


def test_generate_architecture_diagram_adds_portfolio_appendix_sections_to_lld():
    scenarios = [
        {
            "prompt": "Design OpenShift external authentication with Keycloak OIDC, CLI and web-console access, RBAC mapping, and coverage for ROSA HCP and self-managed clusters.",
            "expected_titles": [
                "External authentication appendix — deployment path and token-flow model",
                "External authentication appendix — RBAC and access workflow matrix",
            ],
            "expected_body_fragment": "ROSA HCP, ARO HCP, and self-managed OpenShift 4.20+",
        },
        {
            "prompt": "Create a sovereign cloud on OpenShift Platform Plus with separated management and workload clusters, zero trust, GitOps, and workload identity manager.",
            "expected_titles": [
                "Cloud sovereignty appendix — sovereignty control plane and workload separation",
                "Cloud sovereignty appendix — digital sovereignty control matrix",
            ],
            "expected_body_fragment": "technical sovereignty, operational sovereignty, assurance sovereignty, and data sovereignty",
        },
        {
            "prompt": "Design a telco 5G core on OpenShift with CNFs including UPF AMF SMF NRF, plus AMQ, Service Mesh, ACM, and ODF.",
            "expected_titles": [
                "Telco 5G appendix — CNF and platform service topology",
                "Telco 5G appendix — 5G function matrix",
            ],
            "expected_body_fragment": "control-plane, user-plane, supplementary, and management functions",
        },
        {
            "prompt": "Create Model as a Service on OpenShift AI with 3scale, SSO, vLLM inference servers, multiple models, governance, and chargeback.",
            "expected_titles": [
                "MaaS appendix — OpenShift AI service stack and governance",
                "MaaS appendix — model service catalog matrix",
            ],
            "expected_body_fragment": "provider of AI services, not just GPU infrastructure",
        },
    ]

    for scenario in scenarios:
        payload = generate_architecture_diagram(
            prompt=scenario["prompt"],
            openshift_state={
                "summary": "Portfolio appendix validation run.",
                "resource_counts": {"managed_clusters": 1, "ingress_controllers": 1, "persistent_volume_claims": 2},
                "raw": {},
            },
            knowledge_context={"enabled": True, "used": False, "items": []},
        )

        section_titles = [section["title"] for section in payload["documents"]["lld"]["sections"]]
        section_bodies = ["\n".join(section["body"]) for section in payload["documents"]["lld"]["sections"]]

        for expected_title in scenario["expected_titles"]:
            assert expected_title in section_titles
        assert any(scenario["expected_body_fragment"] in body for body in section_bodies)


def test_generate_architecture_diagram_adds_platform_specific_appendix_sections_to_lld():
    scenarios = [
        {
            "prompt": "Design a ROSA on AWS platform with STS, customer-owned VPC, Route 53, VPC endpoints, and ALB-backed ingress.",
            "expected_titles": [
                "ROSA appendix — AWS account, tenancy, and service ownership",
                "ROSA appendix — AWS endpoints, Route 53, and ingress implementation",
            ],
            "expected_body_fragment": "Implementation matrix detail: list every endpoint service",
        },
        {
            "prompt": "Create an Azure Red Hat OpenShift architecture with Microsoft Entra, Azure RBAC, private API exposure, and Azure Monitor.",
            "expected_titles": [
                "ARO appendix — Azure landing zone, subscription, and resource placement",
                "ARO appendix — RBAC, Entra identity, and VNet design",
            ],
            "expected_body_fragment": "Implementation matrix detail: enumerate RBAC roles",
        },
        {
            "prompt": "Build OpenShift on OpenStack with Neutron networks, Octavia load balancing, API VIP, ingress VIP, and Cinder storage.",
            "expected_titles": [
                "OpenStack appendix — VIP, API, ingress, and Neutron network matrix",
                "OpenStack appendix — Cinder, storage, and implementation matrix",
            ],
            "expected_body_fragment": "Implementation matrix detail: capture per-service owner",
        },
        {
            "prompt": "Design OpenShift on IBM Z LinuxONE with s390x nodes, z/VM hosting, mirrored registry paths, and agent-based install.",
            "expected_titles": [
                "IBM Z appendix — bastion, z/VM, and hosting topology",
                "IBM Z appendix — storage, mirrored content, and install-runbook",
            ],
            "expected_body_fragment": "Low-level runbook detail: include preflight checks",
        },
    ]

    for scenario in scenarios:
        payload = generate_architecture_diagram(
            prompt=scenario["prompt"],
            openshift_state={
                "summary": "Platform appendix validation run.",
                "resource_counts": {"managed_clusters": 1, "ingress_controllers": 1, "persistent_volume_claims": 4},
                "raw": {},
            },
            knowledge_context={"enabled": True, "used": False, "items": []},
        )

        section_titles = [section["title"] for section in payload["documents"]["lld"]["sections"]]
        section_bodies = ["\n".join(section["body"]) for section in payload["documents"]["lld"]["sections"]]

        for expected_title in scenario["expected_titles"]:
            assert expected_title in section_titles
        assert any(scenario["expected_body_fragment"] in body for body in section_bodies)


def test_generate_architecture_diagram_adds_platform_specific_matrix_sections_to_lld():
    scenarios = [
        {
            "prompt": "Design a ROSA on AWS platform with STS, customer-owned VPC, Route 53, VPC endpoints, and ALB-backed ingress.",
            "expected_titles": [
                "ROSA appendix — AWS endpoint inventory table",
                "ROSA appendix — Route 53 and ingress ownership matrix",
                "ROSA appendix — account, VPC, and subnet ownership table",
            ],
            "expected_fragments": [
                "| AWS service | Endpoint type | Primary use | Expected path | Owner | Validation |",
                "| Asset / decision | Implementation pattern | Primary owner | Supporting owner | Evidence / check |",
                "| Scope | Representative assets | Recommended boundary | Owner | Change path |",
                "Hosted control plane via AWS PrivateLink",
                "wildcard CNAME to canonical router hostname",
            ],
        },
        {
            "prompt": "Create an Azure Red Hat OpenShift architecture with Microsoft Entra, Azure RBAC, private API exposure, and Azure Monitor.",
            "expected_titles": [
                "ARO appendix — Azure RBAC role matrix",
                "ARO appendix — landing zone resource placement table",
                "ARO appendix — VNet, subnet, and peering matrix",
            ],
            "expected_fragments": [
                "| Role / identity | Azure scope | OpenShift scope | Core responsibilities | Control expectation |",
                "| Landing-zone layer | Typical Azure scope | Representative resources | Why it lives here | Owner |",
                "| Network element | Placement | Minimum expectation | Traffic / dependency | Validation |",
            ],
        },
        {
            "prompt": "Build OpenShift on OpenStack with Neutron networks, Octavia load balancing, API VIP, ingress VIP, and Cinder storage.",
            "expected_titles": [
                "OpenStack appendix — VIP matrix",
                "OpenStack appendix — Neutron network mapping table",
                "OpenStack appendix — Cinder storage dependency matrix",
            ],
            "expected_fragments": [
                "| VIP / endpoint | Typical function | Delivery model | Owner | Validation |",
                "| Neutron construct | OpenShift use | Example placement | Owner | Evidence |",
                "| Capability | Storage dependency | Why it matters | Owner | Recovery / validation |",
            ],
        },
        {
            "prompt": "Design OpenShift on IBM Z LinuxONE with s390x nodes, z/VM hosting, mirrored registry paths, and agent-based install.",
            "expected_titles": [
                "IBM Z appendix — bastion workflow matrix",
                "IBM Z appendix — z/VM guest and LPAR inventory table",
                "IBM Z appendix — install-runbook step matrix",
            ],
            "expected_fragments": [
                "| Workflow step | Bastion responsibility | Input / output | Primary owner | Validation |",
                "| Hosting element | Representative role | Key dependencies | Owner | Operational note |",
                "| Phase | Key action | Success signal | Rollback / retry point | Owner |",
            ],
        },
    ]

    for scenario in scenarios:
        payload = generate_architecture_diagram(
            prompt=scenario["prompt"],
            openshift_state={
                "summary": "Platform matrix validation run.",
                "resource_counts": {"managed_clusters": 1, "ingress_controllers": 1, "persistent_volume_claims": 4},
                "raw": {},
            },
            knowledge_context={"enabled": True, "used": False, "items": []},
        )

        section_titles = [section["title"] for section in payload["documents"]["lld"]["sections"]]
        section_bodies = ["\n".join(section["body"]) for section in payload["documents"]["lld"]["sections"]]

        for expected_title in scenario["expected_titles"]:
            assert expected_title in section_titles
        for expected_fragment in scenario["expected_fragments"]:
            assert any(expected_fragment in body for body in section_bodies)
