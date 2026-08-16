from __future__ import annotations

import os
import threading
from pathlib import Path

from mangedong.api.db import build_session_factory, init_db
from mangedong.api.worker import run_worker_forever, worker_id


def main() -> None:
    database_url = os.getenv("MANGEDONG_DATABASE_URL", "sqlite:///./mangedong.db")
    storage_dir = Path(os.getenv("MANGEDONG_STORAGE_DIR", "./mangedong_storage")).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)
    session_factory = build_session_factory(database_url)
    init_db(session_factory)
    stop = threading.Event()
    print(f"mangedong worker {worker_id()} queue=database db={database_url}")
    try:
        run_worker_forever(session_factory, storage_dir, stop)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    main()
