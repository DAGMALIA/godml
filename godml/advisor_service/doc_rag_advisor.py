# godml/advisor_service/doc_rag_advisor.py

import json
from difflib import SequenceMatcher
from gpt4all import GPT4All


class DocRAGAdvisor:
    def __init__(self,
                 model_name="mistral-7b-instruct-v0.2-code-ft.Q4_0.gguf",
                 model_path="C:/Users/arturo/.gpt4all/models",
                 doc_index_path="godml_doc_index.json"):
        # Inicializa modelo y carga índice
        self.model = GPT4All(model_name, model_path=model_path)
        with open(doc_index_path, "r", encoding="utf-8") as f:
            self.docs = json.load(f)

    def retrieve_docs(self, question, top_k=1):
        """Búsqueda difusa en name, doc, tags y ejemplos."""
        def score_entry(d):
            text = " ".join([
                d.get("name", ""),
                d.get("signature", ""),
                d.get("doc", ""),
                " ".join(d.get("tags", [])),
                " ".join(d.get("examples", []))
            ])
            return SequenceMatcher(None, question.lower(), text.lower()).ratio()

        scored = [(d, score_entry(d)) for d in self.docs]
        return [s[0] for s in sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]]

    def ask(self, question: str):
        q = question.lower()

        # 🔹 Fast-path: coincidencia exacta con nombre
        for d in self.docs:
            if d["name"].lower() in q:
                return f"""
📌 Función: {d['name']}
🔹 Firma: {d['signature']}
📝 Docstring: {d['doc']}
📊 Ejemplo:
{d['examples'][0] if d.get("examples") else "No hay ejemplo disponible."}
"""

        # 🔹 Fallback: usar RAG + LLM
        docs = self.retrieve_docs(question, top_k=1)
        context = []
        for d in docs:
            block = f"Función: {d['name']}\nFirma: {d['signature']}\nDocstring: {d['doc']}"
            if d.get("examples"):
                examples_text = "\n".join([f"Ejemplo:\n{ex}" for ex in d["examples"]])
                block += f"\n{examples_text}"
            context.append(block)

        prompt = f"""
Eres un asistente experto en GODML.
Responde en español usando SOLO el contexto disponible.
Si hay ejemplos, inclúyelos.

Pregunta: {question}

Contexto:
{chr(10).join(context)}

Respuesta:
"""
        return self.model.generate(prompt, max_tokens=400)

