# -*- coding: utf-8 -*-
"""
char.yml 동기화 통합 스크립트.

1. safetensors 기준으로 누락 키 추가
2. skip != true 항목의 positive.char 정리
3. excluded_tags 제거
4. char / dress 자동 분리

기존 스크립트 역할:
- add_missing_keys_char.py
- remove_excluded_tags_char.py
- split_positive_tags_char.py
"""
import argparse
import os
import sys
from typing import List, Set, Tuple


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, SafeTensorsReader
from utils import TagProcessor
from scripts.split_positive_tags_char import process_char_yml


TEMPLATE = {
    "skip": False,
    "weight": 3,
    "positive": {
        "char": " ",
        "dress": "{   |8::__dress__},",
    },
}


def configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def load_existing_keys(yml_path: str) -> Set[str]:
    import yaml

    with open(yml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return {key for key in data.keys() if key}


def build_initial_values(
    file_path: str,
    excluded_tags: List[str],
    dress_tags: List[str],
    max_tags: int,
) -> Tuple[str, str, bool]:
    tag_frequency = SafeTensorsReader.extract_ss_tag_frequency(file_path)
    if not tag_frequency:
        return TEMPLATE["positive"]["char"].strip(), TEMPLATE["positive"]["dress"], False

    sorted_tags = TagProcessor.process_tag_frequency(
        tag_frequency,
        max_tags=max_tags,
        excluded_tags=excluded_tags,
        dress_tags=dress_tags,
    )

    dress_tag_list = TagProcessor.extract_dress_tags_from_tag_frequency(
        tag_frequency, dress_tags
    ) if dress_tags else []

    if sorted_tags:
        filtered_char, _ = TagProcessor.remove_excluded_tags_from_string(
            sorted_tags, excluded_tags=[], dress_tags=None
        )
        char_value = filtered_char if filtered_char and filtered_char.strip() else sorted_tags
    else:
        char_value = TEMPLATE["positive"]["char"].strip()

    if dress_tag_list:
        dress_value = f"{{  {', '.join(dress_tag_list)} |4::__dress__}},"
    else:
        dress_value = TEMPLATE["positive"]["dress"]

    return char_value, dress_value, True


def append_missing_entries(
    yml_path: str,
    missing_keys: List[str],
    key_to_file: dict,
    excluded_tags: List[str],
    dress_tags: List[str],
    max_tags: int,
    dry_run: bool = False,
) -> int:
    if not missing_keys:
        return 0

    if dry_run:
        for key in missing_keys:
            print(f"    + 추가 예정: {key}")
        return len(missing_keys)

    with open(yml_path, "a", encoding="utf-8") as f:
        for key in missing_keys:
            char_value, dress_value, _ = build_initial_values(
                key_to_file[key], excluded_tags, dress_tags, max_tags
            )
            char_value_escaped = char_value.replace("'", "''")
            dress_value_escaped = dress_value.replace("'", "''")

            f.write(f'"{key}": # auto\n')
            f.write(f'  weight: {TEMPLATE["weight"]}\n')
            f.write("  positive:\n")
            f.write(f"    char: '{char_value_escaped}'\n")
            f.write(f"    dress: '{dress_value_escaped}'\n")
            f.write(f"  skip: {str(TEMPLATE['skip']).lower()}\n")
            f.write("\n")

    return len(missing_keys)


def sync_type(
    type_name: str,
    comfui_dir: str,
    data_dir: str,
    excluded_tags: List[str],
    dress_tags: List[str],
    char_feature_tags: List[str],
    max_tags: int,
    dry_run: bool = False,
) -> Tuple[int, int]:
    print(f"\n{'=' * 80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'=' * 80}")

    folder_path = os.path.join(comfui_dir, "models", "loras", type_name, "char")
    yml_path = os.path.join(data_dir, type_name, "lora", "char.yml")

    if not os.path.exists(folder_path):
        print(f"  경고: char 폴더가 없습니다: {folder_path}")
        return 0, 0

    if not os.path.exists(yml_path):
        print(f"  경고: char.yml 이 없습니다: {yml_path}")
        return 0, 0

    try:
        existing_keys = load_existing_keys(yml_path)
    except Exception as e:
        print(f"  오류: char.yml 읽기 실패: {e}")
        print("  힌트: 먼저 _fix_yaml_quotes.cmd 를 실행해 주세요.")
        return 0, 0

    safetensors_keys, key_to_file = SafeTensorsReader.get_keys_from_folder(folder_path)
    missing_keys = sorted(safetensors_keys - existing_keys)

    print(f"  safetensors 키: {len(safetensors_keys)}개")
    print(f"  yml 키: {len(existing_keys)}개")
    print(f"  누락 키: {len(missing_keys)}개")

    added_count = append_missing_entries(
        yml_path=yml_path,
        missing_keys=missing_keys,
        key_to_file=key_to_file,
        excluded_tags=excluded_tags,
        dress_tags=dress_tags,
        max_tags=max_tags,
        dry_run=dry_run,
    )

    if added_count and not dry_run:
        print(f"  추가 완료: {added_count}개")
    elif added_count and dry_run:
        print(f"  추가 예정: {added_count}개")

    changed_entries, _, _ = process_char_yml(
        yml_path=yml_path,
        excluded_tags=excluded_tags,
        dress_tags=dress_tags,
        char_feature_tags=char_feature_tags,
        dry_run=dry_run,
    )

    if changed_entries == 0:
        print("  [OK] 후처리 변경 없음")
    else:
        print(f"  후처리 변경: {changed_entries}개")

    return added_count, changed_entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="char.yml 누락 키 추가 + 태그 정리를 한 번에 수행합니다."
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

    comfui_dir = config.get_comfui_dir()
    data_dir = config.get_data_dir()
    type_names = args.type_names or config.get_types()
    excluded_tags = config.get_excluded_tags("char")
    dress_tags = config.get_dress_tags()
    char_feature_tags = config.get("char", {}).get("char_feature_tags", [])
    max_tags = config.get_max_tags("lora")

    print("=" * 80)
    print("char.yml 통합 동기화")
    print("=" * 80)
    print(f"처리 타입: {', '.join(type_names)}")
    print(f"excluded_tags: {len(excluded_tags)}개")
    print(f"dress_tags: {len(dress_tags)}개")
    print(f"char_feature_tags: {len(char_feature_tags)}개")
    if args.dry_run:
        print("모드: dry-run")

    total_added = 0
    total_changed = 0

    for type_name in type_names:
        added_count, changed_count = sync_type(
            type_name=type_name,
            comfui_dir=comfui_dir,
            data_dir=data_dir,
            excluded_tags=excluded_tags,
            dress_tags=dress_tags,
            char_feature_tags=char_feature_tags,
            max_tags=max_tags,
            dry_run=args.dry_run,
        )
        total_added += added_count
        total_changed += changed_count

    print(f"\n{'=' * 80}")
    print("완료")
    print(f"{'=' * 80}")
    print(f"추가 키: {total_added}개")
    print(f"후처리 변경: {total_changed}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
