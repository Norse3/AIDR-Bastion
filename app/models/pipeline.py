from pydantic import BaseModel

from app.core.enums import ActionStatus, RuleAction


class TaskRequest(BaseModel):
    prompt: str
    task_id: str | int | None = None
    pipeline_flow: str = "default"


class TriggeredRuleData(BaseModel):
    details: str
    action: RuleAction
    id: str | None = None
    name: str | None = None
    body: str | None = None
    severity: str | None = None
    cwe_id: str | None = None


class PipelineResult(BaseModel):
    status: ActionStatus
    name: str
    triggered_rules: list[TriggeredRuleData] = []


class TaskResult(BaseModel):
    status: ActionStatus
    pipelines: list[PipelineResult]


class TaskResponse(BaseModel):
    status: ActionStatus
    result: list[PipelineResult] | None = None


class PipelineInfo(BaseModel):
    id: str
    name: str
    enabled: bool
    description: str


class FlowInfo(BaseModel):
    flow_name: str
    pipelines: list[PipelineInfo]


class FlowsResponse(BaseModel):
    flows: list[FlowInfo]
