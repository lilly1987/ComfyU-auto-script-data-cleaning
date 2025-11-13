# -*- coding: utf-8 -*-
"""
char.yml 파일의 'char' 필드에서 제외 태그를 제거하는 스크립트
"""
import sys
import os
import re

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, TagProcessor, YAMLHandler

# 설정 로드
config = ConfigLoader()
base_dir = config.get_base_dir()
types = config.get_types()
excluded_tags = config.get_excluded_tags('char')
dress_tags = config.get_dress_tags()

# YAML 핸들러 생성
yaml_handler = YAMLHandler(allow_duplicate_keys=True)

def extract_tags_from_dress_field(dress_value: str) -> list:
    """dress 필드 값에서 태그를 추출합니다."""
    if not dress_value or not isinstance(dress_value, str):
        return []
    
    match = re.search(r'\{([^|]+)\|', dress_value)
    if match:
        tags_str = match.group(1).strip()
        if tags_str:
            return [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    return []

def merge_dress_tags(existing_tags: list, new_tags: list) -> list:
    """기존 dress 태그와 새로운 dress 태그를 병합합니다."""
    merged_tags = []
    seen_normalized = set()
    
    for tag in existing_tags:
        if not tag:
            continue
        normalized = TagProcessor.normalize_tag(tag)
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            merged_tags.append(tag)
    
    for tag in new_tags:
        if not tag:
            continue
        normalized = TagProcessor.normalize_tag(tag)
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            merged_tags.append(tag)
    
    return merged_tags

def process_char_yml(yml_path: str, excluded_tags: list, dress_tags: list):
    """char.yml 파일을 처리합니다."""
    yml_data = yaml_handler.load(yml_path)
    if yml_data is None:
        return None, 0, 0, 0
    
    modified_count = 0
    total_removed_tags = 0
    modified_dress_count = 0
    
    for key, value in yml_data.items():
        if not isinstance(value, dict):
            continue
        
        if 'positive' in value and isinstance(value['positive'], dict):
            positive_dict = value['positive']
            
            if 'char' in positive_dict:
                char_value = positive_dict['char']
                
                if isinstance(char_value, str):
                    # dress 태그 추출
                    dress_tag_list = TagProcessor.extract_dress_tags_from_string(
                        char_value, dress_tags
                    ) if dress_tags else []
                    
                    # 제외 태그 및 dress 태그 제거
                    filtered_char, removed_count = TagProcessor.remove_excluded_tags_from_string(
                        char_value, excluded_tags, dress_tags
                    )
                    
                    char_modified = False
                    if removed_count > 0 or dress_tag_list:
                        yml_data[key]['positive']['char'] = filtered_char
                        char_modified = True
                        modified_count += 1
                        total_removed_tags += removed_count
                        
                        if dress_tag_list:
                            print(f"    - {key}: {removed_count}개 태그 제거, {len(dress_tag_list)}개 dress 태그 이동")
                        else:
                            print(f"    - {key}: {removed_count}개 태그 제거")
                    
                    # dress 필드 처리
                    has_dress = 'dress' in positive_dict
                    existing_dress_value = positive_dict.get('dress', '')
                    
                    if dress_tag_list:
                        existing_dress_tags = []
                        if has_dress and existing_dress_value:
                            existing_dress_tags = extract_tags_from_dress_field(existing_dress_value)
                        
                        merged_dress_tags = merge_dress_tags(existing_dress_tags, dress_tag_list)
                        
                        if merged_dress_tags:
                            dress_tags_str = ', '.join(merged_dress_tags)
                            dress_value = f'{{  {dress_tags_str} |4::__dress__}},'
                        else:
                            dress_value = '{   |4::__dress__},'
                        
                        if has_dress:
                            if set(TagProcessor.normalize_tag(tag) for tag in merged_dress_tags) != \
                               set(TagProcessor.normalize_tag(tag) for tag in existing_dress_tags):
                                yml_data[key]['positive']['dress'] = dress_value
                                modified_dress_count += 1
                                if existing_dress_tags:
                                    print(f"      → dress 필드 업데이트: 기존 {len(existing_dress_tags)}개 + 신규 {len(dress_tag_list)}개 → 총 {len(merged_dress_tags)}개 태그")
                                else:
                                    print(f"      → dress 필드 업데이트: {len(merged_dress_tags)}개 태그 추가")
                        else:
                            yml_data[key]['positive']['dress'] = dress_value
                            modified_dress_count += 1
                            print(f"      → dress 필드 추가: {len(merged_dress_tags)}개 태그")
                    elif not has_dress:
                        yml_data[key]['positive']['dress'] = '{   |4::__dress__},'
                        modified_dress_count += 1
                        if not char_modified:
                            print(f"    - {key}: dress 키 추가")
                        else:
                            print(f"      → dress 키 추가 (기본값)")
    
    return yml_data, modified_count, total_removed_tags, modified_dress_count

def process_type(type_name: str):
    """각 타입에 대해 char.yml 파일을 처리합니다."""
    print(f"\n{'='*80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'='*80}")
    
    yml_path = os.path.join(base_dir, 'ComfyU-auto-script_data', type_name, 'lora', 'char.yml')
    
    if not excluded_tags:
        print(f"  경고: 제외 태그 목록이 비어있습니다.")
        return
    
    print(f"  제외 태그 개수: {len(excluded_tags)}개")
    print(f"  dress 태그 개수: {len(dress_tags)}개")
    
    modified_data, modified_count, total_removed_tags, modified_dress_count = process_char_yml(
        yml_path, excluded_tags, dress_tags
    )
    
    if modified_data is None:
        return
    
    if modified_count == 0 and modified_dress_count == 0:
        print(f"  [OK] 수정할 항목이 없습니다.")
        return
    
    print(f"\n  수정된 내용 저장 중...")
    if yaml_handler.save(yml_path, modified_data):
        messages = []
        if modified_count > 0:
            messages.append(f"{modified_count}개 키에서 총 {total_removed_tags}개 태그 제거")
        if modified_dress_count > 0:
            messages.append(f"{modified_dress_count}개 키의 dress 필드 추가/수정")
        print(f"  [OK] {', '.join(messages)}")
    else:
        print(f"  [실패] 파일 저장에 실패했습니다.")

if __name__ == "__main__":
    print("="*80)
    print("char.yml 파일에서 제외 태그 제거")
    print("="*80)
    
    for type_name in types:
        try:
            process_type(type_name)
        except Exception as e:
            print(f"\n  [오류] {type_name} 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("모든 처리 완료!")
    print(f"{'='*80}")

