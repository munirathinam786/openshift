"""Integration tests using moto to mock AWS services."""
from __future__ import annotations

import os

import boto3
import pytest

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")

from aws_sre_agent.config import Settings
from aws_sre_agent.tools import AwsSreToolkit

try:
    from moto import mock_aws
except ImportError:
    pytest.skip("moto not installed", allow_module_level=True)


def _settings() -> Settings:
    return Settings(
        ollama_base_url="http://localhost:11434",
        local_model_name="test-model",
        aws_region="us-east-1",
        aws_profile=None,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        aws_session_token="testing",
        aws_ca_bundle=None,
        aws_verify_ssl=True,
        allow_mutating_actions=False,
        agent_max_steps=8,
    )


@mock_aws
def test_list_ec2_instances_with_moto() -> None:
    """Create a fake EC2 instance and verify the tool returns it."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
    )

    toolkit = AwsSreToolkit(_settings())
    result = toolkit.invoke("list_ec2_instances", {"state_filter": "running"})

    assert result["count"] >= 1
    assert any(inst["state"] == "running" for inst in result.get("instances", []))


@mock_aws
def test_list_ec2_instances_empty() -> None:
    """When no instances exist the tool should return count 0."""
    toolkit = AwsSreToolkit(_settings())
    result = toolkit.invoke("list_ec2_instances", {})
    assert result["count"] == 0


@mock_aws
def test_list_ebs_volumes_with_moto() -> None:
    """Create a fake EBS volume and verify the tool returns it."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=10, VolumeType="gp2")

    toolkit = AwsSreToolkit(_settings())
    result = toolkit.invoke("list_ebs_volumes", {})

    assert result["count"] >= 1


@mock_aws
def test_list_vpc_inventory_with_moto() -> None:
    """Default VPC should be present in moto."""
    toolkit = AwsSreToolkit(_settings())
    result = toolkit.invoke("list_vpc_inventory", {})

    assert "vpc_count" in result or "count" in result
