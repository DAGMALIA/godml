from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict

from godml.dataprep_service.schema import Recipe as DataprepRecipe


class DatasetConfig(BaseModel):
    uri: str
    hash: Optional[str] = "auto"
    target: Optional[str] = None
    dataprep: Optional[Union[DataprepRecipe, List[DataprepRecipe], Dict[str, Any]]] = None


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
    compliance: Optional[str] = None 
    tags: Optional[List[Dict[str, str]]] = Field(default_factory=list)


class DeployConfig(BaseModel):
    realtime: bool = False
    batch_output: Optional[str]


class PipelineDefinition(BaseModel):
    name: str
    version: str
    provider: str
    description: Optional[str] = None
    dataset: DatasetConfig
    model: ModelConfig
    metrics: List[Metric]
    governance: Governance = Field(default_factory=lambda: Governance(owner="", tags=[]))
    deploy: DeployConfig
    # Nuevo: DataPrep puede ser 1 receta o varias (opcional)
    #dataprep: Optional[Union[DataprepRecipe, List[DataprepRecipe]]] = None

# Resultado del pipeline (puede moverse si prefieres)
class ModelResult(BaseModel):
    model: Any
    predictions: Optional[Any] = None
    metrics: Optional[Dict[str, float]] = None
    output_path: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
