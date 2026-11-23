from pathlib import Path

import yaml

from path_sync import sections
from path_sync._internal.models_dep import DepConfig

README_PATH = Path(__file__).parent.parent / "README.md"


def _first_code_block(heading: str) -> str:
    text = README_PATH.read_text(encoding="utf-8")
    after_heading = text.split(f"\n{heading}\n", 1)[1]
    block = after_heading.split("```", 2)[1]
    return block.split("\n", 1)[1]


def test_readme_section_marker_example_parses():
    example = _first_code_block("## Section Markers")
    assert sections.extract_sections(example, Path("justfile")) == {"default": "lint:\n    ruff check ."}


def test_readme_dep_config_example_enables_auto_merge():
    example = _first_code_block("### Dep Config Reference")
    config = DepConfig.model_validate(yaml.safe_load(example))
    assert config.auto_merge is not None
