from godml.config_service.schema import (
    PipelineDefinition,
    DatasetConfig,
    ModelConfig,
    Hyperparameters,
    Metric,
    Governance,
    DeployConfig
)

import yaml
from importlib.resources import files
from pathlib import Path

def update_dataset_hash_in_yaml(yaml_path: str, new_hash: str):
    """
    Modifica el archivo YAML para reemplazar dataset.hash con el valor calculado.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config['dataset']['hash'] = new_hash

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)

def generate_default_yaml(project_name: str) -> str:
    """Genera YAML válido a partir de PipelineDefinition con deploy_config incluido."""

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
            batch_output="./outputs/predictions.csv"
        )
    )

    # Convertimos a dict
    yaml_dict = pipeline.model_dump()

    # Agregamos manualmente la sección de deploy_config
    yaml_dict["deploy_config"] = {
        "dev": {
            "docker_tag": "godml:dev",
            "port": 8000,
            "host": "0.0.0.0"
        },
        "qa": {
            "docker_tag": "godml:qa",
            "port": 8080,
            "host": "0.0.0.0"
        },
        "prod": {
            "docker_tag": "godml:prod",
            "port": 80,
            "host": "0.0.0.0"
        }
    }

    return yaml.dump(yaml_dict, sort_keys=False)


def generate_readme_md(project_name: str) -> str:
    template_path = files("godml.utils").joinpath("README_TEMPLATE.txt")
    template = template_path.read_text(encoding="utf-8")
    return template.format(project_name=project_name)

def generate_dockerfile_txt() -> str:
    template_path = files("godml.utils").joinpath("DOCKERFILE_TEMPLATE.txt")
    template = template_path.read_text(encoding="utf-8")
    return template