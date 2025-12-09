import json
from pathlib import Path
import shutil
import mztab_m_io


def test_read_01():
    """
    tsv file read
    """
    file_path = "tests/data/example/example.mztab"
    result: mztab_m_io.MzTabMLoadResult = mztab_m_io.read(file_path)
    for message in result.messages:
        print(message.message_type.name, message.message)

    assert result.success
    assert result.mztabm
    mztabm_dict = mztab_m_io.convert_to_dict(result.mztabm)
    assert mztabm_dict


def test_read_02():
    """
    json file read
    """
    file_path = "tests/data/example/example.json"

    result: mztab_m_io.MzTabMLoadResult = mztab_m_io.read(file_path, format="json")
    for message in result.messages:
        print(message.message_type.name, message.message)
    assert result.success
    assert result.mztabm
    mztabm_dict = mztab_m_io.convert_to_dict(result.mztabm)
    assert mztabm_dict


def test_read_03():
    """
    yaml file read
    """
    file_path = "tests/data/example/example.yaml"

    result: mztab_m_io.MzTabMLoadResult = mztab_m_io.read(file_path, format="yaml")
    for message in result.messages:
        print(message.message_type.name, message.message)
    assert result.success
    assert result.mztabm
    mztabm_dict = mztab_m_io.convert_to_dict(result.mztabm)
    assert mztabm_dict


def test_load_from_dict():
    """
    Load from dict
    """
    file_path = "tests/data/example/example.json"
    with open(file_path) as f:
        mztabm_dict = json.load(f)
    mztabm_model = mztab_m_io.load_from_dict(mztabm_dict)
    assert mztabm_model


def test_write_01():
    """
    write an mztab-M model to tsv file
    """
    file_path = "tests/data/example/example.mztab"

    result: mztab_m_io.MzTabMLoadResult = mztab_m_io.read(file_path)
    for message in result.messages:
        print(message.message_type.name, message.message)
    temp_folder = Path(".temp/mztabm")
    target_path = temp_folder / Path("example.mztab")
    try:
        mztab_m_io.write(result.mztabm, str(target_path), format="tsv")
    finally:
        shutil.rmtree(temp_folder)
        pass


def test_write_02():
    """
    write an mztab-M model to json file
    """
    file_path = "tests/data/example/example.json"

    result: mztab_m_io.MzTabMLoadResult = mztab_m_io.read(file_path, format="json")
    for message in result.messages:
        print(message.message_type.name, message.message)
    temp_folder = Path(".temp/mztabm")
    target_path = temp_folder / Path("example.json")
    try:
        mztab_m_io.write(result.mztabm, str(target_path), format="json")
        # assert target_path.read_text() == Path(file_path).read_text()
    finally:
        shutil.rmtree(temp_folder)
        pass


def test_write_03():
    """
    write an mztab-M model to yaml file
    """
    file_path = "tests/data/example/example.yaml"

    result: mztab_m_io.MzTabMLoadResult = mztab_m_io.read(file_path, format="yaml")
    for message in result.messages:
        print(message.message_type.name, message.message)
    temp_folder = Path(".temp/mztabm")
    target_path = temp_folder / Path("example.yaml")
    try:
        mztab_m_io.write(result.mztabm, str(target_path), format="yaml")
        # assert target_path.read_text() == Path(file_path).read_text()
    finally:
        # shutil.rmtree(temp_folder)
        pass
