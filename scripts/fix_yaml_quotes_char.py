# -*- coding: utf-8 -*-
"""
char.yml 안의 작은따옴표 문자열을 YAML-safe 형태로 보정하는 전처리 스크립트.

- YAML 파싱 전에 텍스트로 직접 처리
- 기본 대상은 `char:` / `dress:` 라인
- 바깥쪽 문자열 구분용 작은따옴표는 유지
- 내부의 홀수 작은따옴표만 `''` 로 이스케이프

예:
  char: 'kiki (delico's nursery), blue eyes'
-> char: 'kiki (delico''s nursery), blue eyes'
"""
import argparse
import os
import sys
from typing import List, Tuple


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader


TARGET_KEYS = ("char:", "dress:")


def should_process_line(line: str) -> bool:
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return False
    return any(stripped.startswith(key) for key in TARGET_KEYS)


def split_single_quoted_value(line: str) -> Tuple[str, str, str]:
    first_quote = line.find("'")
    if first_quote == -1:
        return line, "", ""

    prefix = line[: first_quote + 1]
    body = line[first_quote + 1 :]

    last_quote = body.rfind("'")
    if last_quote == -1:
        return line, "", ""

    inner = body[:last_quote]
    suffix = body[last_quote:]
    return prefix, inner, suffix


def escape_inner_single_quotes(text: str) -> str:
    result: List[str] = []
    idx = 0

    while idx < len(text):
        ch = text[idx]
        if ch != "'":
            result.append(ch)
            idx += 1
            continue

        if idx + 1 < len(text) and text[idx + 1] == "'":
            result.append("''")
            idx += 2
            continue

        result.append("''")
        idx += 1

    return "".join(result)


def fix_line(line: str) -> Tuple[str, bool]:
    if not should_process_line(line):
        return line, False

    prefix, inner, suffix = split_single_quoted_value(line)
    if not inner and not suffix:
        return line, False

    escaped = escape_inner_single_quotes(inner)
    updated = prefix + escaped + suffix
    return updated, updated != line


def process_file(file_path: str, dry_run: bool = False) -> Tuple[int, List[int]]:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    changed_line_numbers: List[int] = []
    updated_lines: List[str] = []

    for idx, line in enumerate(lines, start=1):
        updated, changed = fix_line(line)
        updated_lines.append(updated)
        if changed:
            changed_line_numbers.append(idx)

    if changed_line_numbers and not dry_run:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(updated_lines)

    return len(changed_line_numbers), changed_line_numbers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="char.yml 안의 깨진 작은따옴표를 YAML-safe 형태로 보정합니다."
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
        help="파일을 저장하지 않고 수정 예정 줄만 출력",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = ConfigLoader()
    data_dir = config.get_data_dir()
    type_names = args.type_names or config.get_types()

    print("=" * 80)
    print("char.yml 작은따옴표 전처리")
    print("=" * 80)
    print(f"처리 타입: {', '.join(type_names)}")
    if args.dry_run:
        print("모드: dry-run")

    total_changed = 0

    for type_name in type_names:
        file_path = os.path.join(data_dir, type_name, "lora", "char.yml")
        print(f"\n[{type_name}] {file_path}")

        if not os.path.exists(file_path):
            print("  경고: 파일이 없습니다.")
            continue

        changed_count, line_numbers = process_file(file_path, dry_run=args.dry_run)
        total_changed += changed_count

        if changed_count == 0:
            print("  [OK] 수정할 줄이 없습니다.")
            continue

        print(f"  수정 줄 수: {changed_count}")
        print(f"  줄 번호: {', '.join(map(str, line_numbers[:30]))}")
        if len(line_numbers) > 30:
            print(f"  ... 외 {len(line_numbers) - 30}줄")
        if args.dry_run:
            print("  dry-run 이므로 저장하지 않았습니다.")
        else:
            print("  [OK] 저장 완료")

    print(f"\n총 수정 줄 수: {total_changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
