#!/usr/bin/env python3
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/"factoryos/core/session_secret.py"))["ensure_session_secret"]()
