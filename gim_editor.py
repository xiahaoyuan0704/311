"""Backward-compatible entrypoint.

Prefer: `python3 -m gim_desktop` or `./run_desktop.sh`.
"""

from gim_desktop.app import run

if __name__ == "__main__":
    run()
