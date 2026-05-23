from typing import Any

from bridge.activities import ActivityStore, default_activity_store
from bridge.models import BridgeError
from bridge.registry import Registry, default_registry


def create_app(
    registry: Registry = default_registry,
    activities: ActivityStore = default_activity_store,
) -> Any:
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
    except ImportError as exc:
        raise RuntimeError("FastAPI is required to run the Bridge HTTP server.") from exc

    app = FastAPI(title="Bridge")

    @app.exception_handler(BridgeError)
    async def bridge_error_handler(request: Request, exc: BridgeError) -> JSONResponse:
        status = {
            "validation_error": 400,
            "unsupported_signature": 400,
            "unsupported_type": 400,
            "not_found": 404,
            "conflict": 409,
            "unauthorized": 401,
            "forbidden": 403,
            "timeout": 504,
        }.get(exc.code, 500)
        return JSONResponse(status_code=status, content=exc.envelope())

    @app.get("/apps")
    def list_apps() -> dict[str, Any]:
        return registry.manifest()

    @app.get("/apps/{app_name}")
    def get_app(app_name: str) -> dict[str, Any]:
        return registry.app_manifest(app_name)

    @app.get("/apps/{app_name}/actions/{action_name}")
    def invoke_get(app_name: str, action_name: str, request: Request) -> dict[str, Any]:
        arguments = dict(request.query_params)
        if not arguments:
            arguments = None
        result = registry.invoke(app_name, action_name, arguments)
        return result.envelope()

    @app.post("/apps/{app_name}/actions/{action_name}")
    async def invoke_post(
        app_name: str,
        action_name: str,
        request: Request,
    ) -> dict[str, Any]:
        body = await request.json()
        if not isinstance(body, dict):
            raise BridgeError("validation_error", "Action request body must be an object.")
        result = registry.invoke(app_name, action_name, body)
        return result.envelope()

    @app.get("/activities")
    def list_activities() -> dict[str, Any]:
        return activities.manifest()

    @app.get("/activities/{activity_id}")
    def get_activity(activity_id: str) -> dict[str, Any]:
        return activities.get(activity_id).manifest()

    @app.post("/activities/{activity_id}/cancel")
    def cancel_activity(activity_id: str) -> dict[str, Any]:
        return activities.cancel(activity_id).manifest()

    return app
