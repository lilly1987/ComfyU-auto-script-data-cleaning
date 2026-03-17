# -*- coding: utf-8 -*-
"""
Deprecated wrapper.

Keep the old add_missing_keys_char.py entrypoint working, but delegate the
actual processing to sync_char_yml.py.
"""
import os
import sys


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from scripts.sync_char_yml import main


if __name__ == "__main__":
    raise SystemExit(main())
