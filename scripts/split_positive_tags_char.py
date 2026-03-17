# -*- coding: utf-8 -*-
"""
char.yml 의 positive.char 태그를 char / dress 로 자동 분리하는 스크립트.

- skip 이 false 인 항목만 처리
- positive.char 에서 excluded_tags 는 제거
- dress_tags 와 매칭되는 태그는 positive.dress 로 이동
- 나머지 태그는 positive.char 에 유지
- {a,b|c,d} 같은 선택 구조를 가능한 한 보존

config.yml 의 char.char_feature_tags 를 사용해 얼굴/머리/눈/귀/체형 같은
캐릭터 외형 태그를 더 명시적으로 char 쪽으로 분류할 수 있다.
분류 우선순위는 excluded > char_feature > dress > 기본 char 이다.
"""
import argparse
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, TagProcessor, YAMLHandler


DEFAULT_DRESS_SUFFIX = "8::__dress__"
AUTO_SKIP = "auto"


class GroupNode:
    def __init__(self, options: List[List[Any]]):
        self.options = options


def split_top_level(text: str, separator: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    depth = 0

    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)

        if ch == separator and depth == 0:
            parts.append("".join(current))
            current = []
            continue

        current.append(ch)

    parts.append("".join(current))
    return parts


def is_wrapped_group(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return False

    depth = 0
    for idx, ch in enumerate(stripped):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and idx != len(stripped) - 1:
                return False

    return depth == 0


def parse_items(text: str) -> List[Any]:
    items: List[Any] = []

    for raw_part in split_top_level(text, ","):
        part = raw_part.strip()
        if not part:
            continue

        if is_wrapped_group(part):
            inner = part.strip()[1:-1]
            options = [parse_items(option) for option in split_top_level(inner, "|")]
            items.append(GroupNode(options))
        else:
            items.append(part)

    return items


def render_items(items: List[Any]) -> str:
    rendered: List[str] = []

    for item in items:
        if isinstance(item, GroupNode):
            options = [render_items(option) for option in item.options]
            rendered.append("{" + "|".join(options) + "}")
        else:
            text = str(item).strip()
            if text:
                rendered.append(text)

    return ", ".join(rendered)


def dedupe_preserve_order(tags: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()

    for tag in tags:
        normalized = TagProcessor.normalize_tag(tag)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(tag.strip())

    return result


def merge_tag_lists(primary: List[str], secondary: List[str]) -> List[str]:
    return dedupe_preserve_order(primary + secondary)


def collect_flat_tags(items: List[Any]) -> List[str]:
    tags: List[str] = []

    for item in items:
        if isinstance(item, GroupNode):
            for option in item.options:
                tags.extend(collect_flat_tags(option))
        else:
            tags.append(str(item).strip())

    return tags


def classify_items(
    items: List[Any],
    excluded_tags: List[str],
    dress_tags: List[str],
    char_feature_tags: List[str],
) -> Tuple[List[Any], List[Any], List[str]]:
    char_items: List[Any] = []
    dress_items: List[Any] = []
    removed_tags: List[str] = []

    for item in items:
        if isinstance(item, GroupNode):
            char_options: List[List[Any]] = []
            dress_options: List[List[Any]] = []

            for option in item.options:
                option_char, option_dress, option_removed = classify_items(
                    option, excluded_tags, dress_tags, char_feature_tags
                )
                char_options.append(option_char)
                dress_options.append(option_dress)
                removed_tags.extend(option_removed)

            if any(option for option in char_options):
                char_items.append(GroupNode(char_options))
            if any(option for option in dress_options):
                dress_items.append(GroupNode(dress_options))
            continue

        tag = str(item).strip()
        if not tag:
            continue

        if TagProcessor.is_tag_excluded(tag, excluded_tags):
            removed_tags.append(tag)
            continue

        # 얼굴/머리/눈 같은 외형 태그는 dress 규칙보다 우선해서 char 에 남긴다.
        if char_feature_tags and TagProcessor.is_tag_excluded(tag, char_feature_tags):
            char_items.append(tag)
            continue

        if dress_tags and TagProcessor.is_tag_excluded(tag, dress_tags):
            dress_items.append(tag)
            continue

        char_items.append(tag)

    return char_items, dress_items, removed_tags


def extract_dress_structure_from_field(dress_value: str) -> str:
    if not dress_value or not isinstance(dress_value, str):
        return ""

    match = re.search(r"\{\s*\{([^}]+)\}\s*\|", dress_value)
    if match:
        return match.group(1).strip()

    match = re.search(r"\{([^|]+)\|", dress_value)
    if match:
        return match.group(1).strip()

    return ""


def extract_dress_suffix(dress_value: str) -> str:
    if not dress_value or not isinstance(dress_value, str):
        return DEFAULT_DRESS_SUFFIX

    match = re.search(r"\|([^{}]+::__dress__)", dress_value)
    if match:
        return match.group(1).strip().rstrip(",")

    return DEFAULT_DRESS_SUFFIX


def build_dress_field(structure: str, suffix: str) -> str:
    if structure:
        group_count = len([part for part in split_top_level(structure, "|") if part.strip()])
        if group_count > 1:
            rendered_structure = f"{{{structure}}}"
        else:
            rendered_structure = structure
        return f"{{  {rendered_structure}  |{suffix}}},"
    return f"{{   |{suffix}}},"


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y", "auto"}
    return bool(value)


def should_mark_auto_skip(value: Any) -> bool:
    if value is None:
        return True
    if value is False:
        return True
    if isinstance(value, int):
        return value == 0
    if isinstance(value, str):
        return value.strip().lower() in {"", "false", "0"}
    return False


def process_entry(
    entry: Dict[str, Any],
    excluded_tags: List[str],
    dress_tags: List[str],
    char_feature_tags: List[str],
) -> Optional[Dict[str, Any]]:
    positive = entry.get("positive")
    if not isinstance(positive, dict):
        return None

    char_value = positive.get("char")
    if not isinstance(char_value, str) or not char_value.strip():
        return None

    parsed = parse_items(char_value)
    new_char_items, new_dress_items, removed_tags = classify_items(
        parsed, excluded_tags, dress_tags, char_feature_tags
    )

    new_char_value = render_items(new_char_items)
    new_dress_structure = render_items(new_dress_items)

    existing_dress_value = positive.get("dress", "")
    existing_dress_structure = extract_dress_structure_from_field(existing_dress_value)
    dress_suffix = extract_dress_suffix(existing_dress_value)

    merged_dress_tags = merge_tag_lists(
        [tag for tag in split_top_level(existing_dress_structure, ",") if tag.strip()]
        if existing_dress_structure and "{" not in existing_dress_structure and "|" not in existing_dress_structure
        else [],
        [tag for tag in split_top_level(new_dress_structure, ",") if tag.strip()]
        if new_dress_structure and "{" not in new_dress_structure and "|" not in new_dress_structure
        else [],
    )

    if merged_dress_tags and not any(ch in (existing_dress_structure + new_dress_structure) for ch in "{}|"):
        merged_dress_structure = ", ".join(merged_dress_tags)
    elif existing_dress_structure and new_dress_structure:
        merged_dress_structure = f"{existing_dress_structure}|{new_dress_structure}"
    else:
        merged_dress_structure = new_dress_structure or existing_dress_structure

    updated_char = new_char_value if new_char_value else " , "
    updated_dress = build_dress_field(merged_dress_structure, dress_suffix)

    return {
        "char": updated_char,
        "dress": updated_dress,
        "removed_tags": dedupe_preserve_order(removed_tags),
        "moved_dress_tags": dedupe_preserve_order(collect_flat_tags(new_dress_items)),
        "changed": (
            positive.get("char") != updated_char
            or positive.get("dress") != updated_dress
        ),
    }


def process_char_yml(
    yml_path: str,
    excluded_tags: List[str],
    dress_tags: List[str],
    char_feature_tags: List[str],
    mark_auto_skip: bool = False,
    dry_run: bool = False,
) -> Tuple[int, int, List[str]]:
    yaml_handler = YAMLHandler(allow_duplicate_keys=True)
    yml_data = yaml_handler.load(yml_path)
    if yml_data is None:
        return 0, 0, []

    changed_entries = 0
    changed_keys: List[str] = []
    removed_summary: List[str] = []

    for key, value in yml_data.items():
        if not isinstance(value, dict):
            continue

        if normalize_bool(value.get("skip", False)):
            continue

        result = process_entry(value, excluded_tags, dress_tags, char_feature_tags)
        if not result or not result["changed"]:
            continue

        value["positive"]["char"] = result["char"]
        value["positive"]["dress"] = result["dress"]
        if mark_auto_skip and should_mark_auto_skip(value.get("skip")):
            value["skip"] = AUTO_SKIP

        changed_entries += 1
        changed_keys.append(str(key))
        removed_summary.extend(result["removed_tags"])

        print(f"    - {key}")
        if result["moved_dress_tags"]:
            print(f"      dress 이동: {', '.join(result['moved_dress_tags'])}")
        if result["removed_tags"]:
            print(f"      제외 제거: {', '.join(result['removed_tags'])}")

    if changed_entries > 0 and not dry_run:
        if yaml_handler.save(yml_path, yml_data):
            print(f"  [OK] 저장 완료: {yml_path}")
        else:
            print(f"  [ERROR] 저장 실패: {yml_path}")

    return changed_entries, len(dedupe_preserve_order(removed_summary)), changed_keys


def process_type(
    type_name: str,
    data_dir: str,
    excluded_tags: List[str],
    dress_tags: List[str],
    char_feature_tags: List[str],
    dry_run: bool = False,
) -> Tuple[int, List[str]]:
    print(f"\n{'=' * 80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'=' * 80}")

    yml_path = os.path.join(data_dir, type_name, "lora", "char.yml")
    if not os.path.exists(yml_path):
        print(f"  경고: 파일이 없습니다: {yml_path}")
        return 0, []

    changed_entries, removed_count, changed_keys = process_char_yml(
        yml_path=yml_path,
        excluded_tags=excluded_tags,
        dress_tags=dress_tags,
        char_feature_tags=char_feature_tags,
        dry_run=dry_run,
    )

    if changed_entries == 0:
        print("  [OK] 변경할 항목이 없습니다.")
    else:
        print(f"  변경 항목: {changed_entries}개")
        print(f"  제거된 제외 태그 종류: {removed_count}개")
        if dry_run:
            print("  dry-run 이므로 파일은 저장하지 않았습니다.")

    return changed_entries, changed_keys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="positive.char 태그를 char / dress 로 자동 분리합니다."
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
        help="파일을 저장하지 않고 변경 예정만 출력",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = ConfigLoader()

    data_dir = config.get_data_dir()
    type_names = args.type_names or config.get_types()
    excluded_tags = config.get_char_excluded_tags()
    dress_tags = config.get_char_dress_tags()
    char_feature_tags = config.get_char_feature_tags()

    print("=" * 80)
    print("positive.char -> char / dress 자동 분리")
    print("=" * 80)
    print(f"처리 타입: {', '.join(type_names)}")
    print(f"excluded_tags: {len(excluded_tags)}개")
    print(f"dress_tags: {len(dress_tags)}개")
    print(f"char_feature_tags: {len(char_feature_tags)}개 (선택 사전)")
    if args.dry_run:
        print("모드: dry-run")

    total_changed = 0
    all_changed_keys: List[str] = []

    for type_name in type_names:
        changed_count, changed_keys = process_type(
            type_name=type_name,
            data_dir=data_dir,
            excluded_tags=excluded_tags,
            dress_tags=dress_tags,
            char_feature_tags=char_feature_tags,
            dry_run=args.dry_run,
        )
        total_changed += changed_count
        all_changed_keys.extend(changed_keys)

    print(f"\n{'=' * 80}")
    print("완료")
    print(f"{'=' * 80}")
    print(f"총 변경 항목: {total_changed}개")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
