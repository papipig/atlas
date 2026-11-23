from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone


def run_dryrun_once() -> int:
    env = os.environ.copy()
    env.setdefault("RUN_MODE", "dryrun")
    env.setdefault("ALLOW_OUTBOUND_NETWORK", "false")
    result = subprocess.run(
        ["python3", "scripts/dryrun_runner.py"],
        env=env,
        check=False,
    )
    return result.returncode


def main() -> None:
    run_mode = os.getenv("RUN_MODE", "dryrun")
    interval = int(os.getenv("SCHEDULER_LOOP_SEC", "60"))
    print(f"[scheduler] starting run_mode={run_mode} interval={interval}s", flush=True)

    while True:
        print(f"[scheduler] tick={datetime.now(timezone.utc).isoformat()}", flush=True)
        if run_mode == "dryrun":
            code = run_dryrun_once()
            print(f"[scheduler] dryrun_runner exit_code={code}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
