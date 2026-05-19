from __future__ import annotations

import shlex
from typing import Iterable

READ_ONLY_AWS_VERBS = {"describe", "get", "head", "list"}
BLOCKED_SHELL_TOKENS = {";", "&&", "||", "|", ">", ">>", "<", "`"}


class SafetyError(ValueError):
    """Raised when a command or action violates the safety policy."""


def ensure_no_shell_operators(command: str) -> None:
    """Reject shell chaining, redirection, and multi-line command input."""

    for token in BLOCKED_SHELL_TOKENS:
        if token in command:
            raise SafetyError(f"Blocked shell operator detected: {token}")
    if "\n" in command:
        raise SafetyError("Multi-line commands are not allowed")


def parse_aws_cli_command(command: str) -> list[str]:
    """Parse and validate a minimal ``aws <service> <operation>`` command line."""

    ensure_no_shell_operators(command)
    parts = shlex.split(command)
    if len(parts) < 3 or parts[0] != "aws":
        raise SafetyError("Command must start with 'aws <service> <operation>'")
    return parts


def aws_cli_operation(parts: Iterable[str]) -> str:
    """Extract the first non-flag AWS CLI operation token from *parts*."""

    parts = list(parts)
    if len(parts) < 3:
        raise SafetyError("AWS CLI command is incomplete")
    for token in parts[2:]:
        if token.startswith("-"):
            continue
        return token
    raise SafetyError("AWS CLI operation was not found")


def ensure_read_only_aws_cli(command: str) -> list[str]:
    """Validate that *command* is an AWS CLI invocation using a read-only verb."""

    parts = parse_aws_cli_command(command)
    operation = aws_cli_operation(parts)
    verb = operation.split("-", maxsplit=1)[0].lower()
    if verb not in READ_ONLY_AWS_VERBS:
        raise SafetyError(
            f"Only read-only AWS CLI operations are allowed. Rejected operation: {operation}"
        )
    return parts
