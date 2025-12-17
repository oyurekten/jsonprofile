import json

from mztab_m_io.model.mztabm import MzTabM

if __name__ == "__main__":
    schema = MzTabM.model_json_schema(by_alias=True)
    with open("mztab_m_io/schema/mztabm.schema-2.1.0-M.json", "w") as f:
        json.dump(schema, f, indent=2)
