# 🚀 Deploy GODML con Docker y GitHub Actions

Este repositorio construye y publica automáticamente tu imagen Docker a DockerHub y luego permite desplegarla (opcionalmente).

## ✅ Requisitos

- Tener una cuenta en Docker Hub
- Agregar estos secretos en GitHub:
  - `DOCKER_USERNAME`
  - `DOCKER_PASSWORD`

## 🧪 Flujo

1. Push a `main`
2. GitHub Actions:
   - Construye imagen Docker
   - La publica en DockerHub
   - Ejecuta despliegue (ajustable)

## 🧩 Personalización

- Cambia el `CMD` en Dockerfile según tu app
- Modifica el paso `deploy` si usas AWS ECS, EC2, o K8s

---

> Plantilla generada con ❤️ por el framework **GODML**
