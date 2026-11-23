from __future__ import annotations

import os
import time
from datetime import datetime, timezone


def main() -> None:
    run_mode = os.getenv("RUN_MODE", "dryrun")
    dataset = os.getenv("DRYRUN_DATASET_PATH", "./tests/fixtures/dryrun")
    print(f"[worker] starting run_mode={run_mode} dataset={dataset}", flush=True)

    while True:
        print(
            f"[worker] heartbeat={datetime.now(timezone.utc).isoformat()} mode={run_mode}",
            flush=True,
        )
        time.sleep(20)


if __name__ == "__main__":
    main()
