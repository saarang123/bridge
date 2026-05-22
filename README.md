# Bridge

A personal services platform that exposes long-running processes on a home server to two clients: a phone app, and local LLM agents (Claude Code, Codex, etc.).

The same backend powers both — the phone gets HTTPS endpoints rendered as mini-app tiles; LLM agents get MCP tools they can call autonomously. Registering a new mini-app exposes its actions to both surfaces at once.

> **Project type:** Personal infra. Open-source target — framework will be released once anchor mini-apps stabilize. Until then, internal-only.
> **Read alongside:** the podcast mini-app at [`../podcast-this/`](../podcast-this/).
> **Hosting model:** server on a home machine (e.g. Mac mini) reachable from a phone via Tailscale, and from local LLM agents via stdio MCP transport.
> **Status:** pre-implementation. Scope locked, code not started.

---

## 1. The mental model — one backend, two consumers

Most "personal tooling" projects pick one interface and build to it: a CLI, a phone app, a web dashboard, an MCP server. Bridge is the case where none of those is the right primary interface — you want to use a service manually from your phone *and* hand it to an LLM agent running locally on the same server.

Same actions, two surfaces:

| Action | Phone (manual) | LLM agent (autonomous) |
|---|---|---|
| List podcast episodes | Tile shows queue | MCP `list_episodes` returns JSON |
| Generate episode from doc | Tap "Generate" on a doc | MCP `generate_episode(path)` |
| Start a terminal session | Tile launches webview | MCP `spawn_terminal()` returns id |
| Search the corpus | Search bar in app | MCP `search(query)` returns hits |

Both surfaces hit the same endpoints. The phone renders results as UI; the LLM uses them as tool outputs.

## 2. Architecture

```
┌──────────────────┐                       ┌─────────────────────────┐
│  iPhone          │ ─── Tailscale ──────▶ │  Home server            │
│  Bridge app      │     HTTPS             │  ┌───────────────────┐  │
│  (SwiftUI)       │                       │  │ Bridge core       │  │
└──────────────────┘                       │  │  - HTTP API       │  │
                                           │  │  - MCP server     │  │
┌──────────────────┐                       │  └─────────┬─────────┘  │
│  Local LLM       │ ─── stdio MCP ──────▶ │            │             │
│  (Claude Code,   │     (or SSE)          │  ┌─────────▼─────────┐  │
│   Codex, etc.)   │                       │  │ Mini-apps         │  │
└──────────────────┘                       │  │  - podcast        │  │
                                           │  │  - terminal       │  │
                                           │  │  - ...            │  │
                                           │  └───────────────────┘  │
                                           └─────────────────────────┘
```

A single Python process exposes the same action registry over two transports: FastAPI for HTTPS, an MCP server for stdio/SSE. Mini-apps don't know which transport invoked them.

## 3. MVP scope (v0)

- **Core**: FastAPI HTTP server + MCP server in one Python process, sharing an action registry.
- **iOS app**: SwiftUI shell, TestFlight Internal Testing. One device.
- **Mini-app registry**: each mini-app registers `{name, icon, actions[]}` at startup; both HTTP and MCP layers expose its actions.
- **First mini-app**: podcast (see [`../podcast-this/`](../podcast-this/)).
- **Auth**: Tailscale-gated for phone, local stdio for MCP. No public exposure.

## 4. Deferred to v1+

| Feature | When |
|---|---|
| Terminal mini-app: spawn / attach / control Claude Code or Codex sessions on the server from the phone | After podcast mini-app stable |
| Knowledge browser mini-app (search + retrieval over a markdown corpus) | After a retrieval system is built |
| Push notifications (long job finished, agent waiting for input) | After 2+ mini-apps |
| Web admin UI (manage mini-apps, view logs) | If maintenance gets painful |
| Hot-reload mini-apps (drop a config + binary, no restart) | Stretch |
| Public OSS release | After podcast + terminal mini-apps stabilize |

## 5. Mini-app protocol

Each mini-app declares actions in code:

```python
@bridge.mini_app("podcast", icon="headphones")
class Podcast:
    @action(ui_kind="list")
    def list_episodes(self) -> list[Episode]: ...

    @action(ui_kind="trigger")
    def generate_episode(self, source_path: str) -> JobId: ...
```

`@action` generates both:
- A REST endpoint (`GET /podcast/list_episodes`, `POST /podcast/generate_episode`).
- An MCP tool (`podcast.list_episodes`, `podcast.generate_episode`) with a JSON schema derived from the function signature.

The phone shell renders each action by its `ui_kind` (`list | detail | trigger | webview | custom`). LLM agents discover actions via MCP `list_tools`.

## 6. Project structure (planned)

```
bridge/
├── README.md
├── ios/                    Xcode project, SwiftUI
│   └── Bridge/
├── server/                 Python package
│   ├── bridge/
│   │   ├── core.py         registry, @action decorator, schema generation
│   │   ├── http.py         FastAPI app
│   │   ├── mcp.py          MCP server (stdio + SSE transports)
│   │   └── mini_apps/      external mini-app entrypoints
│   └── pyproject.toml
└── docs/
    └── mini-app-protocol.md
```

## 7. Practical commands

```bash
# Server: serve HTTP + MCP (stdio) in one process
cd ~/Documents/bridge/server
uv run bridge serve

# Add Bridge as an MCP server for Claude Code locally
claude mcp add bridge -- uv run --directory ~/Documents/bridge/server bridge mcp

# iOS app
open ios/Bridge.xcodeproj
# Build & deploy: Xcode → Product → Archive → Distribute → TestFlight
```

## 8. Why this shape (rationale, abridged)

- **Why not just a CLI?** You want to use this from your phone, away from the laptop.
- **Why not just a phone app?** You want the same actions callable by local LLM agents that already run on the home server.
- **Why MCP and not a custom RPC?** MCP is what local agents already speak. Free integration with Claude Code, Codex, and any future agent.
- **Why a registry instead of hand-coded endpoints?** Each mini-app becomes a self-contained drop-in; the framework value compounds as more land.
