# -*- coding: utf-8 -*-
"""
checkpoint.yml 동기화 통합 스크립트.

현재 역할:
1. models/checkpoints/<type> 기준으로 누락된 checkpoint 키 추가
2. checkpoint.yml 기존 항목의 기본 키/구조 보정
3. dry-run 지원

기존 add_missing_checkpoint.py 를 대체하는 통합 엔트리포인트 용도.
"""
import argparse
import os
import sys
from copy import deepcopy
from typing import Any, Dict, List, Tuple


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, YAMLHandler


DEFAULT_ENTRY = {
    "skip": False,
    "weight": 3,
    "favorites": 1,
    "steps": [30],
    "cfg": [4.0],
    "negative": {
        "checkpoint": "  ",
        "quality": " ,",
    },
    "positive": {
        "checkpoint": " ",
        "quality": " ",
        "anime": "",
    },
    "sampler_name": ["euler_ancestral"],
}


def configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def get_checkpoint_files(checkpoint_dir: str) -> List[str]:
    if not os.path.exists(checkpoint_dir):
        return []

    names: List[str] = []
    for filename in os.listdir(checkpoint_dir):
        if filename.endswith(".safetensors"):
            names.append(filename[:-len(".safetensors")])

    return sorted(names)


def ensure_mapping(parent: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        parent[key] = {}
    return parent[key]


def ensure_list(parent: Dict[str, Any], key: str, default: List[Any]) -> bool:
    value = parent.get(key)
    if isinstance(value, list) and value:
        return False
    parent[key] = list(default)
    return True


def ensure_scalar(parent: Dict[str, Any], key: str, default: Any) -> bool:
    if key in parent:
        return False
    parent[key] = default
    return True


def normalize_entry(entry: Dict[str, Any]) -> int:
    changes = 0

    changes += int(ensure_scalar(entry, "skip", DEFAULT_ENTRY["skip"]))
    changes += int(ensure_scalar(entry, "weight", DEFAULT_ENTRY["weight"]))
    changes += int(ensure_scalar(entry, "favorites", DEFAULT_ENTRY["favorites"]))
    changes += int(ensure_list(entry, "steps", DEFAULT_ENTRY["steps"]))
    changes += int(ensure_list(entry, "cfg", DEFAULT_ENTRY["cfg"]))
    changes += int(ensure_list(entry, "sampler_name", DEFAULT_ENTRY["sampler_name"]))

    negative = ensure_mapping(entry, "negative")
    changes += int(ensure_scalar(negative, "checkpoint", DEFAULT_ENTRY["negative"]["checkpoint"]))
    changes += int(ensure_scalar(negative, "quality", DEFAULT_ENTRY["negative"]["quality"]))

    positive = ensure_mapping(entry, "positive")
    changes += int(ensure_scalar(positive, "checkpoint", DEFAULT_ENTRY["positive"]["checkpoint"]))
    changes += int(ensure_scalar(positive, "quality", DEFAULT_ENTRY["positive"]["quality"]))
    changes += int(ensure_scalar(positive, "anime", DEFAULT_ENTRY["positive"]["anime"]))

    return changes


def build_new_entry() -> Dict[str, Any]:
    return deepcopy(DEFAULT_ENTRY)


def sync_type(
    type_name: str,
    comfui_dir: str,
    data_dir: str,
    yaml_handler: YAMLHandler,
    dry_run: bool = False,
) -> Tuple[int, int]:
    print(f"\n{'=' * 80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'=' * 80}")

    yml_path = os.path.join(data_dir, type_name, "checkpoint", "checkpoint.yml")
    checkpoint_dir = os.path.join(comfui_dir, "models", "checkpoints", type_name)

    if not os.path.exists(yml_path):
        print(f"  경고: checkpoint.yml 이 없습니다: {yml_path}")
        return 0, 0

    if not os.path.exists(checkpoint_dir):
        print(f"  경고: checkpoint 폴더가 없습니다: {checkpoint_dir}")
        return 0, 0

    yml_data = yaml_handler.load(yml_path)
    if yml_data is None:
        print("  오류: checkpoint.yml 로드 실패")
        return 0, 0

    checkpoint_files = get_checkpoint_files(checkpoint_dir)
    existing_keys = {key for key in yml_data.keys() if key}
    missing_keys = [key for key in checkpoint_files if key not in existing_keys]

    print(f"  checkpoint 파일: {len(checkpoint_files)}개")
    print(f"  yml 키: {len(existing_keys)}개")
    print(f"  누락 키: {len(missing_keys)}개")

    added_count = 0
    normalized_count = 0

    for key in missing_keys:
        if dry_run:
            print(f"    + 추가 예정: {key}")
        else:
            yml_data[key] = build_new_entry()
        added_count += 1

    for key, value in yml_data.items():
        if not isinstance(value, dict):
            continue

        changes = normalize_entry(value)
        if changes > 0:
            normalized_count += 1
            print(f"    * 구조 보정: {key}")

    if not dry_run and (added_count > 0 or normalized_count > 0):
        if yaml_handler.save(yml_path, yml_data):
            print(f"  [OK] 저장 완료: {yml_path}")
        else:
            print(f"  [ERROR] 저장 실패: {yml_path}")
            return added_count, normalized_count

    if added_count == 0 and normalized_count == 0:
        print("  [OK] 변경할 항목이 없습니다.")
    else:
        print(f"  추가 키: {added_count}개")
        print(f"  구조 보정: {normalized_count}개")
        if dry_run:
            print("  dry-run 이므로 저장하지 않았습니다.")

    return added_count, normalized_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="checkpoint.yml 누락 키 추가와 기본 구조 보정을 한 번에 수행합니다."
    )
    parser.add_argument(
        "--type",
        dest="type_names",
        action="append",
        help="처리할 타입명. 여러 번 지정 가능. 미지정 시 config.yml 의 types 전체 처리",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 저장 없이 변경 예정만 출력",
    )
    return parser.parse_args()


def main() -> int:
    configure_console_encoding()
    args = parse_args()
    config = ConfigLoader()
    yaml_handler = YAMLHandler(allow_duplicate_keys=True)

    comfui_dir = config.get_comfui_dir()
    data_dir = config.get_data_dir()
    type_names = args.type_names or config.get_types()

    print("=" * 80)
    print("checkpoint.yml 통합 동기화")
    print("=" * 80)
    print(f"처리 타입: {', '.join(type_names)}")
    if args.dry_run:
        print("모드: dry-run")

    total_added = 0
    total_normalized = 0

    for type_name in type_names:
        added_count, normalized_count = sync_type(
            type_name=type_name,
            comfui_dir=comfui_dir,
            data_dir=data_dir,
            yaml_handler=yaml_handler,
            dry_run=args.dry_run,
        )
        total_added += added_count
        total_normalized += normalized_count

    print(f"\n{'=' * 80}")
    print("완료")
    print(f"{'=' * 80}")
    print(f"추가 키: {total_added}개")
    print(f"구조 보정: {total_normalized}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
