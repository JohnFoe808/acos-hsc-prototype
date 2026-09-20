from __future__ import annotations

import asyncio
import hmac
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .backends import available_backends
from .cognition import CognitiveEventLoop
from .compute_fabric import ComputeFabric
from .config import settings
from .engine import CognitiveExecutive
from .hybrid import HybridExecutor, HybridGraph, reference_workflow
from .model_core import ModelRequest, configured_model_core
from .permissions import PermissionBroker
from .quantum import bell_state, qiskit_available
from .router import ComputeRouter
from .schemas import (
    ComputeJobRequest,
    ConversationCreate,
    ConversationUpdate,
    EventCreate,
    HybridGraphRequest,
    MemoryCreate,
    MemoryKind,
    MessageRequest,
    MessageResponse,
    ModelRequestBody,
    SearchRequest,
    SkillCreate,
    SkillExecution,
    ToolRequest,
    VerificationRequest,
    WorkspaceUpdate,
    WorldAdvance,
    WorldEntityCreate,
)
from .search import is_trusted_domain, local_search
from .skills import SuperconsciousSkillEngine
from .store import Store
from .system_tools import list_workspace, system_status
from .verification import verify_plan
from .workspace import GlobalWorkspace
from .world import World

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

store = Store(settings.database_path)
permissions = PermissionBroker()
workspace = GlobalWorkspace(store)
skills = SuperconsciousSkillEngine(store, settings.skill_promotion_threshold)
router = ComputeRouter()
engine = CognitiveExecutive(store, workspace, skills, permissions, router)
world = World(store)
model_core = configured_model_core(settings)
engine.model_core = model_core
cognition = CognitiveEventLoop(store, workspace, model_core)
compute = ComputeFabric(store, permissions)
hybrid = HybridExecutor(store, compute, permissions)
reflection_task: asyncio.Task[None] | None = None


def require_auth(authorization: str | None = Header(default=None)) -> None:
    if not settings.require_auth:
        return
    if (
        not settings.api_token
        or not authorization
        or not hmac.compare_digest(authorization, settings.api_token)
    ):
        raise HTTPException(401, "Authentication required.")


async def _reflection_scheduler() -> None:
    while True:
        await asyncio.sleep(60)
        cognition.process_once(20)
        cognition.reflect()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global reflection_task
    reflection_task = asyncio.create_task(_reflection_scheduler())
    try:
        yield
    finally:
        if reflection_task:
            reflection_task.cancel()
            await asyncio.gather(reflection_task, return_exceptions=True)


