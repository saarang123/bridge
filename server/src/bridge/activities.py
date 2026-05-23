from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from itertools import count
from typing import Any

from bridge.models import Activity, ActivityKind, ActivityStatus, BridgeError


class ActivityStore:
    def __init__(self) -> None:
        self._activities: dict[str, Activity] = {}
        self._ids = count(1)

    def list(self) -> list[Activity]:
        return sorted(
            self._activities.values(),
            key=lambda activity: activity.updated_at,
            reverse=True,
        )

    def get(self, activity_id: str) -> Activity:
        try:
            return self._activities[activity_id]
        except KeyError as exc:
            raise BridgeError(
                "not_found",
                f"Unknown activity: {activity_id}.",
                details={"activity_id": activity_id},
            ) from exc

    def create(
        self,
        *,
        kind: ActivityKind,
        app: str,
        title: str,
        status: ActivityStatus = "queued",
        phase: str = "",
        summary: str = "",
        actions: list[str] | None = None,
        detail_url: str | None = None,
    ) -> Activity:
        now = _now()
        activity = Activity(
            id=f"act_{next(self._ids):06d}",
            kind=kind,
            app=app,
            title=title,
            status=status,
            phase=phase,
            summary=summary,
            created_at=now,
            updated_at=now,
            actions=actions or [],
            detail_url=detail_url,
        )
        self._activities[activity.id] = activity
        return activity

    def update(self, activity_id: str, **changes: Any) -> Activity:
        activity = self.get(activity_id)
        updated = replace(activity, updated_at=_now(), **changes)
        self._activities[activity_id] = updated
        return updated

    def cancel(self, activity_id: str) -> Activity:
        activity = self.get(activity_id)
        if activity.status in {"complete", "failed", "cancelled"}:
            raise BridgeError(
                "conflict",
                f"Activity is already terminal: {activity.status}.",
                details={"activity_id": activity_id, "status": activity.status},
            )
        return self.update(
            activity_id,
            status="cancelled",
            phase="Cancelled",
            actions=[action for action in activity.actions if action != "cancel"],
        )

    def manifest(self) -> dict[str, Any]:
        return {"activities": [activity.manifest() for activity in self.list()]}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


default_activity_store = ActivityStore()
