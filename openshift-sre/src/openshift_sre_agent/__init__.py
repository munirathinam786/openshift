"""OpenShift SRE local-model agent.

Keep package import side effects lightweight so utility modules like
``config`` and ``persistence`` can be imported without eagerly pulling in
the full Kubernetes-backed agent stack.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
	from .agent import OpenShiftSreAgent

__all__ = ["OpenShiftSreAgent"]


def __getattr__(name: str) -> Any:
	if name == "OpenShiftSreAgent":
		from .agent import OpenShiftSreAgent

		return OpenShiftSreAgent
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
