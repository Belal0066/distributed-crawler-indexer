from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from master_node import MasterNode

app = FastAPI(title="Master Node API", description="API for submitting crawl and index jobs.")

# Initialize MasterNode
master_node = MasterNode()

# --- Models ---
class CrawlJobRequest(BaseModel):
    urls: List[str]
    allowed_domains: Optional[List[str]] = None
    job_id: Optional[str] = None
    depth: Optional[int] = 1

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    crawl_status: Optional[str] = None
    index_status: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[dict]

# --- API Endpoints ---
@app.post("/submit_crawl", response_model=JobStatusResponse)
def submit_crawl(job: CrawlJobRequest):
    """Submit a new crawl job and trigger indexing."""
    try:
        result = master_node.submit_crawl_job(
            urls=job.urls,
            allowed_domains=job.allowed_domains,
            job_id=job.job_id,
            depth=job.depth
        )
        return JobStatusResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/job_status/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str):
    """Get the status of both crawl and index jobs."""
    try:
        result = master_node.get_job_status(job_id)
        return JobStatusResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=SearchResponse)
def search(query: str):
    """Search through indexed content using Elasticsearch."""
    try:
        results = master_node.search_content(query)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    """Check the health of all components."""
    return master_node.check_health()
