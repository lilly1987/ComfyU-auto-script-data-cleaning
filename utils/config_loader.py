# -*- coding: utf-8 -*-
"""Configuration loader helpers."""
import os
from typing import Any, Dict, List, Optional

import yaml


class ConfigLoader:
    """Load and expose values from config.yml."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(script_dir, "config.yml")

        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            print(f"  warning: config file not found: {self.config_path}")
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            return self._config
        except Exception as e:
            print(f"  error: failed to read config file: {e}")
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_comfui_dir(self) -> str:
        return self.get("comfui_dir", r"W:\ComfyUI_windows_portable")

    def get_data_dir(self) -> str:
        return self.get("data_dir", r"W:\ComfyU-auto-script_data")

    def get_base_dir(self) -> str:
        return self.get("base_dir", r"W:\\")

    def get_types(self) -> List[str]:
        return self.get("types", ["IL", "Pony"])

    def _merge_unique_tags(self, *tag_lists: List[str]) -> List[str]:
        merged: List[str] = []
        seen = set()

        for tag_list in tag_lists:
            for tag in tag_list or []:
                normalized = str(tag).strip()
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                merged.append(tag)

        return merged

    def get_excluded_tags(self, section: str = "char") -> List[str]:
        if section == "char":
            return self.get_char_excluded_tags()
        if section == "lora":
            return self.get("lora", {}).get("excluded_tags", [])
        return []

    def get_dress_tags(self) -> List[str]:
        return self.get_char_dress_tags()

    def get_char_feature_tags(self) -> List[str]:
        char_config = self.get("char", {})
        return self._merge_unique_tags(
            char_config.get("hair_tags", []),
            char_config.get("face_tags", []),
            char_config.get("char_feature_tags", []),
        )

    def get_char_excluded_tags(self) -> List[str]:
        char_config = self.get("char", {})
        return self._merge_unique_tags(
            char_config.get("excluded_tags", []),
            char_config.get("body_tags", []),
            char_config.get("skin_tags", []),
        )

    def get_char_dress_tags(self) -> List[str]:
        char_config = self.get("char", {})
        return self._merge_unique_tags(
            char_config.get("dress_tags", []),
            char_config.get("accessory_tags", []),
        )

    def get_max_tags(self, section: str = "lora") -> int:
        if section == "lora":
            return self.get("lora", {}).get("max_tags", 64)
        return 64
