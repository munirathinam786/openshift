from aws_sre_agent.safety import SafetyError, ensure_read_only_aws_cli


def test_allow_read_only_describe_command() -> None:
    parts = ensure_read_only_aws_cli("aws ec2 describe-instances --region us-east-1")
    assert parts[:3] == ["aws", "ec2", "describe-instances"]


def test_block_mutating_command() -> None:
    try:
        ensure_read_only_aws_cli("aws ec2 terminate-instances --instance-ids i-123")
    except SafetyError as error:
        assert "read-only" in str(error)
    else:
        raise AssertionError("Mutating AWS CLI command should be rejected")


def test_block_shell_operator() -> None:
    try:
        ensure_read_only_aws_cli("aws ec2 describe-instances && whoami")
    except SafetyError as error:
        assert "Blocked shell operator" in str(error)
    else:
        raise AssertionError("Shell operator should be rejected")
