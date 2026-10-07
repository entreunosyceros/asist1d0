#!/usr/bin/env python3
"""Lanza la API REST y el portal web de Asist{1d0}."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.app import main  # noqa: E402

if __name__ == "__main__":
    main()
