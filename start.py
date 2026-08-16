#!/usr/bin/env python3
"""Cross-platform one-click launcher for the mangedong workbench."""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            os.environ.setdefault(key, value)


def venv_python() -> Path:
    if os.name == "nt":
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def ensure_python() -> Path:
    if os.environ.get("MANGEDONG_NO_VENV") == "1":
        return Path(sys.executable)
    python = venv_python()
    if not python.exists():
        print(f"creating virtualenv at {ROOT / '.venv'}", flush=True)
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    return python


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    os.chdir(ROOT)
    load_dotenv(ROOT / ".env")
    host = os.environ.get("MANGEDONG_HOST", "0.0.0.0")
    port = os.environ.get("MANGEDONG_PORT", "8000")

    if "--help" in argv or "-h" in argv:
        print(
            "Usage: python start.py [--dry-run]\n"
            "Starts the mangedong Web workbench at http://127.0.0.1:<port>/app\n"
            "Windows: double-click start.cmd  |  macOS/Linux: ./start.sh"
        )
        return 0

    if "--dry-run" in argv:
        print(f"mangedong workbench http://127.0.0.1:{port}/app")
        print(f"health http://127.0.0.1:{port}/health")
        print(f"uvicorn mangedong.api.app:create_app --factory --host {host} --port {port}")
        return 0

    python = ensure_python()
    if os.environ.get("MANGEDONG_SKIP_INSTALL") != "1":
        print("installing mangedong into the virtualenv", flush=True)
        subprocess.check_call([str(python), "-m", "pip", "install", "-q", "-e", str(ROOT)])

    os.environ.setdefault("MANGEDONG_DATABASE_URL", "sqlite:///./mangedong.db")
    os.environ.setdefault("MANGEDONG_STORAGE_DIR", "./mangedong_storage")
    os.environ.setdefault("MANGEDONG_SECRET_KEY", "dev-secret-change-me")

    print(f"mangedong 工作台: http://127.0.0.1:{port}/app", flush=True)
    print(f"健康检查:         http://127.0.0.1:{port}/health", flush=True)
    print("Ctrl+C 停止。", flush=True)
    return subprocess.call(
        [
            str(python),
            "-m",
            "uvicorn",
            "mangedong.api.app:create_app",
            "--factory",
            "--host",
            host,
            "--port",
            str(port),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
