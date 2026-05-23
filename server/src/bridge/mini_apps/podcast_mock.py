from __future__ import annotations

from dataclasses import dataclass

from bridge import action, mini_app
from bridge.activities import ActivityStore, default_activity_store


@dataclass(frozen=True)
class SourceDoc:
    title: str
    source_uri: str
    kind: str


@dataclass(frozen=True)
class Episode:
    title: str
    status: str
    audio_url: str | None = None


@mini_app(
    "podcast",
    title="Podcast This",
    icon="headphones",
    description="Generate narrated podcast episodes from documents and links.",
)
class PodcastMockMiniApp:
    def __init__(self, activity_store: ActivityStore = default_activity_store) -> None:
        self.activity_store = activity_store

    @action(ui_kind="list", method="GET", description="List known source documents.")
    def list_sources(self) -> list[SourceDoc]:
        return [
            SourceDoc(
                title="Backpropagation Notes",
                source_uri="/example/docs/backprop.md",
                kind="markdown",
            ),
            SourceDoc(
                title="Transformer Architecture",
                source_uri="/example/docs/transformers.md",
                kind="markdown",
            ),
        ]

    @action(ui_kind="form", method="POST", description="Start podcast generation.")
    def generate_episode(self, source_uri: str) -> str:
        activity = self.activity_store.create(
            kind="job",
            app="podcast",
            title=f"Generate: {source_uri.rsplit('/', 1)[-1]}",
            status="running",
            phase="Queued",
            summary="Podcast generation will run in Podcast This once wired.",
            actions=["cancel"],
            detail_url=None,
        )
        return activity.id

    @action(ui_kind="list", method="GET", description="List generated episodes.")
    def list_episodes(self) -> list[Episode]:
        return [
            Episode(
                title="Example Episode",
                status="published",
                audio_url="https://example.invalid/audio/example.mp3",
            )
        ]
