from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

from godml.advisor_service.schemas import RecipeSchema

_DEFAULT_MODEL_PATH = os.environ.get(
    "GODML_GPT4ALL_PATH",
    str(Path.home() / ".gpt4all" / "models"),
)
_DEFAULT_MODEL_NAME = os.environ.get(
    "GODML_GPT4ALL_MODEL",
    "q4_0-orca-mini-3b.gguf",
)
_DEFAULT_EXAMPLES_PATH = os.environ.get(
    "GODML_RECIPES_PATH",
    str(Path.home() / ".godml" / "recipes_examples.json"),
)


class RAGAdvisor:
    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL_NAME,
        model_path: str = _DEFAULT_MODEL_PATH,
        examples_path: str = _DEFAULT_EXAMPLES_PATH,
    ):
        try:
            from gpt4all import GPT4All
        except ImportError as e:
            raise ImportError(
                "El advisor RAG requiere gpt4all. "
                "Instala con: pip install godml[advisor]"
            ) from e

        self.model = GPT4All(model_name, model_path=model_path)
        self.examples = self._load_examples(examples_path)

    def _load_examples(self, examples_path: str) -> list:
        try:
            with open(examples_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception:
            return []

    def retrieve_examples(self, dataset_summary: str, top_k: int = 2) -> list:
        if not self.examples:
            return []
        scored = [
            (e, SequenceMatcher(None, dataset_summary, e.get("summary", "")).ratio())
            for e in self.examples
        ]
        return [s[0] for s in sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]]

    def _extract_first_json(self, raw_output: str) -> str:
        start = raw_output.find("{")
        if start == -1:
            raise ValueError("No se encontro '{' en salida del LLM")

        depth = 0
        end = start
        for i, ch in enumerate(raw_output[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        else:
            raise ValueError("JSON no cerrado en salida del LLM")

        candidate = raw_output[start : end + 1]
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        return candidate

    def suggest_recipe(self, dataset_summary: str) -> dict:
        examples = self.retrieve_examples(dataset_summary, top_k=2)
        examples_text = "\n\n".join([
            f"Ejemplo:\nDataset: {e['summary']}\nReceta:\n{json.dumps(e['recipe'], indent=2)}"
            for e in examples
        ])

        examples_section = ("Ejemplos:\n" + examples_text) if examples_text else ""
        prompt = f"""
Eres un experto en ciencia de datos y GODML.
Genera una receta de DataPrep en formato JSON para usar en un notebook.

Reglas:
- SOLO devuelve JSON valido con inputs, steps y outputs.
- No devuelvas explicaciones ni comentarios.

{examples_section}

Ahora genera la receta para:
Dataset: {dataset_summary}
Receta:
"""
        raw_output = self.model.generate(prompt, max_tokens=800)

        try:
            cleaned = self._extract_first_json(raw_output)
            recipe_dict = json.loads(cleaned)
            validated = RecipeSchema(**recipe_dict)
            return validated.model_dump()
        except Exception:
            return self.fallback_recipe()

    def fallback_recipe(self) -> dict:
        return {
            "inputs": [{"name": "raw", "connector": "csv", "uri": "inp"}],
            "steps": [{"op": "drop_duplicates", "params": {}}],
            "outputs": [{"name": "clean", "connector": "csv", "uri": "out"}],
        }
