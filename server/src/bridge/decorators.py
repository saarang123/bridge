from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from bridge.models import HttpMethod, UiKind


@dataclass(frozen=True)
class ActionDeclaration:
    name: str | None
    title: str | None
    ui_kind: UiKind
    method: HttpMethod | None
    description: str
    idempotent: bool | None
    confirm: bool
    timeout_s: float | None


@dataclass(frozen=True)
class MiniAppDeclaration:
    name: str
    title: str | None
    icon: str
    description: str
    version: str


def action(
    *,
    ui_kind: UiKind,
    name: str | None = None,
    title: str | None = None,
    method: HttpMethod | None = None,
    description: str = "",
    idempotent: bool | None = None,
    confirm: bool = False,
    timeout_s: float | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn.__bridge_action__ = ActionDeclaration(
            name=name,
            title=title,
            ui_kind=ui_kind,
            method=method,
            description=description,
            idempotent=idempotent,
            confirm=confirm,
            timeout_s=timeout_s,
        )
        return fn

    return decorate


def mini_app(
    name: str,
    *,
    title: str | None = None,
    icon: str = "square.grid.2x2",
    description: str = "",
    version: str = "0.1.0",
) -> Callable[[type[Any]], type[Any]]:
    def decorate(cls: type[Any]) -> type[Any]:
        cls.__bridge_mini_app__ = MiniAppDeclaration(
            name=name,
            title=title,
            icon=icon,
            description=description,
            version=version,
        )
        return cls

    return decorate
