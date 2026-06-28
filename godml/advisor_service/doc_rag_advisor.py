from __future__ import annotations

import json
import os
from difflib import SequenceMatcher
from pathlib import Path

_DEFAULT_MODEL_PATH = os.environ.get(
    "GODML_GPT4ALL_PATH",
    str(Path.home() / ".gpt4all" / "models"),
)
_DEFAULT_MODEL_NAME = os.environ.get(
    "GODML_DOC_MODEL",
    "mistral-7b-instruct-v0.2-code-ft.Q4_0.gguf",
)
_DEFAULT_INDEX_PATH = os.environ.get(
    "GODML_DOC_INDEX_PATH",
    str(Path.home() / ".godml" / "godml_doc_index.json"),
)

_UNAVAILABLE_MSG = (
    "El advisor de documentacion no esta disponible.\n"
    "Para habilitarlo:\n"
    "  1. Instala: pip install godml[advisor]\n"
    "  2. Genera el indice: godml build-advisor-index\n"
    "  3. O define GODML_DOC_INDEX_PATH con la ruta al indice JSON."
)


class DocRAGAdvisor:
    def __init__(
        self,
        model_name: str = _DEFAULT_MODEL_NAME,
        model_path: str = _DEFAULT_MODEL_PATH,
        doc_index_path: str = _DEFAULT_INDEX_PATH,
    ):
        try:
            from gpt4all import GPT4All
        except ImportError as e:
            raise ImportError(
                "El advisor de documentacion requiere gpt4all. "
                "Instala con: pip install godml[advisor]"
            ) from e

        self.model = GPT4All(model_name, model_path=model_path)
        self.docs = self._load_index(doc_index_path)

    def _load_index(self, path: str) -> list:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception:
            return []

    def retrieve_docs(self, question: str, top_k: int = 1) -> list:
        if not self.docs:
            return []

        def score_entry(d: dict) -> float:
            text = " ".join([
                d.get("name", ""),
                d.get("signature", ""),
                d.get("doc", ""),
                " ".join(d.get("tags", [])),
                " ".join(d.get("examples", [])),
            ])
            return SequenceMatcher(None, question.lower(), text.lower()).ratio()

        scored = [(d, score_entry(d)) for d in self.docs]
        return [s[0] for s in sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]]

    def ask(self, question: str) -> str:
        if not self.docs:
            return _UNAVAILABLE_MSG

        q = question.lower()

        for d in self.docs:
            if d.get("name", "").lower() in q:
                example = d["examples"][0] if d.get("examples") else "No hay ejemplo disponible."
                return (
                    f"Funcion: {d['name']}\n"
                    f"Firma: {d['signature']}\n"
                    f"Docstring: {d['doc']}\n"
                    f"Ejemplo:\n{example}"
                )

        docs = self.retrieve_docs(question, top_k=1)
        context = []
        for d in docs:
            block = f"Funcion: {d['name']}\nFirma: {d['signature']}\nDocstring: {d['doc']}"
            if d.get("examples"):
                block += "\n" + "\n".join([f"Ejemplo:\n{ex}" for ex in d["examples"]])
            context.append(block)

        prompt = f"""
Eres un asistente experto en GODML.
Responde en espanol usando SOLO el contexto disponible.
Si hay ejemplos, incluyelos.

Pregunta: {question}

Contexto:
{chr(10).join(context)}

Respuesta:
"""
        return self.model.generate(prompt, max_tokens=400)
