# mzTab-M Python Implementation 

## Requirements

Python 3.12 and 3.12+

## Installation

```bash
# install python package manager uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# add $HOME/.local/bin to your PATH, either restart your shell or run
export PATH=$HOME/.local/bin:$PATH

# install git from https://git-scm.com/downloads
# Linux command
# apt update; apt install git -y

# Mac command
# brew install git

# clone project from github
git clone https://github.com/lifs-tools/pymzTab-m

git checkout development

# install python if it is not installed
uv python install 3.12

# install python dependencies
uv sync

# open your IDE (vscode, pycharm, etc.) and set python interpreter as .venv/bin/python

```

## Usage

```python
# These features are still experimental.

import mztab_m_io as mztabm

file_path = "tests/data/example/example.mztab"
result: mztabm.MzTabMLoadResult = mztabm.read(file_path)
for message in result.messages:
    print(message.message_type.name, message.message)
mztabm_model = result.mztabm

# You can use model object to get data in mzTab-M file
print("mzTab-M Id", result.mztabm.metadata.mztab_id)

# You can convert model to json and fetch values from dictionary
mztabm_dict = mztabm.convert_to_dict(result.mztabm)
print("mzTab-M Id",  mztabm_dict.get("mzTab-ID"))

# if you have a json version of mzTab-M, you can read it with format parameter.
file_path = "tests/data/example/example.json"
result: mztabm.MzTabMLoadResult = mztabm.read(file_path, format="json")

# you can also load from dictionary
with open(file_path) as f:
    mztabm_dict = json.load(f)
mztabm_model = mztabm.load_from_dict(mztabm_dict)

# You can write model object to mzTab-M file as tsv, json or yaml
temp_folder = Path(".temp/mztabm")
target_path = temp_folder / Path("example.mztab")
mztabm.write(result.mztabm, str(target_path), format="tsv")

# Following feature are not tested yet
target_path = temp_folder / Path("example.json")
mztabm.write(result.mztabm, str(target_path), format="json")
target_path = temp_folder / Path("example.yaml")
mztabm.write(result.mztabm, str(target_path), format="yaml")



```

## Authors

ozgury@ebi.ac.uk, nils.hoffmann@isas.de
