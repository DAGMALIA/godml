import ast
import os
import json
import re
from pathlib import Path

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

def build_index(out_file=None):
    base_dir = os.path.dirname(__file__)
    out_file = out_file or str(Path.home() / ".godml" / "godml_doc_index.json")

    files = [os.path.join(base_dir, "godml_cli.py")]
    notebook_api_dir = os.path.join(base_dir, "notebook_api")
    for name in sorted(os.listdir(notebook_api_dir)):
        if name.endswith(".py"):
            files.append(os.path.join(notebook_api_dir, name))

    for file in files:
        parse_file(file)

    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(DOC_INDEX, f, indent=2, ensure_ascii=False)
    print(f"Indice generado con {len(DOC_INDEX)} funciones en {out_path}")

if __name__ == "__main__":
    build_index()
