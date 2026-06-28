from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from godml.dataprep_service.schema import Recipe as DataprepRecipe

class DatasetConfig(BaseModel):
    uri: str
    compliant_output: Optional[str] = None
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

class Governance(BaseModel):
    owner: str
    compliance: Optional[str] = None
    policy: Optional[str] = Field(default="mask_sensitive")  # drop_sensitive | mask_sensitive | hash_sensitive
    tags: Optional[List[Dict[str, str]]] = Field(default_factory=list)

class DeployConfig(BaseModel):
    realtime: bool = False
    batch_output: Optional[str] = None
    model_output: Optional[str] = None  # 🆕 se agrega para guardar el modelo localmente

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

# 🧩 Resultado estandarizado de un pipeline GODML
class ModelResult(BaseModel):
    """
    Resultado del pipeline GODML, con trazabilidad y seguridad.
    """
    model: Any
    predictions: Optional[Any] = None
    metrics: Optional[Dict[str, float]] = None
    output_path: Optional[str] = None
    model_path: Optional[str] = None   # 🆕 ruta al modelo guardado (.pkl)

    model_config = ConfigDict(arbitrary_types_allowed=True)
