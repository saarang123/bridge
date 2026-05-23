from __future__ import annotations

from dataclasses import dataclass

from bridge.activities import default_activity_store
from bridge import action, mini_app


@dataclass(frozen=True)
class EchoResult:
    message: str


@mini_app(
    "demo",
    title="Demo",
    icon="hammer",
    description="Small built-in app for proving Bridge wiring.",
)
class DemoMiniApp:
    @action(ui_kind="list", method="GET", description="Return a static list.")
    def list_items(self) -> list[str]:
        return ["alpha", "beta", "gamma"]

    @action(ui_kind="form", method="POST", description="Echo a message.")
    def echo(self, message: str) -> EchoResult:
        return EchoResult(message=message)

    @action(ui_kind="trigger", method="POST", description="Create a demo activity.")
    def start_demo_job(self) -> str:
        activity = default_activity_store.create(
            kind="job",
            app="demo",
            title="Demo Job",
            status="running",
            phase="Working",
            summary="Synthetic activity for exercising the Active tab.",
            actions=["cancel"],
        )
        return activity.id