app = FastAPI(
    title="ACOS HSC Prototype API",
    version="0.3.1",
    description="Safe cognitive operating-layer prototype for a future Hybrid Systematic Computer.",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest() -> FileResponse:
    return FileResponse(STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/service-worker.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(STATIC_DIR / "service-worker.js", media_type="application/javascript")


@app.websocket("/ws/events")
async def event_stream(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    authorization = websocket.headers.get("authorization")
    if settings.require_auth:
        supplied = authorization or (f"Bearer {token}" if token else None)
        if (
            not settings.api_token
            or not supplied
            or not hmac.compare_digest(supplied, settings.api_token)
        ):
            await websocket.close(code=1008, reason="Authentication required.")
            return

    await websocket.accept()
    last_id = 0
    try:
        while True:
            events = store.list_events(50)
            new_events = [event for event in reversed(events) if event["id"] > last_id]
            for event in new_events:
                await websocket.send_json(event)
                last_id = event["id"]
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "name": settings.app_name,
        "qiskit": qiskit_available(),
        "model": model_core.status(),
    }


@app.get("/api/model/status")
def model_status(_: None = Depends(require_auth)) -> dict:
    return model_core.status()


@app.get("/api/model/health")
def model_health(_: None = Depends(require_auth)) -> dict:
    return model_core.health()


@app.post("/api/model/infer")
def model_infer(payload: ModelRequestBody, _: None = Depends(require_auth)) -> dict:
    memories = store.search_memories(payload.goal, 10)
    result = model_core.complete(
        ModelRequest(goal=payload.goal, workspace=workspace.get(), memories=memories)
    )
    event = store.record_event("model.response", {"result": result.as_dict()}, "model-core")
    return {"result": result.as_dict(), "event_id": event["id"]}


@app.post("/api/search")
def trusted_search(payload: SearchRequest, _: None = Depends(require_auth)) -> dict:
    """Explicit trusted-source search; local fallback is the default."""
    invalid = [domain for domain in payload.domains if not is_trusted_domain(domain)]
    if invalid:
        raise HTTPException(422, "Search domains must be trusted .gov, .edu, .org, or public docs.")
    if payload.network:
        # Deliberately disabled until a reviewed provider is configured. This makes
        # the no-network-by-default boundary observable rather than implicit.
        return {
            "query": payload.query,
            "network": False,
            "provider": "local-fallback",
            "results": local_search(payload.query),
            "notice": "Network provider is disabled in this bounded simulation.",
        }
    return {
        "query": payload.query,
        "network": False,
        "provider": "local-fallback",
        "results": local_search(payload.query),
        "notice": "No network request was made. Results are advisory simulation data.",
    }


@app.get("/api/cognition/attention")
def cognition_attention(
    limit: int = Query(50, ge=1, le=100), _: None = Depends(require_auth)
) -> list[dict]:
    return store.next_attention(limit)


@app.post("/api/cognition/process")
def cognition_process(
    limit: int = Query(10, ge=1, le=100), _: None = Depends(require_auth)
) -> dict:
    processed = cognition.process_once(limit)
    return {"processed": processed, "count": len(processed), "advisory_only": True}


@app.post("/api/cognition/reflect")
def cognition_reflect(_: None = Depends(require_auth)) -> dict:
    return cognition.reflect()


@app.get("/api/cognition/reflections")
def cognition_reflections(
    limit: int = Query(20, ge=1, le=100), _: None = Depends(require_auth)
) -> list[dict]:
    return store.list_reflections(limit)


@app.post("/api/cognition/consolidate")
def cognition_consolidate(_: None = Depends(require_auth)) -> dict:
    return store.consolidate_memories()


@app.get("/api/cognition/memory-state")
def cognition_memory_state(_: None = Depends(require_auth)) -> dict:
    return store.memory_observability()


@app.post("/api/message", response_model=MessageResponse)
def message(payload: MessageRequest, _: None = Depends(require_auth)) -> dict:
    return engine.process(payload.text, payload.conversation_id, payload.context)


@app.get("/api/conversations/{conversation_id}")
def conversation_history(
    conversation_id: str, limit: int = Query(50, ge=1, le=100), _: None = Depends(require_auth)
) -> list[dict]:
    return store.list_chat_messages(conversation_id, limit)


@app.get("/api/conversations")
def conversations(_: None = Depends(require_auth)) -> list[dict]:
    return store.list_conversations()


@app.post("/api/conversations")
def create_conversation(
    payload: ConversationCreate | None = None, _: None = Depends(require_auth)
) -> dict:
    return store.create_conversation(payload.title if payload else "New chat")


@app.get("/api/conversations/{conversation_id}/metadata")
def conversation_metadata(conversation_id: str, _: None = Depends(require_auth)) -> dict:
    try:
        return store.get_conversation(conversation_id)
    except KeyError:
        raise HTTPException(404, "Conversation not found") from None


@app.patch("/api/conversations/{conversation_id}")
def rename_conversation(
    conversation_id: str, payload: ConversationUpdate, _: None = Depends(require_auth)
) -> dict:
    try:
        return store.update_conversation(conversation_id, payload.title)
    except KeyError:
        raise HTTPException(404, "Conversation not found") from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.get("/api/status")
def status(_: None = Depends(require_auth)) -> dict:
    return system_status()


@app.get("/api/workspace")
def get_workspace(_: None = Depends(require_auth)) -> dict:
    return workspace.get()


@app.patch("/api/workspace")
def patch_workspace(payload: WorkspaceUpdate, _: None = Depends(require_auth)) -> dict:
    return workspace.update(**payload.model_dump(exclude_none=True))


@app.get("/api/world")
def get_world(_: None = Depends(require_auth)) -> dict:
    return world.status()


@app.post("/api/world/time")
def advance_world(payload: WorldAdvance, _: None = Depends(require_auth)) -> dict:
    try:
        return world.advance(payload.steps)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@app.post("/api/world/entities")
def add_world_entity(payload: WorldEntityCreate, _: None = Depends(require_auth)) -> dict:
    try:
        return world.add_entity(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None


@app.get("/api/events")
def events(limit: int = Query(50, ge=1, le=200), _: None = Depends(require_auth)) -> list[dict]:
    return store.list_events(limit)


@app.post("/api/events")
def create_event(payload: EventCreate, _: None = Depends(require_auth)) -> dict:
    return store.record_event(payload.type, payload.payload, payload.source)


@app.post("/api/verify")
def verify(payload: VerificationRequest, _: None = Depends(require_auth)) -> dict:
    return verify_plan({"steps": payload.criteria}, payload.evidence)


@app.get("/api/backends")
def backends(_: None = Depends(require_auth)) -> dict:
    return {"available": available_backends(), "topology": compute.topology()}


@app.get("/api/compute/topology")
def compute_topology(_: None = Depends(require_auth)) -> list[dict]:
    return compute.topology()


@app.get("/api/compute/health")
def compute_health(_: None = Depends(require_auth)) -> list[dict]:
    return compute.topology()


@app.post("/api/compute/benchmark")
def compute_benchmark(_: None = Depends(require_auth)) -> list[dict]:
    return compute.benchmark()


@app.post("/api/compute/plan")
def compute_plan(payload: ComputeJobRequest, _: None = Depends(require_auth)) -> dict:
    return compute.plan(payload.operation, payload.payload)


@app.post("/api/compute/jobs")
def compute_submit(payload: ComputeJobRequest, _: None = Depends(require_auth)) -> dict:
    try:
        return compute.submit(
            payload.operation,
            payload.payload,
            payload.backend,
            payload.approved,
            payload.timeout,
            payload.retries,
        )
    except KeyError:
        raise HTTPException(404, "Backend not found") from None
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except (RuntimeError, ValueError, TimeoutError) as exc:
        raise HTTPException(409, str(exc)) from None


@app.get("/api/compute/jobs")
def compute_jobs(
    limit: int = Query(50, ge=1, le=200), _: None = Depends(require_auth)
) -> list[dict]:
    return store.list_compute_jobs(limit)


@app.get("/api/compute/jobs/{job_id}")
def compute_job(job_id: str, _: None = Depends(require_auth)) -> dict:
    try:
        return store.get_compute_job(job_id)
    except KeyError:
        raise HTTPException(404, "Job not found") from None


@app.post("/api/hybrid/plan")
def hybrid_plan(payload: HybridGraphRequest, _: None = Depends(require_auth)) -> dict:
    try:
        graph = HybridGraph.model_validate(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return graph.model_dump()


@app.post("/api/hybrid/jobs")
def hybrid_submit(payload: HybridGraphRequest, _: None = Depends(require_auth)) -> dict:
    try:
        return hybrid.execute(HybridGraph.model_validate(payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from None
    except (RuntimeError, TimeoutError) as exc:
        raise HTTPException(409, str(exc)) from None


@app.get("/api/hybrid/jobs")
def hybrid_jobs(
    limit: int = Query(50, ge=1, le=200), _: None = Depends(require_auth)
) -> list[dict]:
    return store.list_hybrid_jobs(limit)


@app.get("/api/hybrid/jobs/{job_id}")
def hybrid_job(job_id: str, _: None = Depends(require_auth)) -> dict:
    try:
        return store.get_hybrid_job(job_id)
    except KeyError:
        raise HTTPException(404, "Hybrid job not found") from None


@app.post("/api/hybrid/reference/{name}")
def hybrid_reference(name: str, _: None = Depends(require_auth)) -> dict:
    try:
        return hybrid.execute(reference_workflow(name))
    except KeyError:
        raise HTTPException(404, "Reference workflow not found") from None
    except (PermissionError, RuntimeError, TimeoutError) as exc:
        raise HTTPException(409, str(exc)) from None


@app.post("/api/hybrid/compare")
def hybrid_compare(values: list[float], _: None = Depends(require_auth)) -> dict:
    return hybrid.compare_classical_baseline(values)


@app.get("/api/memories")
def memories(
    kind: MemoryKind | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(require_auth),
) -> list[dict]:
    return store.search_memories(q, limit, kind) if q else store.list_memories(kind, limit)


@app.post("/api/memories")
def create_memory(payload: MemoryCreate, _: None = Depends(require_auth)) -> dict:
    decision = permissions.check("memory.write")
    if not decision.allowed:
        raise HTTPException(403, decision.reason)
    return store.add_memory(payload.kind, payload.content, payload.importance, payload.metadata)


@app.get("/api/skills")
def list_skills(_: None = Depends(require_auth)) -> list[dict]:
    return skills.store.list_skills()


@app.post("/api/skills")
def create_skill(payload: SkillCreate, _: None = Depends(require_auth)) -> dict:
    decision = permissions.check("skill.create")
    if not decision.allowed:
        raise HTTPException(403, decision.reason)
    return skills.create(payload.name, payload.description, payload.trigger, payload.steps)


@app.post("/api/skills/execute")
def record_skill(payload: SkillExecution, _: None = Depends(require_auth)) -> dict:
    try:
        return skills.record(payload.name, payload.success)
    except KeyError:
        raise HTTPException(404, "Skill not found") from None


@app.post("/api/tools/run")
def run_tool(payload: ToolRequest, _: None = Depends(require_auth)) -> dict:
    decision = permissions.check(payload.action, approved=payload.approved)
    store.audit(
        "tool.request",
        {"action": payload.action, "allowed": decision.allowed, "level": decision.level},
    )
    if not decision.allowed:
        raise HTTPException(403, decision.reason)

    if payload.action == "system.status":
        return {"action": payload.action, "result": system_status()}
    if payload.action == "filesystem.list":
        return {"action": payload.action, "result": list_workspace(settings.workspace_dir)}
    if payload.action == "quantum.bell":
        return {"action": payload.action, "result": bell_state()}
    raise HTTPException(400, "Tool action is not registered")


@app.get("/api/audit")
def audit(limit: int = Query(50, ge=1, le=200), _: None = Depends(require_auth)) -> list[dict]:
    return store.list_audit(limit)
