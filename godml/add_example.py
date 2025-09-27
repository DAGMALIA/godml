import json

EXAMPLES_PATH = "recipes_examples.json"

def add_example(summary: str, recipe: dict):
    with open(EXAMPLES_PATH, "r", encoding="utf-8") as f:
        examples = json.load(f)
    examples.append({"summary": summary, "recipe": recipe})
    with open(EXAMPLES_PATH, "w", encoding="utf-8") as f:
        json.dump(examples, f, indent=2, ensure_ascii=False)
    print(f"✅ Ejemplo agregado: {summary}")

if __name__ == "__main__":
    recipe = {
        "inputs": [{"name": "raw", "connector": "csv", "uri": "inp"}],
        "steps": [{"op": "drop_duplicates", "params": {}}],
        "outputs": [{"name": "clean", "connector": "csv", "uri": "out"}]
    }
    add_example("Dataset simple con duplicados", recipe)
