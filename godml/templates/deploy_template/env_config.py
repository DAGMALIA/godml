
ENVIRONMENTS = {
    "dev": {
        "port": 8000,
        "host": "0.0.0.0",
        "reload": True,
        "docker_tag": "godml-dev"
    },
    "qa": {
        "port": 8001,
        "host": "0.0.0.0",
        "reload": False,
        "docker_tag": "godml-staging"
    },
    "prod": {
        "port": 80,
        "host": "0.0.0.0",
        "reload": False,
        "docker_tag": "godml-prod"
    }
}