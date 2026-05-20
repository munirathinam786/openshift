from __future__ import annotations

import shlex
from typing import Iterable

READ_ONLY_OC_VERBS = {"get", "describe", "logs", "whoami", "api-resources", "api-versions", "version", "explain", "adm"}
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


def parse_oc_cli_command(command: str) -> list[str]:
    """Parse and validate a minimal ``oc <verb> ...`` command line."""

    ensure_no_shell_operators(command)
    parts = shlex.split(command)
    if len(parts) < 2 or parts[0] not in ("oc", "kubectl"):
        raise SafetyError("Command must start with 'oc <verb>' or 'kubectl <verb>'")
    return parts


def oc_cli_verb(parts: Iterable[str]) -> str:
    """Extract the first non-flag verb token from an oc/kubectl command."""

    parts = list(parts)
    if len(parts) < 2:
        raise SafetyError("CLI command is incomplete")
    for token in parts[1:]:
        if token.startswith("-"):
            continue
        return token
    raise SafetyError("CLI verb was not found")


def ensure_read_only_oc_cli(command: str) -> list[str]:
    """Validate that *command* is an oc/kubectl invocation using a read-only verb."""

    parts = parse_oc_cli_command(command)
    verb = oc_cli_verb(parts)
    if verb not in READ_ONLY_OC_VERBS:
        raise SafetyError(
            f"Only read-only oc/kubectl operations are allowed. Rejected verb: {verb}"
        )
    return parts


# Legacy aliases for backward compatibility with tests
READ_ONLY_AWS_VERBS = READ_ONLY_OC_VERBS
ensure_read_only_aws_cli = ensure_read_only_oc_cli
