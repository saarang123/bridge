from __future__ import annotations

import unittest

from bridge.activities import ActivityStore
from bridge import action, mini_app
from bridge.mcp import McpRegistryAdapter
from bridge.mini_apps.demo import DemoMiniApp
from bridge.mini_apps.podcast import PodcastMiniApp
from bridge.mini_apps.podcast_mock import PodcastMockMiniApp
from bridge.registry import Registry


class RegistryTests(unittest.TestCase):
    def test_manifest_contains_registered_action_schemas(self) -> None:
        registry = Registry()
        registry.register(DemoMiniApp)

        manifest = registry.manifest()

        self.assertEqual(manifest["apps"][0]["name"], "demo")
        actions = {action["name"]: action for action in manifest["apps"][0]["actions"]}
        self.assertEqual(actions["echo"]["method"], "POST")
        self.assertEqual(actions["echo"]["input_schema"]["required"], ["message"])
        self.assertEqual(
            actions["echo"]["input_schema"]["properties"]["message"],
            {"type": "string"},
        )

    def test_invoke_serializes_dataclass_results(self) -> None:
        registry = Registry()
        registry.register(DemoMiniApp)

        result = registry.invoke("demo", "echo", {"message": "hi"})

        self.assertEqual(result.data, {"message": "hi"})

    def test_mcp_adapter_lists_and_calls_tools(self) -> None:
        registry = Registry()
        registry.register(DemoMiniApp)
        adapter = McpRegistryAdapter(registry)

        tools = {tool["name"]: tool for tool in adapter.list_tools()}

        self.assertIn("demo.echo", tools)
        self.assertEqual(
            adapter.call_tool("demo.echo", {"message": "from mcp"}),
            {"message": "from mcp"},
        )

    def test_rejects_unknown_arguments(self) -> None:
        registry = Registry()
        registry.register(DemoMiniApp)

        with self.assertRaisesRegex(Exception, "Unknown argument"):
            registry.invoke("demo", "echo", {"message": "hi", "extra": "nope"})

    def test_rejects_missing_required_arguments(self) -> None:
        registry = Registry()
        registry.register(DemoMiniApp)

        with self.assertRaisesRegex(Exception, "Missing required argument: message"):
            registry.invoke("demo", "echo")

    def test_coerces_simple_query_string_values(self) -> None:
        @mini_app("typed")
        class TypedMiniApp:
            @action(ui_kind="detail", method="GET")
            def add_one(self, value: int) -> int:
                return value + 1

        registry = Registry()
        registry.register(TypedMiniApp)

        result = registry.invoke("typed", "add_one", {"value": "41"})

        self.assertEqual(result.data, 42)


class ActivityStoreTests(unittest.TestCase):
    def test_activity_manifest_and_cancel(self) -> None:
        store = ActivityStore()
        activity = store.create(
            kind="job",
            app="podcast",
            title="Generate Episode",
            status="running",
            phase="Rewrite",
            actions=["cancel"],
        )

        self.assertEqual(store.manifest()["activities"][0]["id"], activity.id)

        cancelled = store.cancel(activity.id)

        self.assertEqual(cancelled.status, "cancelled")
        self.assertNotIn("cancel", cancelled.actions)


class PodcastMockTests(unittest.TestCase):
    def test_podcast_mock_exposes_expected_actions(self) -> None:
        registry = Registry()
        registry.register(PodcastMockMiniApp)

        manifest = registry.app_manifest("podcast")
        action_names = {action["name"] for action in manifest["actions"]}

        self.assertEqual(
            action_names,
            {"generate_episode", "list_episodes", "list_sources"},
        )


class FakePodcastService:
    def list_sources(self) -> list[dict[str, str]]:
        return [{"title": "Doc", "source_uri": "/tmp/doc.md", "kind": "markdown"}]

    def generate_episode(self, source_uri: str) -> dict[str, str]:
        return {"job_id": "job_1", "status": "queued"}

    def list_episodes(self) -> list[dict[str, str]]:
        return [{"episode_id": "ep_1", "title": "Doc", "status": "generating"}]

    def get_job(self, job_id: str) -> dict[str, str]:
        if job_id == "missing":
            raise KeyError(job_id)
        return {"job_id": job_id, "status": "running", "phase": "rewriting"}


class PodcastAdapterTests(unittest.TestCase):
    def test_podcast_adapter_wraps_service(self) -> None:
        registry = Registry()
        registry.register(PodcastMiniApp, FakePodcastService())

        result = registry.invoke(
            "podcast",
            "generate_episode",
            {"source_uri": "/tmp/doc.md"},
        )

        self.assertEqual(result.data["job_id"], "job_1")
        self.assertIsNotNone(result.data["activity_id"])

    def test_podcast_get_job_rejects_empty_id(self) -> None:
        registry = Registry()
        registry.register(PodcastMiniApp, FakePodcastService())

        with self.assertRaisesRegex(Exception, "job_id is required"):
            registry.invoke("podcast", "get_job", {"job_id": ""})

    def test_podcast_get_job_maps_unknown_id(self) -> None:
        registry = Registry()
        registry.register(PodcastMiniApp, FakePodcastService())

        with self.assertRaisesRegex(Exception, "Unknown podcast job"):
            registry.invoke("podcast", "get_job", {"job_id": "missing"})


if __name__ == "__main__":
    unittest.main()
