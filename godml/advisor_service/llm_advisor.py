from gpt4all import GPT4All

class LLMAdvisor:
    def __init__(self, model_name="q4_0-orca-mini-3b.gguf",
                model_path="C:/Users/arturo/.gpt4all/models"):
        self.model = GPT4All(model_name, model_path=model_path)

    def suggest_recipe(self, dataset_summary: str, language: str = "es"):
        prompt = f"""
    Eres un experto en ciencia de datos y en GODML.

    Eres un asistente experto en DataPrep con GODML.
    Genera SIEMPRE un JSON válido con comillas dobles.

    REGLAS:
    - Si hay más de 10% de nulos en una columna, aplica "fillna" (numéricas: media/mediana, categóricas: moda).
    - Si una columna tiene >90% nulos, sugiere descartarla.
    - Codifica siempre variables categóricas con "one_hot".
    - Incluye "drop_duplicates".
    - Si hay una columna de fecha, sugiere "extract_date_parts".
    - Si hay un target binario, no lo toques en one_hot.
    - Si no hay target, NO inventes uno.
    
    Responde siempre en {language}.

    Ejemplo:
    Dataset: Titanic (891 filas, target binario, variables categóricas y numéricas, con nulos)
    Receta:
    {{
        "inputs": [{{"name": "raw", "connector": "csv", "uri": inp}}],
        "steps": [
            {{"op": "select", "params": {{"columns": ["Survived","Pclass","Sex","Age","SibSp","Parch","Fare","Embarked"]}}}},
            {{"op": "safe_cast", "params": {{"mapping": {{"Age": "float", "Fare": "float","Pclass": "int","SibSp": "int","Parch": "int"}}}}}},
            {{"op": "fillna", "params": {{"columns": {{"Age": 28.0, "Embarked": "S"}}}}}},
            {{"op": "fillna", "params": {{"columns": {{"Fare": 14.45}}}}}},
            {{"op": "one_hot", "params": {{"columns": ["Sex","Embarked"], "drop_first": true}}}},
            {{"op": "rename", "params": {{"mapping": {{"Survived": "survived"}}}}}},
            {{"op": "safe_cast", "params": {{"mapping": {{"survived": "int"}}}}}},
            {{"op": "drop_duplicates", "params": {{}}}}
        ],
        "outputs": [{{"name": "clean", "connector": "csv", "uri": out}}]
    }}

    Ahora genera una receta similar para:
    Dataset: {dataset_summary}

    Responde SOLO con JSON válido.
    
    Receta:
    """
        return self.model.generate(prompt, max_tokens=800)

