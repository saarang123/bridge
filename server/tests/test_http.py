from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient
except (ImportError, RuntimeError):  # pragma: no cover - exercised only outside the uv env.
    TestClient = None  # type: ignore[assignment]

from bridge.activities import ActivityStore
from bridge.http import create_app
from bridge.mini_apps.demo import DemoMiniApp
from bridge.mini_apps.podcast_mock import PodcastMockMiniApp
from bridge.registry import Registry


class HttpSmokeTests(unittest.TestCase):
    @unittest.skipIf(TestClient is None, "fastapi is not installed")
    def setUp(self) -> None:
        registry = Registry()
        registry.register(DemoMiniApp)
        self.activities = ActivityStore()
        registry.register(PodcastMockMiniApp, self.activities)
        self.client = TestClient(create_app(registry, self.activities))

    def test_apps_endpoint(self) -> None:
        response = self.client.get("/apps")
        data = response.json()
        names = {app["name"] for app in data["apps"]}

        self.assertIn("podcast", names)

    def test_podcast_generation_creates_activity(self) -> None:
        response = self.client.post(
            "/apps/podcast/actions/generate_episode",
            json={"source_uri": "/tmp/example.md"},
        )
        activity_id = response.json()["data"]

        activities = self.client.get("/activities").json()["activities"]

        self.assertEqual(activity_id, "act_000001")
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]["app"], "podcast")


if __name__ == "__main__":
    unittest.main()
