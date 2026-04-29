from __future__ import annotations

from pathlib import Path

from ashare_similarity.config import _storage_home_from_local_script


def test_storage_home_from_local_script_matches_launch_scripts(tmp_path: Path):
    runtime_home = tmp_path / "runtime-home"
    (tmp_path / "ashare_similarity.local.ps1").write_text(
        f'$env:ASHARE_SIMILARITY_HOME = "{runtime_home}"\n',
        encoding="utf-8",
    )

    assert _storage_home_from_local_script(tmp_path) == runtime_home.resolve()

