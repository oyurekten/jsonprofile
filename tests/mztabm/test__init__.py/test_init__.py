from mztabm import MzTabMLoadResult, convert_to_dict, read


def test_read_01():
    file_path = "tests/data/example/example.mztab"
    result: MzTabMLoadResult = read(file_path)
    for message in result.messages:
        print(message.message_type.name, message.message)
    assert result.success
    assert result.mztabm


def test_convert_to_dict_01():
    file_path = "tests/data/example/example.mztab"
    result: MzTabMLoadResult = read(file_path)
    mztabm_dict = convert_to_dict(result.mztabm)
    assert mztabm_dict
    assert mztabm_dict.get("metadata")
