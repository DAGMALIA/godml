## ⚠️ Vulnerabilidades conocidas ignoradas temporalmente

Actualmente, el paquete `mlflow==3.4.0` contiene las siguientes vulnerabilidades no parchadas oficialmente:

- 71577, 71578, 71579, 71584, 71587, 71691, 71692, 71693

Estas han sido marcadas como `ignored` en nuestra política debido a que:

- No existe aún una versión segura publicada.
- No se cargan modelos de fuentes externas (RCE mitigado).
- Se monitorea semanalmente su estado vía Safety CLI.

Ver: https://data.safetycli.com/p/pypi/mlflow/eda/?from=3.4.0
