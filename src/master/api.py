from fastapi import FastAPI, HTTPException, Body, Path, Query
from typing import List, Optional, Dict
from pydantic import BaseModel
import uvicorn
from .master_node import MasterNode
from common.fault_tolerance import fault_manager

# Initialize FastAPI app
app = FastAPI(title="Crawler-Indexer API", description="API for distributed crawler and indexer")

# Initialize master node
master_node = MasterNode()

# Data models
class CrawlRequest(BaseModel):
    urls: List[str]
    allowed_domains: Optional[List[str]] = None
    job_id: Optional[str] = None
    depth: Optional[int] = 1

class SearchRequest(BaseModel):
    query: str
    search_type: Optional[str] = "match"

# API routes
@app.get("/")
def read_root():
    return {"message": "Welcome to the Crawler-Indexer API"}

@app.post("/crawl", response_model=Dict)
def crawl(request: CrawlRequest):
    """
    Submit URLs for crawling and indexing
    """
    try:
        result = master_node.submit_crawl_job(
            urls=request.urls,
            allowed_domains=request.allowed_domains,
            job_id=request.job_id,
            depth=request.depth
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/job/{job_id}", response_model=Dict)
def get_job_status(job_id: str):
    """
    Get the status of a job
    """
    try:
        result = master_node.get_job_status(job_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search", response_model=List[Dict])
def search(request: SearchRequest):
    """
    Search through the indexed content
    """
    try:
        results = master_node.search_content(request.query, search_type=request.search_type)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def check_health():
    """Check system health"""
    return master_node.check_health()

# Add fault tolerance endpoints
@app.get("/fault-tolerance")
def get_fault_tolerance_status():
    """Get fault tolerance status"""
    return master_node.check_fault_tolerance()

@app.get("/fault-tolerance/nodes")
def get_nodes_status():
    """Get status of all nodes"""
    from common.monitor import check_node_health
    return check_node_health(max_age=300)  # Get nodes seen in the last 5 minutes

# Entry point
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
