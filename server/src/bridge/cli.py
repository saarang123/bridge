from __future__ import annotations

import argparse
import os

from bridge.http import create_app
from bridge.mini_apps.demo import DemoMiniApp
from bridge.mini_apps.podcast import PodcastMiniApp
from bridge.mini_apps.podcast_mock import PodcastMockMiniApp
from bridge.activities import default_activity_store
from bridge.registry import default_registry


def main() -> None:
    parser = argparse.ArgumentParser(prog="bridge")
    subcommands = parser.add_subparsers(dest="command", required=True)
    serve = subcommands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8080, type=int)
    subcommands.add_parser("manifest")
    args = parser.parse_args()

    _register_builtin_apps()

    if args.command == "manifest":
        import json

        print(json.dumps(default_registry.manifest(), indent=2))
        return

    if args.command == "serve":
        import uvicorn

        uvicorn.run(create_app(default_registry), host=args.host, port=args.port)


def _register_builtin_apps() -> None:
    if not default_registry.apps():
        default_registry.register(DemoMiniApp)
        if os.environ.get("BRIDGE_PODCAST_MODE") == "mock":
            default_registry.register(PodcastMockMiniApp, default_activity_store)
        else:
            default_registry.register(PodcastMiniApp, activity_store=default_activity_store)


if __name__ == "__main__":
    main()
