from __future__ import annotations

import dataclasses
import inspect
from enum import Enum
from types import NoneType, UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from bridge.models import BridgeError


def callable_input_schema(fn: Any) -> dict[str, Any]:
    signature = inspect.signature(fn)
    hints = get_type_hints(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            raise BridgeError(
                "unsupported_signature",
                f"Unsupported parameter kind for {name}.",
                details={"parameter": name, "kind": str(parameter.kind)},
            )

        annotation = hints.get(name, Any)
        properties[name] = schema_for_type(annotation)
        if parameter.default is not inspect.Parameter.empty:
            properties[name]["default"] = parameter.default
        else:
            required.append(name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def callable_output_schema(fn: Any) -> dict[str, Any]:
    hints = get_type_hints(fn)
    return schema_for_type(hints.get("return", Any))


def schema_for_type(annotation: Any) -> dict[str, Any]:
    if annotation is Any:
        return {}
    if annotation is None or annotation is NoneType:
        return {"type": "null"}
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Literal:
        values = list(args)
        return {"enum": values}

    if origin in {list, tuple}:
        item_type = args[0] if args else Any
        return {"type": "array", "items": schema_for_type(item_type)}

    if origin is dict:
        key_type = args[0] if args else str
        value_type = args[1] if len(args) > 1 else Any
        if key_type is not str:
            raise BridgeError(
                "unsupported_type",
                "Only dicts with string keys can cross the Bridge protocol.",
            )
        return {"type": "object", "additionalProperties": schema_for_type(value_type)}

    if origin in {Union, UnionType}:
        return _union_schema(args)

    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return {"enum": [item.value for item in annotation]}

    if dataclasses.is_dataclass(annotation):
        return _dataclass_schema(annotation)

    raise BridgeError(
        "unsupported_type",
        f"Unsupported protocol type: {annotation!r}.",
    )


def _union_schema(args: tuple[Any, ...]) -> dict[str, Any]:
    non_null = [arg for arg in args if arg is not NoneType]
    has_null = len(non_null) != len(args)

    if len(non_null) == 1 and has_null:
        schema = schema_for_type(non_null[0])
        schema["nullable"] = True
        return schema

    return {"anyOf": [schema_for_type(arg) for arg in args]}


def _dataclass_schema(annotation: Any) -> dict[str, Any]:
    hints = get_type_hints(annotation)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for field in dataclasses.fields(annotation):
        field_schema = schema_for_type(hints.get(field.name, Any))
        if field.default is not dataclasses.MISSING:
            field_schema["default"] = field.default
        elif field.default_factory is dataclasses.MISSING:
            required.append(field.name)
        properties[field.name] = field_schema

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema
