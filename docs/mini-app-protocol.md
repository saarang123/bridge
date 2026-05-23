# Mini-App Protocol

Bridge mini-apps are Python objects that declare actions once and let Bridge expose
those actions to two consumers:

- the iOS app over HTTPS
- local LLM agents over MCP

The protocol is intentionally code-first for v0. A mini-app does not ship a separate
manifest file as its source of truth; Bridge derives the runtime manifest, HTTP
routes, and MCP tool schemas from decorated Python callables.

## Goals

- Keep manual phone workflows and autonomous agent workflows backed by the same
  implementation.
- Make each action explicit enough to render in the phone shell without hand-written
  Swift per mini-app.
- Generate MCP schemas from normal Python signatures and type hints.
- Keep the first version easy to inspect and debug.

## Non-Goals for v0

- Hot-loading mini-apps without restarting Bridge.
- Arbitrary custom native UI shipped by mini-apps.
- Public unauthenticated endpoints.
- A plugin marketplace or remote install flow.
- Streaming action output, except where an action returns a URL to a live webview.

## Core Shape

```python
from bridge import action, mini_app


@mini_app(
    "podcast",
    title="Podcast This",
    icon="headphones",
    description="Generate narrated podcast episodes from source documents.",
)
class PodcastApp:
    @action(
        ui_kind="list",
        title="Episodes",
        method="GET",
    )
    def list_episodes(self) -> list[Episode]:
        ...

    @action(
        ui_kind="trigger",
        title="Generate Episode",
        method="POST",
    )
    def generate_episode(self, source_uri: str) -> JobRef:
        ...
```

`@mini_app` registers a namespace. `@action` registers an invokable capability inside
that namespace.

The example above creates:

- `GET /apps/podcast/actions/list_episodes`
- `POST /apps/podcast/actions/generate_episode`
- MCP tool `podcast.list_episodes`
- MCP tool `podcast.generate_episode`

## Mini-App Declaration

`@mini_app(...)` accepts:

| Field | Required | Notes |
|---|---:|---|
| `name` | yes | Stable machine name. Lowercase `snake_case` or `kebab-case`; used in URLs and MCP tool names. |
| `title` | no | Human-readable display name. Defaults to title-cased `name`. |
| `icon` | no | Symbol name from the Bridge icon allowlist. Defaults to `square.grid.2x2`. |
| `description` | no | Short display and discovery text. |
| `version` | no | Mini-app protocol version or app implementation version. Defaults to `0.1.0`. |

Names must be unique process-wide. Bridge should fail startup on duplicate mini-app
names rather than letting later registrations shadow earlier ones.

## Action Declaration

`@action(...)` accepts:

| Field | Required | Notes |
|---|---:|---|
| `ui_kind` | yes | Phone rendering hint. One of `list`, `detail`, `trigger`, `form`, `webview`, `custom`. |
| `title` | no | Display label. Defaults to title-cased function name. |
| `description` | no | Short explanation for UI affordances and MCP tool description. |
| `method` | no | HTTP method. Defaults to `GET` for no-argument read actions, otherwise `POST`. |
| `idempotent` | no | Whether retries are safe. Defaults to `True` for `GET`, `False` for `POST`. |
| `returns` | no | Optional explicit return renderer when type hints are insufficient. |
| `timeout_s` | no | Action timeout hint. Defaults to the server default. |
| `confirm` | no | If true, the phone asks for confirmation before invoking. |

Action function names must be unique within a mini-app. Public action names should be
stable; renaming a function renames its HTTP route and MCP tool unless `name=` is
added later.

## Type Contract

Bridge derives JSON Schema from function signatures and return annotations.

Supported parameter types for v0:

- `str`, `int`, `float`, `bool`
- `list[T]`
- `dict[str, T]`
- `Literal[...]`
- `Enum`
- `dataclass`
- Pydantic `BaseModel`
- `Optional[T]` / `T | None`

Unsupported parameter types should fail at startup with a clear error. The first
version should be strict; silent coercion makes both the phone UI and MCP tools hard
to trust.

Recommended conventions:

- Use Pydantic models for structured inputs and outputs that cross the protocol.
- Use dataclasses for internal-only objects or very small response records.
- Avoid raw `Any` in action signatures.
- Avoid positional-only parameters.
- Keep defaults JSON-serializable.

## Invocation Model

Each action is invoked with one JSON object of named arguments.

For an action:

```python
def generate_episode(self, source_uri: str, voice: str | None = None) -> JobRef:
    ...
```

HTTP request body:

```json
{
  "source_uri": "/example/docs/backprop.md",
  "voice": null
}
```

MCP tool arguments:

```json
{
  "source_uri": "/example/docs/backprop.md",
  "voice": null
}
```

The callable receives normal Python arguments:

```python
generate_episode(source_uri="/example/docs/backprop.md", voice=None)
```

Bridge owns validation, error formatting, and transport adaptation. The mini-app owns
business logic.

## HTTP Mapping

Routes:

| Route | Purpose |
|---|---|
| `GET /apps` | List mini-app manifests. |
| `GET /apps/{app_name}` | Return one mini-app manifest. |
| `GET /apps/{app_name}/actions/{action_name}` | Invoke a read action with query params. |
| `POST /apps/{app_name}/actions/{action_name}` | Invoke an action with JSON body. |

Response envelope:

```json
{
  "ok": true,
  "data": {},
  "meta": {
    "app": "podcast",
    "action": "generate_episode",
    "request_id": "req_..."
  }
}
```

Error envelope:

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "source_uri is required",
    "details": {}
  },
  "meta": {
    "app": "podcast",
    "action": "generate_episode",
    "request_id": "req_..."
  }
}
```

HTTP status codes should still be meaningful:

| Status | Use |
|---:|---|
| `200` | Action completed successfully. |
| `202` | Long-running job accepted. |
| `400` | Validation failed. |
| `401` | Missing or invalid auth. |
| `403` | Caller is authenticated but not allowed. |
| `404` | App or action does not exist. |
| `409` | Conflict with current state. |
| `500` | Unhandled server error. |

## MCP Mapping

Each action becomes one MCP tool.

Tool name:

```text
{app_name}.{action_name}
```

Tool description:

```text
{action title}. {action description}
```

Tool input schema is the JSON Schema derived from the action parameters. Tool output
is the same serializable data returned by HTTP, without requiring the model to know
about HTTP envelopes. Bridge may include the envelope internally for logs, but MCP
callers should receive the action result or a normal MCP tool error.

## Runtime Manifest

`GET /apps` returns enough metadata for the iOS shell to render available mini-apps
and action entry points:

```json
{
  "apps": [
    {
      "name": "podcast",
      "title": "Podcast This",
      "icon": "headphones",
      "description": "Generate narrated podcast episodes from source documents.",
      "version": "0.1.0",
      "actions": [
        {
          "name": "generate_episode",
          "title": "Generate Episode",
          "description": "",
          "ui_kind": "trigger",
          "method": "POST",
          "idempotent": false,
          "input_schema": {
            "type": "object",
            "required": ["source_uri"],
            "properties": {
              "source_uri": { "type": "string" }
            }
          }
        }
      ]
    }
  ]
}
```

This manifest is generated, not hand-authored, in v0.

## UI Kinds

`ui_kind` is a rendering hint, not a separate protocol.

| Kind | Expected phone behavior |
|---|---|
| `list` | Render returned array as rows. |
| `detail` | Render returned object as fields or sections. |
| `trigger` | Render as a button; good for no-input or prefilled actions. |
| `form` | Render inputs from `input_schema`, then submit. |
| `webview` | Invoke action and open returned URL in an in-app webview. |
| `custom` | Reserved escape hatch; v0 may show raw JSON until native handling exists. |

The MCP layer ignores `ui_kind` except as descriptive metadata.

## Long-Running Work

Actions that do expensive work should return a job reference quickly:

```json
{
  "job_id": "job_...",
  "status": "queued",
  "status_url": "/apps/podcast/actions/get_job?job_id=job_..."
}
```

Long-running work should not hold an HTTP request open in v0. A mini-app that creates
jobs should also expose a status action, for example `get_job(job_id: str)`.

## Error Codes

Use stable machine-readable codes:

- `validation_error`
- `not_found`
- `conflict`
- `unauthorized`
- `forbidden`
- `timeout`
- `dependency_unavailable`
- `internal_error`

Exception classes in Bridge should map to these codes. Unhandled exceptions should be
logged with request IDs and returned as `internal_error`.

## Auth and Network Exposure

The v0 default should stay private:

- phone access over Tailscale HTTPS
- local agents over stdio MCP
- no public internet exposure

That is the conservative default because Bridge actions are capability-bearing. A
public endpoint is viable later, but it changes the security model: every action must
be treated like an internet-facing API with authentication, authorization, rate
limits, audit logs, dependency hardening, and careful prompt/tool abuse handling.

The protocol should not depend on Tailscale. HTTP routes, schemas, and auth hooks
should work the same if the deployment later moves behind Caddy with public DNS,
OAuth, mTLS, Cloudflare Access, or another access layer.

Practical v0 stance:

- Build as though routes could be public one day.
- Deploy as though they are private today.
- Keep auth as a replaceable boundary around the same route surface.

## Startup Behavior

At startup, Bridge should:

1. Import configured mini-app modules.
2. Register `@mini_app` classes.
3. Inspect decorated actions.
4. Generate JSON Schemas.
5. Fail fast on duplicate names, unsupported types, invalid HTTP methods, or invalid
   `ui_kind` values.
6. Start HTTP and MCP transports from the same registry.

This keeps protocol errors visible before a phone tap or MCP tool call hits them.

## Open Questions

- Whether v0 should support async action functions from day one.
- Whether `GET` action parameters should be accepted only as query params or also as
  JSON bodies for consistency.
- Whether Bridge should reserve an app-level `jobs` protocol instead of letting each
  mini-app define job status actions.
- Whether action names should allow explicit `name=` overrides immediately, or wait
  until there is a real migration need.
