# -*- coding: utf-8 -*-
"""
Deprecated wrapper.

기존 add_missing_checkpoint.py 진입점을 유지하되,
실제 처리는 sync_checkpoint_yml.py 로 위임한다.
"""
import os
import sys


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from scripts.sync_checkpoint_yml import main


if __name__ == "__main__":
    raise SystemExit(main())
