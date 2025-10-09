from fastapi import APIRouter

from app.manager import pipeline_manager
from app.models.pipeline import (
    FlowInfo,
    FlowsResponse,
    PipelineInfo,
    TaskRequest,
    TaskResult,
)

flow_router = APIRouter(prefix="/flow", tags=["Flow API"])


@flow_router.post("/run")
async def run_flow(request: TaskRequest) -> TaskResult:
    task_result = await pipeline_manager.run_pipeline(
        prompt=request.prompt, pipeline_flow=request.pipeline_flow, task_id=request.task_id
    )
    return task_result


@flow_router.get("/list")
async def get_flows_list() -> FlowsResponse:
    """
    Get list of all available flows and their pipelines.

    Returns:
        FlowsResponse: List of flows with pipeline information
    """
    flows = []

    for flow_name, pipelines in pipeline_manager.pipeline_flows.items():
        pipeline_infos = [PipelineInfo(name=pipeline.name, enabled=pipeline.enabled) for pipeline in pipelines]
        flows.append(FlowInfo(flow_name=flow_name, pipelines=pipeline_infos))

    return FlowsResponse(flows=flows)
