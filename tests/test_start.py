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
    result = subprocess.run(["bash", str(script), "--dry-run"], check=True, capture_output=True, text=True, cwd=ROOT)
    assert "http://127.0.0.1:8000/app" in result.stdout
    assert "create_app" in result.stdout


def test_start_py_respects_port() -> None:
    env = {**os.environ, "MANGEDONG_PORT": "8011"}
    result = subprocess.run(["python3", str(ROOT / "start.py"), "--dry-run"], check=True, capture_output=True, text=True, cwd=ROOT, env=env)
    assert "http://127.0.0.1:8011/app" in result.stdout


def test_windows_cmd_wrapper_is_crlf_and_delegates() -> None:
    raw = (ROOT / "start.cmd").read_bytes()
    assert b"start.py" in raw
    assert b"\r\n" in raw
    assert b"python start.py" in raw
    # CMD requires CRLF; LF-only files eat command letters on Windows.
    assert raw.count(b"\n") == raw.count(b"\r\n")


def test_cli_serve_help() -> None:
    result = subprocess.run(["python3", "-m", "mangedong.cli", "serve", "--help"], check=True, capture_output=True, text=True, cwd=ROOT)
    assert "workbench" in result.stdout.lower() or "工作台" in result.stdout
    assert "--port" in result.stdout
