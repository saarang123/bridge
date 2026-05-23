from __future__ import annotations

import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from bridge import action, mini_app
from bridge.activities import ActivityStore, default_activity_store
from bridge.models import BridgeError


@mini_app(
    "podcast",
    title="Podcast This",
    icon="headphones",
    description="Generate narrated podcast episodes from documents and links.",
)
class PodcastMiniApp:
    def __init__(
        self,
        service: Any | None = None,
        activity_store: ActivityStore = default_activity_store,
    ) -> None:
        self.service = service or create_podcast_service_from_env()
        self.activity_store = activity_store

    @action(ui_kind="list", method="GET", description="List known source documents.")
    def list_sources(self) -> list[dict[str, Any]]:
        return [_to_dict(item) for item in self.service.list_sources()]

    @action(ui_kind="form", method="POST", description="Start podcast generation.")
    def generate_episode(self, source_uri: str) -> dict[str, Any]:
        job_ref = self.service.generate_episode(source_uri)
        data = _to_dict(job_ref)
        job_id = data["job_id"]
        activity = self.activity_store.create(
            kind="job",
            app="podcast",
            title=f"Generate: {Path(source_uri).name or source_uri}",
            status=_activity_status(data.get("status", "queued")),
            phase="queued",
            summary=source_uri,
            actions=["cancel"],
        )
        data["activity_id"] = activity.id
        return data

    @action(ui_kind="list", method="GET", description="List generated episodes.")
    def list_episodes(self) -> list[dict[str, Any]]:
        return [_to_dict(item) for item in self.service.list_episodes()]

    @action(ui_kind="detail", method="GET", description="Get generation job status.")
    def get_job(self, job_id: str) -> dict[str, Any]:
        if not job_id.strip():
            raise BridgeError("validation_error", "job_id is required.")
        try:
            status = _to_dict(self.service.get_job(job_id))
        except KeyError as exc:
            raise BridgeError("not_found", f"Unknown podcast job: {job_id}.") from exc
        self._sync_activity_for_job(status)
        return status

    def _sync_activity_for_job(self, status: dict[str, Any]) -> None:
        # PodcastService does not persist Bridge activity ids yet. We still sync
        # when a matching active podcast job is obvious from the current process.
        job_id = status.get("job_id")
        if not job_id:
            return

        detail_url = status.get("audio_url") or status.get("feed_url")
        for activity in self.activity_store.list():
            if activity.app != "podcast" or activity.kind != "job":
                continue
            if activity.status in {"complete", "failed", "cancelled"}:
                continue
            self.activity_store.update(
                activity.id,
                status=_activity_status(status.get("status", activity.status)),
                phase=status.get("phase") or activity.phase,
                summary=status.get("message") or activity.summary,
                detail_url=detail_url,
                actions=[] if status.get("status") in {"complete", "failed"} else activity.actions,
            )
            return


def create_podcast_service_from_env() -> Any:
    podcast_cli = Path(
        os.environ.get("BRIDGE_PODCAST_CLI", str(_default_podcast_cli()))
    ).expanduser()
    if podcast_cli.exists():
        sys.path.insert(0, str(podcast_cli.resolve()))

    try:
        from podcast.service import PodcastService, ServiceSettings
    except ImportError as exc:
        raise RuntimeError(
            "Podcast This is not importable. Set BRIDGE_PODCAST_CLI to its cli/ directory "
            "or run Bridge with BRIDGE_PODCAST_MODE=mock."
        ) from exc

    podcast_root = podcast_cli.parent
    settings = ServiceSettings(
        source_roots=_path_list("BRIDGE_PODCAST_SOURCE_ROOTS"),
        audio_dir=_path("BRIDGE_PODCAST_AUDIO_DIR", str(podcast_root / "audio")),
        feed_dir=_path("BRIDGE_PODCAST_FEED_DIR", str(podcast_root / "feed")),
        jobs_dir=_path("BRIDGE_PODCAST_JOBS_DIR", str(podcast_root / "jobs")),
        work_dir=_path("BRIDGE_PODCAST_WORK_DIR", str(podcast_root / "work")),
        audio_url_base=os.environ.get(
            "BRIDGE_PODCAST_AUDIO_URL_BASE",
            "http://localhost:8000/audio",
        ),
        feed_url=os.environ.get(
            "BRIDGE_PODCAST_FEED_URL",
            "http://localhost:8000/feed/feed.xml",
        ),
        spindle_url=os.environ.get("BRIDGE_PODCAST_SPINDLE_URL", "http://localhost:8080"),
        spindle_auth_token=os.environ.get("BRIDGE_PODCAST_SPINDLE_AUTH_TOKEN"),
        tts_config_id=os.environ.get(
            "BRIDGE_PODCAST_TTS_CONFIG_ID",
            "audio-tts-kokoro-v1",
        ),
        tts_voice=os.environ.get("BRIDGE_PODCAST_TTS_VOICE"),
        rewrite_cli_binary=os.environ.get("BRIDGE_PODCAST_REWRITE_CLI", "claude"),
    )
    return PodcastService(settings)


def _default_podcast_cli() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "podcast-this" / "cli"
        if candidate.exists():
            return candidate
    return Path("../podcast-this/cli")


def _path(env_name: str, default: str) -> Path:
    return Path(os.environ.get(env_name, default)).expanduser()


def _path_list(env_name: str) -> list[Path]:
    raw = os.environ.get(env_name)
    if not raw:
        return [Path("~/Documents").expanduser()]
    return [Path(item).expanduser() for item in raw.split(":") if item]


def _to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"Expected dataclass or dict from PodcastService, got {type(value)!r}.")


def _activity_status(status: Any) -> str:
    if status in {"queued", "running", "waiting", "complete", "failed", "cancelled"}:
        return status
    return "running"
