import argparse
import logging
import subprocess
import sys
from pathlib import Path

import orjson
from jsonprofile.validator.checkers.default_checker import OpaPolicyInput
from jsonprofile.validator.opa_engine import OpaEngine

from scripts.utils import setup_basic_logging_config

logger = logging.getLogger(__name__)

DEFAULT_WASM = Path("mztab_m_io/resources/mztabm-default-2.1.0-M.wasm")
DEFAULT_INPUT = Path("tests/data/example/example.json")


def build_policy_bundle(policy_root: Path, entrypoint: str, output_path: Path) -> None:
    subprocess.run(
        [
            "opa",
            "build",
            "-t",
            "wasm",
            "--ignore",
            "tests",
            "--ignore",
            "mztabm/policies/input.json",
            "-e",
            entrypoint,
            "-o",
            str(output_path),
            str(policy_root),
        ],
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an mzTab-M OPA policy.")
    parser.add_argument(
        "entrypoint",
        nargs="?",
        default="mztabm/policies",
        help="OPA entrypoint, e.g. mztabm/policies",
    )
    parser.add_argument("--wasm", type=Path, default=DEFAULT_WASM)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="JSON root document to pass as input.root.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    setup_basic_logging_config()
    args = parse_args()

    root = orjson.loads(args.input.read_text())
    input_data = OpaPolicyInput(
        policy_ids=["policy_d_0010", "policy_d_0020", "policy_d_0021", "policy_d_0022"],
        value=root,
        root=root,
    ).model_dump(by_alias=True)

    engine = OpaEngine(str(args.wasm))
    result = engine.evaluate(input_data=input_data, entrypoint=args.entrypoint)

    sys.stdout.write(
        orjson.dumps(
            result,
            option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS,
        ).decode()
    )

    sys.stdout.write("\n")
