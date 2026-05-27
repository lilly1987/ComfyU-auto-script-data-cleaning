# -*- coding: utf-8 -*-
"""Print char.yml entries with skip: auto and safetensors files >= 200 MB."""
import os
import sys
from typing import Any

import yaml


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader


MIN_SIZE_BYTES = 200 * 1024 * 1024


def configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def is_auto_skip(value: Any) -> bool:
    # return isinstance(value, str) and value.strip().lower() == "auto"
    return value in (False, None) or (isinstance(value, str) and value.strip().lower() == "auto")


def load_yml(yml_path: str) -> dict:
    with open(yml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def process_type(type_name: str, comfui_dir: str, data_dir: str) -> list:
    lora_dir = os.path.join(comfui_dir, "models", "loras", type_name, "char")
    yml_path = os.path.join(data_dir, type_name, "lora", "char.yml")

    if not os.path.exists(yml_path):
        print(f"warning: char.yml not found: {yml_path}", file=sys.stderr)
        return []

    yml_data = load_yml(yml_path)
    results = []
    for key in yml_data.keys():
        if not key:
            continue

        entry = yml_data.get(key)
        if not isinstance(entry, dict):
            continue

        if not is_auto_skip(entry.get("skip")):
            continue

        safetensors_path = os.path.join(lora_dir, f"{key}.safetensors")
        if not os.path.isfile(safetensors_path):
            continue

        size = os.path.getsize(safetensors_path)
        if size >= MIN_SIZE_BYTES:
            results.append((type_name, key, size))
    return results



def main() -> int:
    configure_console_encoding()

    config = ConfigLoader()
    comfui_dir = config.get_comfui_dir()
    data_dir = config.get_data_dir()

    all_results = []
    for type_name in config.get_types():
        all_results.extend(process_type(type_name, comfui_dir, data_dir))

    # 용량(size) 기준 내림차순 정렬
    # all_results.sort(key=lambda x: x[2], reverse=True)
    all_results.sort(key=lambda x: x[2])

    for type_name, key, size in all_results:
        print(f"{type_name}\t{key}\t({size / (1024 * 1024):.1f} MB)")

    print(f"total\t{len(all_results)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
