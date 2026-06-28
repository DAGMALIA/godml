import yaml
from godml.config_service.schema import (
    PipelineDefinition,
    DatasetConfig,
    ModelConfig,
    Hyperparameters,
    Metric,
    Governance,
    DeployConfig
)
from importlib.resources import files

def update_dataset_hash_in_yaml(yaml_path: str, new_hash: str):
    """
    Modifica el archivo YAML para reemplazar dataset.hash con el valor calculado.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if "dataset" not in config:
        config["dataset"] = {}
    config["dataset"]["hash"] = new_hash

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)


def generate_readme_md(project_name: str) -> str:
    """
    Carga la plantilla README_TEMPLATE.txt desde godml.utils y reemplaza el nombre del proyecto.
    """
    try:
        template_path = files("godml.utils").joinpath("README_TEMPLATE.txt")
        template = template_path.read_text(encoding="utf-8")
        return template.format(project_name=project_name)
    except Exception as e:
        raise RuntimeError(f"Error generando README para {project_name}: {e}")


def generate_dockerfile_txt() -> str:
    """
    Carga la plantilla DOCKERFILE_TEMPLATE.txt desde godml.utils.
    """
    try:
        template_path = files("godml.utils").joinpath("DOCKERFILE_TEMPLATE.txt")
        return template_path.read_text(encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Error generando Dockerfile por defecto: {e}")


def generate_default_yaml(project_name: str) -> str:
    """Genera un archivo godml.yml limpio, validado y legible."""
    try:
        pipeline = PipelineDefinition(
            name=project_name,
            version="1.0.0",
            provider="mlflow",
            dataset=DatasetConfig(
                uri="./data/your_dataset.csv",
                hash="auto"
            ),
            model=ModelConfig(
                type="xgboost",
                source="core",
                hyperparameters=Hyperparameters(
                    max_depth=5,
                    eta=0.3,
                    objective="binary:logistic"
                )
            ),
            metrics=[
                Metric(name="auc", threshold=0.85),
                Metric(name="accuracy", threshold=0.80)
            ],
            governance=Governance(
                owner="your-team@company.com",
                compliance="pci-dss",
                tags=[
                    {"project": project_name},
                    {"environment": "development"}
                ]
            ),
            deploy=DeployConfig(
                realtime=False,
                batch_output="./outputs/predictions.csv",
                model_output="./models/dev/model.pkl"
            )
        )

        yaml_dict = pipeline.model_dump()

        yaml_dict["deploy_config"] = {
            "dev": {
                "docker_tag": "godml:dev",
                "port": 8000,
                "host": "127.0.0.1"
            },
            "qa": {
                "docker_tag": "godml:qa",
                "port": 8080,
                "host": "127.0.0.1"
            },
            "prod": {
                "docker_tag": "godml:prod",
                "port": 80,
                "host": "127.0.0.1"
            }
        }

        # Limpieza previa de saltos de línea escapados
        yaml_str = yaml.safe_dump(
            yaml_dict,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False
        ).replace("\\n", "\n")

        return yaml_str

    except Exception as e:
        raise RuntimeError(f"Error generando YAML para {project_name}: {e}")
