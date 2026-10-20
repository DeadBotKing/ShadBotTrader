"""Application lifecycle states."""

from __future__ import annotations

from enum import Enum


class ApplicationState(str, Enum):
    """The coarse states an application passes through."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
