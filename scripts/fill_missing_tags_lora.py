# -*- coding: utf-8 -*-
"""
lora.yml(또는 동일 구조의 XML/YML)에서 tag 배열이 비어있는 항목을
safetensors 메타데이터(ss_tag_frequency) 기반으로 자동 생성해 채워 넣는 스크립트
"""
import sys
import os
from typing import Dict, List, Tuple, Any

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import (  # noqa: E402
    ConfigLoader,
    YAMLHandler,
    SafeTensorsReader,
    TagProcessor,
)

# 설정 로드
config = ConfigLoader()
base_dir = config.get_base_dir()
types = config.get_types()

# YAML 핸들러 생성
yaml_handler = YAMLHandler(allow_duplicate_keys=True)

# 태그 추출 관련 설정
max_tags = config.get_max_tags('tag')
excluded_tags = config.get_excluded_tags('tag')

# safetensors가 위치한 기본 폴더(ComfyUI/models/loras/<type>/etc)
def get_safetensors_folder(type_name: str) -> str:
    return os.path.join(base_dir, 'ComfyUI', 'models', 'loras', type_name, 'etc')


def should_fill_tag(tag_value: Any) -> bool:
    """tag 필드가 비었는지 여부"""
    if tag_value is None:
        return True
    if isinstance(tag_value, list):
        return all((not isinstance(item, str)) or (not item.strip()) for item in tag_value)
    if isinstance(tag_value, str):
        return not tag_value.strip()
    return True


def build_tag_list_from_frequency(tag_frequency: Dict[str, Any]) -> List[str]:
    """ss_tag_frequency에서 추출한 문자열을 리스트로 정리"""
    tag_string = TagProcessor.process_tag_frequency(
        tag_frequency,
        max_tags=max_tags,
        excluded_tags=excluded_tags,
    )
    if not tag_string:
        return []

    tags: List[str] = []
    seen = set()
    for raw_tag in tag_string.split(','):
        tag = raw_tag.strip()
        if not tag:
            continue
        normalized = TagProcessor.normalize_tag(tag)
        if normalized in seen:
            continue
        seen.add(normalized)
        tags.append(tag)
    return tags


def get_tags_from_safetensors(key: str, key_to_file: Dict[str, str]) -> List[str]:
    """키에 해당하는 safetensors 메타데이터에서 태그 추출"""
    file_path = key_to_file.get(key)
    if not file_path:
        return []

    tag_frequency = SafeTensorsReader.extract_ss_tag_frequency(file_path)
    if not tag_frequency:
        return []

    return build_tag_list_from_frequency(tag_frequency)


def process_lora_file(yml_path: str, key_to_file: Dict[str, str]) -> Tuple[int, int]:
    """단일 lora.yml 파일 처리"""
    data = yaml_handler.load(yml_path)
    if not data or not isinstance(data, dict):
        print(f"  - {os.path.basename(yml_path)}: 로드 실패 또는 비어 있음")
        return 0, 0

    updated_keys = 0
    skipped_keys = 0

    for key, value in data.items():
        if not isinstance(value, dict):
            continue

        current_tag = value.get('tag')
        if not should_fill_tag(current_tag):
            continue

        new_tags = get_tags_from_safetensors(key, key_to_file)

        if not new_tags:
            skipped_keys += 1
            continue

        value['tag'] = new_tags
        updated_keys += 1
        print(f"    - {key}: safetensors에서 tag {len(new_tags)}개 추출")

    if updated_keys > 0:
        if yaml_handler.save(yml_path, data):
            print(f"  [OK] {os.path.basename(yml_path)} 저장 완료 "
                  f"(tag 채움 {updated_keys}개, tag 없음 {skipped_keys}개)")
        else:
            print(f"  [실패] {os.path.basename(yml_path)} 저장 실패")
    else:
        print(f"  - {os.path.basename(yml_path)}: 채울 tag 없음 {skipped_keys}개")

    return updated_keys, skipped_keys


def process_type(type_name: str):
    """타입별 lora 폴더 처리"""
    print(f"\n{'=' * 80}")
    print(f"[{type_name}] tag 자동 생성")
    print(f"{'=' * 80}")

    lora_dir = os.path.join(base_dir, 'ComfyU-auto-script_data', type_name, 'lora')
    if not os.path.isdir(lora_dir):
        print(f"  경고: 폴더를 찾을 수 없습니다: {lora_dir}")
        return

    safetensors_folder = get_safetensors_folder(type_name)
    tensor_keys, key_to_file = SafeTensorsReader.get_keys_from_folder(safetensors_folder)
    print(f"  safetensors 폴더: {safetensors_folder}")
    print(f"  safetensors 키 수: {len(tensor_keys)}")

    if not tensor_keys:
        print("  경고: safetensors 키를 찾지 못했습니다.")
        return

    target_files = [
        os.path.join(lora_dir, filename)
        for filename in os.listdir(lora_dir)
        if filename.lower().endswith(('.yml', '.yaml'))
    ]

    if not target_files:
        print("  처리할 YML/XML 파일이 없습니다.")
        return

    total_updated = 0
    total_skipped = 0

    for file_path in target_files:
        updated, skipped = process_lora_file(file_path, key_to_file)
        total_updated += updated
        total_skipped += skipped

    print(f"\n  결과 요약: tag 채움 {total_updated}개, positive 없음 {total_skipped}개")


if __name__ == "__main__":
    print("=" * 80)
    print("lora 사전에서 누락된 tag 자동 생성")
    print("=" * 80)

    for type_name in types:
        try:
            process_type(type_name)
        except Exception as exc:
            print(f"\n  [오류] {type_name} 처리 중 예외: {exc}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("모든 처리 완료")
    print(f"{'=' * 80}")


