
import json
import os
from jsonschema import validate, ValidationError

def load_config(path='config.v2.json', schema_path='config_schema.v2.json'):
    with open(schema_path, 'r', encoding='utf-8') as schema_file:
        schema = json.load(schema_file)
    with open(path, 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)

    try:
        validate(instance=config, schema=schema)
    except ValidationError as e:
        raise Exception(f"Erro de validação no config: {e.message}")
    
    return config
