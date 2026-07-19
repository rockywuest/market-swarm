"""REST API routes for Market Swarm.

All endpoints in a single file — the project is small enough that
splitting into multiple routers would add overhead without benefit.
"""

import asyncio
import os
import tempfile
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from ..engine import run_simulation_async
from ..registry import get_pack, list_packs
from .jobs import JobManager
from .models import (
    JobResponse,
    PackInfo,
    PersonaInfo,
    ResultResponse,
    SimulationRequest,
)

router = APIRouter(prefix="/api")

# Singleton job manager — initialized in main.py via app.state
_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    if _job_manager is None:
        raise RuntimeError("JobManager not initialized")
    return _job_manager


def init_job_manager(manager: JobManager) -> None:
    global _job_manager
    _job_manager = manager


async def verify_api_key(request: Request) -> None:
    """Check X-API-Key header. Disabled if env var is unset (dev mode)."""
    api_key = os.getenv("MARKET_SWARM_API_KEY")
    if api_key is None:
        return
    if request.headers.get("X-API-Key") != api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Set X-API-Key header.",
        )


# --- Pack endpoints (public) ---


@router.get("/packs", response_model=list[PackInfo])
async def get_packs() -> list[PackInfo]:
    """List all available industry packs."""
    packs = list_packs()
    return [
        PackInfo(
            product_type=p.product_type,
            display_name=p.display_name,
            version=p.version,
            description=p.description,
            persona_count=len(p.personas),
        )
        for p in packs
    ]


@router.get("/packs/{pack_type}/personas", response_model=list[PersonaInfo])
async def get_personas(pack_type: str) -> list[PersonaInfo]:
    """List all personas for an industry pack."""
    try:
        pack = get_pack(pack_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [
        PersonaInfo(
            name=p.name,
            type=p.type,
            retailer=p.retailer,
            pack_type=pack_type,
        )
        for p in pack.personas
    ]


# --- Simulation endpoints (auth required) ---


@router.post("/simulations", response_model=JobResponse, status_code=201)
async def create_simulation(
    request: SimulationRequest,
    _auth: None = Depends(verify_api_key),
    manager: JobManager = Depends(get_job_manager),
) -> JobResponse:
    """Submit a new simulation job. Returns immediately with job ID."""
    # Validate YAML
    try:
        parsed = yaml.safe_load(request.product_yaml)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    if not isinstance(parsed, dict) or "product" not in parsed:
        raise HTTPException(
            status_code=400,
            detail="YAML must contain a 'product' key at root level",
        )

    product_data = parsed["product"]
    product_name = product_data.get("name", "Unknown")
    pack_type = request.pack_override or product_data.get("product_type", "fmcg")

    # Verify pack exists
    try:
        get_pack(pack_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create job
    job = manager.create_job(
        product_yaml=request.product_yaml,
        product_name=product_name,
        pack_type=pack_type,
        model_name=request.model_name,
    )

    # Fire background execution
    asyncio.create_task(_run_simulation_background(job.id, manager))

    return job.to_response()


@router.get("/simulations", response_model=list[JobResponse])
async def list_simulations(
    _auth: None = Depends(verify_api_key),
    manager: JobManager = Depends(get_job_manager),
) -> list[JobResponse]:
    """List all simulation jobs (newest first)."""
    return [job.to_response() for job in manager.list_jobs()]


@router.get("/simulations/{job_id}", response_model=JobResponse)
async def get_simulation(
    job_id: str,
    _auth: None = Depends(verify_api_key),
    manager: JobManager = Depends(get_job_manager),
) -> JobResponse:
    """Get status of a simulation job."""
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job.to_response()


# --- Result endpoints ---


@router.get("/results/{job_id}", response_model=None)
async def get_result(
    job_id: str,
    _auth: None = Depends(verify_api_key),
    manager: JobManager = Depends(get_job_manager),
) -> ResultResponse | JSONResponse:
    """Get full simulation result. Returns 202 if still running."""
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.status in ("pending", "running"):
        return JSONResponse(
            status_code=202,
            content={
                "status": job.status.value,
                "message": "Simulation still in progress",
                "progress": {
                    "completed": job.progress_completed,
                    "total": job.progress_total,
                },
            },
        )

    if job.status == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {job.error}",
        )

    # Load persisted result
    result_data = manager.load_result(job_id)
    if result_data is None:
        raise HTTPException(status_code=404, detail="Result file not found")

    execution_time = 0.0
    if job.started_at and job.completed_at:
        execution_time = (job.completed_at - job.started_at).total_seconds()

    return ResultResponse(
        job_id=job_id,
        product=result_data.get("product", {}),
        responses=result_data.get("responses", []),
        avg_score=result_data.get("avg_score", 0.0),
        listing_rate=result_data.get("listing_rate", 0.0),
        top_objections=result_data.get("top_objections", []),
        top_suggestions=result_data.get("top_suggestions", []),
        channel_scores=result_data.get("channel_scores", {}),
        disclaimer=result_data.get("disclaimer", ""),
        model_used=job.model_name,
        execution_time_seconds=execution_time,
        created_at=job.created_at,
    )


# --- Export endpoint ---


@router.get("/results/{job_id}/export")
async def export_result(
    job_id: str,
    format: str = "pdf",
    _auth: None = Depends(verify_api_key),
    manager: JobManager = Depends(get_job_manager),
):
    """Export simulation result as PDF or PPTX."""
    from fastapi.responses import Response

    from ..export import export_pdf, export_pptx

    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Simulation not yet completed")

    result_data = manager.load_result(job_id)
    if result_data is None:
        raise HTTPException(status_code=404, detail="Result file not found")

    product_name = result_data.get("product", {}).get("name", "result")
    safe_name = product_name.replace(" ", "_").lower()

    if format == "pptx":
        content = export_pptx(result_data)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pptx"'},
        )
    else:
        content = export_pdf(result_data)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
        )


# --- Background execution ---


async def _run_simulation_background(job_id: str, manager: JobManager) -> None:
    """Execute simulation with parallel LLM calls, update job status."""
    job = manager.get_job(job_id)
    if job is None:
        return

    tmp_path = None
    try:
        # Write YAML to temp file (engine expects file path)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
            tmp.write(job.product_yaml)
            tmp_path = tmp.name

        # Determine persona count for progress tracking
        pack = get_pack(job.pack_type)
        manager.mark_running(job_id, len(pack.personas))

        # Determine pack_override
        yaml_pack_type = (
            yaml.safe_load(job.product_yaml).get("product", {}).get("product_type", "fmcg")
        )
        pack_override = job.pack_type if job.pack_type != yaml_pack_type else None

        # Progress callback for polling UI
        def on_progress(completed: int, total: int) -> None:
            manager.update_progress(job_id, completed)

        # Run async engine with parallel LLM calls
        result = await run_simulation_async(
            tmp_path,
            model=job.model_name,
            pack_override=pack_override,
            on_progress=on_progress,
        )

        manager.save_result(job_id, result)
        manager.mark_completed(job_id)

    except Exception as e:
        manager.mark_failed(job_id, str(e))

    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
