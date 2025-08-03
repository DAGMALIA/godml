from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DatasetConfig(BaseModel):
    uri: str
    hash: Optional[str] = "auto"


class Hyperparameters(BaseModel):
    max_depth: Optional[int] = None
    eta: Optional[float] = None
    objective: Optional[str] = None
    n_estimators: Optional[int] = None
    max_features: Optional[str] = None
    random_state: Optional[int] = None


class ModelConfig(BaseModel):
    type: str
    source: Optional[str] = "core"
    hyperparameters: Hyperparameters


class Metric(BaseModel):
    name: str
    threshold: float


class GovernanceTag(BaseModel):
    compliance: Optional[str]
    project: Optional[str]


class Governance(BaseModel):
    owner: str
    tags: Optional[List[Dict[str, str]]] = []


class DeployConfig(BaseModel):
    realtime: bool = False
    batch_output: Optional[str]


class PipelineDefinition(BaseModel):
    name: str
    version: str
    provider: str
    dataset: DatasetConfig
    model: ModelConfig
    metrics: List[Metric]
    governance: Governance
    deploy: DeployConfig


# Resultado del pipeline (puede moverse si prefieres)
class ModelResult(BaseModel):
    model: Any
    predictions: Optional[Any] = None
    metrics: Optional[Dict[str, float]] = None
    output_path: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
