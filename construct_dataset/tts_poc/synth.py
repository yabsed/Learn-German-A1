#!/usr/bin/env python3
"""호환용 진입점. 새 즉석 합성 CLI는 tools/say.py에 있다."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from say import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
