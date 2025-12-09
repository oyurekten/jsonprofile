import json
from mztab_m_io import MzTabMLoadResult, convert_to_dict, read
from mztab_m_io.model.mztabm import MzTabM


if __name__ == "__main__":
    schema = MzTabM.model_json_schema(by_alias=True)
    with open("mztabm.schema.json", "w") as f:
        json.dump(schema, f, indent=2)
    file_path = "tests/data/example/example.mztab"
    result: MzTabMLoadResult = read(file_path)

    for message in result.messages:
        print(message.message_type.name, message.message)
    if not result.success:
        exit(1)
    mztabm_dict = convert_to_dict(result.mztabm)
    data = result.mztabm
