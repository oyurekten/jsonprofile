from pathlib import Path

import orjson


def test_shared_conformance_manifest_loads() -> None:
    manifest_path = Path(__file__).parents[2] / "shared/conformance/smoke.json"
    manifest = orjson.loads(manifest_path.read_bytes())

    assert manifest["version"] == "0.1.0"
    assert {case["id"] for case in manifest["cases"]} == {
        "minimal-valid-profile",
        "missing-required-profile-name",
    }
