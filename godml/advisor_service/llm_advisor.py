from __future__ import annotations

import os
from pathlib import Path

# Default model path resolves to ~/.gpt4all/models on any OS
_DEFAULT_MODEL_PATH = os.environ.get(
    "GODML_GPT4ALL_PATH",
    str(Path.home() / ".gpt4all" / "models"),
)
_DEFAULT_MODEL_NAME = os.environ.get(
    "GODML_GPT4ALL_MODEL",
    "q4_0-orca-mini-3b.gguf",
)


class LLMAdvisor:
    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL_NAME,
        model_path: str = _DEFAULT_MODEL_PATH,
    ):
        try:
            from gpt4all import GPT4All
        except ImportError as e:
            raise ImportError(
                "El advisor LLM requiere gpt4all. "
                "Instala con: pip install godml[advisor]"
            ) from e
        self.model = GPT4All(model_name, model_path=model_path)

    def suggest_recipe(self, dataset_summary: str, language: str = "es") -> str:
        prompt = f"""
Eres un experto en ciencia de datos y en GODML.
Eres un asistente experto en DataPrep con GODML.
Genera SIEMPRE un JSON valido con comillas dobles.

REGLAS:
- Si hay mas de 10% de nulos en una columna, aplica "fillna".
- Si una columna tiene >90% nulos, sugiere descartarla.
- Codifica siempre variables categoricas con "one_hot".
- Incluye "drop_duplicates".
- Si hay una columna de fecha, sugiere "extract_date_parts".
- Si hay un target binario, no lo toques en one_hot.
- Si no hay target, NO inventes uno.

Responde siempre en {language}.

Dataset: {dataset_summary}

Responde SOLO con JSON valido.

Receta:
"""
        return self.model.generate(prompt, max_tokens=800)
