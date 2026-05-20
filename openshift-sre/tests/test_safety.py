from openshift_sre_agent.safety import SafetyError, ensure_read_only_oc_cli


def test_allow_read_only_get_command() -> None:
    parts = ensure_read_only_oc_cli("oc get pods --namespace openshift-monitoring")
    assert parts[:3] == ["oc", "get", "pods"]


def test_block_mutating_command() -> None:
    try:
        ensure_read_only_oc_cli("oc delete pod my-pod --namespace default")
    except SafetyError as error:
        assert "read-only" in str(error)
    else:
        raise AssertionError("Mutating oc CLI command should be rejected")


def test_block_shell_operator() -> None:
    try:
        ensure_read_only_oc_cli("oc get pods && whoami")
    except SafetyError as error:
        assert "Blocked shell operator" in str(error)
    else:
        raise AssertionError("Shell operator should be rejected")
