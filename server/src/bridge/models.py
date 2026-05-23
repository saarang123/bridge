from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

UiKind = Literal["list", "detail", "trigger", "form", "webview", "custom"]
HttpMethod = Literal["GET", "POST"]
ActivityKind = Literal["job", "session"]
ActivityStatus = Literal["queued", "running", "waiting", "complete", "failed", "cancelled"]


@dataclass(frozen=True)
class ActionSpec:
    name: str
    title: str
    ui_kind: UiKind
    method: HttpMethod
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    idempotent: bool
    confirm: bool
    timeout_s: float | None
    handler: Callable[..., Any] = field(repr=False)

    def manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "ui_kind": self.ui_kind,
            "method": self.method,
            "idempotent": self.idempotent,
            "confirm": self.confirm,
            "timeout_s": self.timeout_s,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


@dataclass(frozen=True)
class AppSpec:
    name: str
    title: str
    icon: str
    description: str
    version: str
    actions: dict[str, ActionSpec]
    instance: Any = field(repr=False)

    def manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "icon": self.icon,
            "description": self.description,
            "version": self.version,
            "actions": [
                action.manifest()
                for action in sorted(self.actions.values(), key=lambda item: item.name)
            ],
        }


@dataclass(frozen=True)
class InvocationResult:
    app: str
    action: str
    data: Any

    def envelope(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "data": self.data,
            "meta": {
                "app": self.app,
                "action": self.action,
                "request_id": request_id,
            },
        }


class BridgeError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def envelope(
        self,
        *,
        app: str | None = None,
        action: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            },
            "meta": {
                "app": app,
                "action": action,
                "request_id": request_id,
            },
        }


@dataclass(frozen=True)
class Activity:
    id: str
    kind: ActivityKind
    app: str
    title: str
    status: ActivityStatus
    phase: str
    created_at: str
    updated_at: str
    actions: list[str]
    summary: str = ""
    detail_url: str | None = None

    def manifest(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "app": self.app,
            "title": self.title,
            "status": self.status,
            "phase": self.phase,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "actions": self.actions,
            "detail_url": self.detail_url,
        }
