from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_start_script_is_executable_and_dry_run() -> None:
    script = ROOT / "start.sh"
    assert script.is_file()
    mode = script.stat().st_mode
    assert mode & stat.S_IXUSR
    text = script.read_text(encoding="utf-8")
    assert "mangedong.api.app:create_app" in text
    assert "--factory" in text
    result = subprocess.run(["bash", str(script), "--dry-run"], check=True, capture_output=True, text=True, cwd=ROOT)
    assert "http://127.0.0.1:8000/app" in result.stdout
    assert "create_app" in result.stdout


def test_start_script_respects_port_and_env_file(tmp_path: Path) -> None:
    script = ROOT / "start.sh"
    env = {**os.environ, "MANGEDONG_PORT": "8011"}
    result = subprocess.run(["bash", str(script), "--dry-run"], check=True, capture_output=True, text=True, cwd=ROOT, env=env)
    assert "http://127.0.0.1:8011/app" in result.stdout


def test_cli_serve_help() -> None:
    result = subprocess.run(["python3", "-m", "mangedong.cli", "serve", "--help"], check=True, capture_output=True, text=True, cwd=ROOT)
    assert "workbench" in result.stdout.lower() or "工作台" in result.stdout
    assert "--port" in result.stdout
