"""FastAPI REST API for the Website Redesigner."""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

app = FastAPI(title="Website Redesigner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_BASE = Path("./output")


# --- Models ---

class RedesignRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class Job(BaseModel):
    job_id: str
    url: str
    status: str = "pending"  # pending | processing | done | failed
    output_dir: Optional[str] = None
    error: Optional[str] = None


# --- Job store ---

jobs: dict[str, Job] = {}


# --- Background processing ---

async def process_url_async(job_id: str, url: str):
    """Run the redesign pipeline in a background thread."""
    from redesign import process_url

    jobs[job_id].status = "processing"
    try:
        output_dir = await asyncio.to_thread(process_url, url, OUTPUT_BASE)
        jobs[job_id].status = "done"
        jobs[job_id].output_dir = str(output_dir)
    except Exception as e:
        jobs[job_id].status = "failed"
        jobs[job_id].error = str(e)


# --- Allowed files ---

ALLOWED_FILES = {"original.png", "redesign.png", "redesign.html", "content.json"}

MEDIA_TYPES = {
    ".png": "image/png",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json",
}


# --- Routes ---

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/redesign", status_code=202)
async def create_redesign(req: RedesignRequest, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex[:12]
    jobs[job_id] = Job(job_id=job_id, url=req.url)
    background_tasks.add_task(process_url_async, job_id, req.url)
    return {"job_id": job_id, "status": "pending"}


@app.get("/redesign/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    result = {"job_id": job.job_id, "url": job.url, "status": job.status}

    if job.status == "done" and job.output_dir:
        output_dir = Path(job.output_dir)
        result["files"] = [
            f.name for f in output_dir.iterdir()
            if f.name in ALLOWED_FILES
        ]

    if job.status == "failed" and job.error:
        result["error"] = job.error

    return result


@app.get("/redesign/{job_id}/{filename}")
async def get_job_file(job_id: str, filename: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail="File not found")

    job = jobs[job_id]
    if not job.output_dir:
        raise HTTPException(status_code=404, detail="No output available")

    file_path = Path(job.output_dir) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = MEDIA_TYPES.get(file_path.suffix, "application/octet-stream")
    return FileResponse(file_path, media_type=media_type)
