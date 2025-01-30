from importlib.resources import files
import json


observatories_schema=json.loads(files('tofo.schema').joinpath('observatory.json').read_text())
