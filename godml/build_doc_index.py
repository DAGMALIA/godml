import ast
import os
import json
import re

DOC_INDEX = []

def extract_examples(doc: str):
    if not doc:
        return []
    examples = []
    for match in re.findall(r"(>>>[^\n]+(?:\n\.\.\.[^\n]+)*)", doc):
        examples.append(match.strip())
    for match in re.findall(r"Ejemplo:(.*?)(?:\n\n|\Z)", doc, re.S):
        examples.append(match.strip())
    for match in re.findall(r"```(?:python)?\n(.*?)```", doc, re.S):
        examples.append(match.strip())
    return examples

def parse_file(path):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
        tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node) or "No docstring disponible."
            DOC_INDEX.append({
                "name": node.name,
                "path": path,
                "signature": f"{node.name}(...)",
                "doc": doc.split("\n")[0],
                "examples": extract_examples(doc)
            })

def build_index(out_file="godml_doc_index.json"):
    base_dir = os.path.dirname(__file__)
    files = ["godml_cli.py", "notebook_api.py"]
    for file in files:
        parse_file(os.path.join(base_dir, file))
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(DOC_INDEX, f, indent=2, ensure_ascii=False)
    print(f"✅ Índice generado con {len(DOC_INDEX)} funciones → {out_file}")

if __name__ == "__main__":
    build_index()
