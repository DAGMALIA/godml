# godml/deploy_service/env_config.py

ENVIRONMENTS = {
    "development": {
        "port": 8000,
        "host": "0.0.0.0",
        "reload": True,
        "docker_tag": "godml-dev"
    },
    "staging": {
        "port": 8001,
        "host": "0.0.0.0",
        "reload": False,
        "docker_tag": "godml-staging"
    },
    "production": {
        "port": 80,
        "host": "0.0.0.0",
        "reload": False,
        "docker_tag": "godml-prod"
    }
}
