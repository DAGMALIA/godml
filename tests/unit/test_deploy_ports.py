# test_deploy_ports.py
"""
F1-08: `godml deploy` published `-p {port}:{port}` but the container always
listens on 8000 (Dockerfile CMD, EXPOSE and healthcheck), so any environment
whose port was not 8000 (qa: 8001, prod: 80) was unreachable. `godml serve`
ran uvicorn with reload=True in every environment.
"""

import pytest
import yaml

import godml.cli.commands.deploy as deploy
import godml.cli.commands.serve as serve

DEPLOY_CONFIG = {
    "dev": {"host": "0.0.0.0", "port": 8000, "docker_tag": "demo-dev"},
    "qa": {"host": "0.0.0.0", "port": 8001, "docker_tag": "demo-qa"},
    "prod": {"host": "0.0.0.0", "port": 80, "docker_tag": "demo-prod"},
}


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "godml.yml").write_text(
        yaml.safe_dump({"deploy_config": DEPLOY_CONFIG})
    )
    return tmp_path


@pytest.fixture
def docker_calls(monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.setattr(deploy, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(deploy.subprocess, "run", lambda args, **kw: calls.append(args))
    return calls


def published_port(calls) -> str:
    run = next(c for c in calls if c[1] == "run")
    return run[run.index("-p") + 1]


@pytest.mark.parametrize("env, host_port", [("dev", 8000), ("qa", 8001), ("prod", 80)])
def test_deploy_maps_host_port_to_container_8000(project, docker_calls, env, host_port):
    deploy.deploy_command("demo", env)
    assert published_port(docker_calls) == f"{host_port}:8000"


def test_deploy_does_not_pass_an_unused_port_env(project, docker_calls):
    deploy.deploy_command("demo", "qa")
    run = next(c for c in docker_calls if c[1] == "run")
    assert not any(arg.startswith("PORT=") for arg in run)


@pytest.fixture
def uvicorn_calls(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(serve.uvicorn, "run", lambda app, **kw: calls.append(kw))
    return calls


@pytest.mark.parametrize("env, reload", [("dev", True), ("qa", False), ("prod", False)])
def test_serve_reloads_only_in_dev(project, uvicorn_calls, env, reload):
    serve.serve_command(env)
    assert uvicorn_calls[0]["reload"] is reload
    assert uvicorn_calls[0]["port"] == DEPLOY_CONFIG[env]["port"]


def test_container_port_matches_dockerfile_template():
    """The mapping is only right while the image really listens on CONTAINER_PORT."""
    import re

    from godml.utils.yaml_utils import generate_dockerfile_txt

    dockerfile = generate_dockerfile_txt("0.0.0")
    port = str(deploy.CONTAINER_PORT)
    assert re.search(rf'"--port",\s*"{port}"', dockerfile)
    assert re.search(rf"^EXPOSE {port}$", dockerfile, re.MULTILINE)
    assert f"localhost:{port}/health" in dockerfile
