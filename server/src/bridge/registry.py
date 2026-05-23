from __future__ import annotations

import dataclasses
import inspect
import re
from typing import Any, get_type_hints

from bridge.decorators import ActionDeclaration, MiniAppDeclaration
from bridge.models import ActionSpec, AppSpec, BridgeError, InvocationResult
from bridge.schema import callable_input_schema, callable_output_schema

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
UI_KINDS = {"list", "detail", "trigger", "form", "webview", "custom"}
HTTP_METHODS = {"GET", "POST"}


class Registry:
    def __init__(self) -> None:
        self._apps: dict[str, AppSpec] = {}

    def register(self, app_cls: type[Any], *args: Any, **kwargs: Any) -> AppSpec:
        declaration = getattr(app_cls, "__bridge_mini_app__", None)
        if declaration is None:
            raise BridgeError(
                "invalid_mini_app",
                f"{app_cls.__name__} is missing @mini_app.",
            )

        if not isinstance(declaration, MiniAppDeclaration):
            raise BridgeError("invalid_mini_app", "Invalid mini-app declaration.")

        self._validate_name(declaration.name, "mini-app")
        if declaration.name in self._apps:
            raise BridgeError(
                "duplicate_mini_app",
                f"Mini-app already registered: {declaration.name}.",
            )

        instance = app_cls(*args, **kwargs)
        actions = self._collect_actions(instance)
        app = AppSpec(
            name=declaration.name,
            title=declaration.title or _titleize(declaration.name),
            icon=declaration.icon,
            description=declaration.description,
            version=declaration.version,
            actions=actions,
            instance=instance,
        )
        self._apps[app.name] = app
        return app

    def apps(self) -> list[AppSpec]:
        return [self._apps[name] for name in sorted(self._apps)]

    def get_app(self, app_name: str) -> AppSpec:
        try:
            return self._apps[app_name]
        except KeyError as exc:
            raise BridgeError("not_found", f"Unknown mini-app: {app_name}.") from exc

    def manifest(self) -> dict[str, Any]:
        return {"apps": [app.manifest() for app in self.apps()]}

    def app_manifest(self, app_name: str) -> dict[str, Any]:
        return self.get_app(app_name).manifest()

    def invoke(
        self,
        app_name: str,
        action_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> InvocationResult:
        app = self.get_app(app_name)
        try:
            action = app.actions[action_name]
        except KeyError as exc:
            raise BridgeError(
                "not_found",
                f"Unknown action: {app_name}.{action_name}.",
            ) from exc

        arguments = self._coerce_arguments(action.handler, arguments or {})
        data = action.handler(**arguments)
        return InvocationResult(app=app_name, action=action_name, data=_serialize(data))

    def _collect_actions(self, instance: Any) -> dict[str, ActionSpec]:
        actions: dict[str, ActionSpec] = {}

        for attr_name in dir(instance):
            handler = getattr(instance, attr_name)
            declaration = getattr(handler, "__bridge_action__", None)
            if declaration is None:
                continue
            if not isinstance(declaration, ActionDeclaration):
                raise BridgeError("invalid_action", "Invalid action declaration.")

            name = declaration.name or attr_name
            self._validate_name(name, "action")
            if name in actions:
                raise BridgeError("duplicate_action", f"Duplicate action: {name}.")
            if declaration.ui_kind not in UI_KINDS:
                raise BridgeError(
                    "invalid_action",
                    f"Invalid ui_kind: {declaration.ui_kind}.",
                )

            method = declaration.method or _default_method(handler)
            if method not in HTTP_METHODS:
                raise BridgeError("invalid_action", f"Invalid HTTP method: {method}.")

            idempotent = (
                declaration.idempotent
                if declaration.idempotent is not None
                else method == "GET"
            )

            actions[name] = ActionSpec(
                name=name,
                title=declaration.title or _titleize(name),
                ui_kind=declaration.ui_kind,
                method=method,
                description=declaration.description,
                input_schema=callable_input_schema(handler),
                output_schema=callable_output_schema(handler),
                idempotent=idempotent,
                confirm=declaration.confirm,
                timeout_s=declaration.timeout_s,
                handler=handler,
            )

        return actions

    @staticmethod
    def _validate_name(name: str, label: str) -> None:
        if not NAME_RE.match(name):
            raise BridgeError(
                "invalid_name",
                f"Invalid {label} name: {name}.",
                details={"name": name, "pattern": NAME_RE.pattern},
            )

    @staticmethod
    def _coerce_arguments(handler: Any, arguments: dict[str, Any]) -> dict[str, Any]:
        signature = inspect.signature(handler)
        hints = get_type_hints(handler)
        coerced: dict[str, Any] = {}
        for name, value in arguments.items():
            parameter = signature.parameters.get(name)
            if parameter is None:
                raise BridgeError(
                    "validation_error",
                    f"Unknown argument: {name}.",
                    details={"argument": name},
                )
            coerced[name] = _coerce_value(value, hints.get(name, parameter.annotation))

        missing = [
            name
            for name, parameter in signature.parameters.items()
            if name != "self"
            and parameter.default is inspect.Parameter.empty
            and name not in coerced
        ]
        if missing:
            raise BridgeError(
                "validation_error",
                f"Missing required argument: {missing[0]}.",
                details={"argument": missing[0], "missing": missing},
            )
        return coerced


def _default_method(handler: Any) -> str:
    input_schema = callable_input_schema(handler)
    return "GET" if not input_schema.get("required") else "POST"


def _serialize(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {
            field.name: _serialize(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _coerce_value(value: Any, annotation: Any) -> Any:
    if not isinstance(value, str):
        return value
    if annotation is inspect.Signature.empty or annotation is str:
        return value
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is bool:
        return value.lower() in {"1", "true", "yes", "on"}
    return value


def _titleize(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


default_registry = Registry()
