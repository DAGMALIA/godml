# CLAUDE.md — Instrucciones para Claude Code en GoDML 2.0

## Contexto

GoDML (Governed · Observable · Declarative ML) es un framework MLOps open source publicado en PyPI. Se está construyendo la versión 2.0 en torno a 5 pilares: **Train, Govern, Serve, Observe, Tools**. Tiene usuarios activos, así que no se rompe la API de 1.x sin shim de compatibilidad ni ruta de migración.

El plan completo y el estado del proyecto viven en `GODML_2_0_PLAN.md`. **Ese archivo es la fuente de verdad.**

## Al iniciar cada sesión

1. Lee `GODML_2_0_PLAN.md`: tablero de estado (§0), decisiones (§3) y log (§7).
2. Trabaja en la **fase activa** y toma la siguiente tarea ⬜ en orden, salvo que el usuario indique otra.
3. Si una tarea depende de una decisión ⬜ en §3, detente y pregunta antes de avanzar.

## Cómo trabajar una tarea

1. Marca la tarea como 🟨 en el plan.
2. Crea una rama `godml2/<ID-tarea>` (por ejemplo `godml2/F1-01`).
3. Si es un bug: escribe primero el test que lo reproduce y confirma que falla.
4. Implementa el cambio mínimo y correcto.
5. Corre `ruff check`, `ruff format --check`, `mypy` (en los módulos tocados) y `pytest`.
6. Commit con Conventional Commits, mencionando el ID: `fix(govern): compliance fail-closed [F1-01]`.
7. Marca la tarea como ✅ (o ⛔ con la razón) y agrega una fila al log de estado (§7).
8. Si cerraste una fase, actualiza su fila en el tablero (§0) y la **fase activa**.

## Reglas no negociables

- **Fail-closed en gobernanza.** Nunca `except Exception: pass` ni devolver datos sin procesar ante un error de compliance o validación.
- **Sin efectos colaterales al importar.** No crear archivos o carpetas, no `logging.basicConfig`, no `warnings.filterwarnings` global.
- **Sin `print` en la librería.** Usa `logging.getLogger("godml.<modulo>")`. La salida visual es solo de la CLI.
- **Dependencias por pilar.** Una dependencia nueva va en el extra de su pilar, nunca en el core sin aprobación. Los imports de extras opcionales se hacen dentro de funciones o con guardas que lancen `MissingExtra` con el comando de instalación.
- **Dependencias entre módulos.** `core` no importa pilares. Los pilares solo importan `core` (y `govern` cuando aplique).
- **No documentar lo que no existe.** README y docs solo describen funcionalidad implementada y probada.
- **Una sola versión.** Nunca escribir la versión del paquete como literal; usar `importlib.metadata`.
- **Seguridad.** Validar rutas con `Path.resolve()` + `is_relative_to`; no cargar pickles desde rutas no validadas; no secretos en código ni ejemplos.
- **Tests herméticos.** Ningún test escribe fuera de `tmp_path` ni importa módulos con efectos colaterales a nivel módulo; los scripts ejecutables deben tener la lógica bajo `if __name__ == '__main__':`.

## Comandos útiles

```bash
pip install -e ".[all,dev]"
pytest -q
pytest --cov=godml --cov-report=term-missing
ruff check . && ruff format --check .
mypy godml
bandit -r godml -c pyproject.toml
```

## Reporte de estado para el chat de planeación

Al final de cada sesión, entrega este bloque para que el usuario lo copie en el chat de planeación:

```
## Reporte GoDML 2.0 — <fecha>
Fase activa: <Fx>
Completadas: <IDs>
En progreso: <IDs>
Bloqueadas: <IDs + razón>
Decisiones que necesito: <lista o "ninguna">
Hallazgos nuevos (bugs/deuda no listados en el plan): <lista>
Siguiente paso propuesto: <ID + descripción>
```
