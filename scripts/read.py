from mztabm import MzTabMLoadResult, convert_to_dict, read


if __name__ == "__main__":
    file_path = "tests/data/example/example.mztab"
    result: MzTabMLoadResult = read(file_path)

    for message in result.messages:
        print(message.message_type.name, message.message)
    if not result.success:
        exit(1)
    mztabm_dict = convert_to_dict(result.mztabm)
    data = result.mztabm
