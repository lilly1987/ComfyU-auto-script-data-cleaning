# -*- coding: utf-8 -*-
"""
lora.yml 파일의 'positive' 필드에서 제외 태그를 제거하는 스크립트
"""
import sys
import os

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, TagProcessor, YAMLHandler

# 설정 로드
config = ConfigLoader()
base_dir = config.get_base_dir()
types = config.get_types()
excluded_tags = config.get_excluded_tags('lora')

# YAML 핸들러 생성
yaml_handler = YAMLHandler(allow_duplicate_keys=True)

def process_lora_yml(yml_path: str, excluded_tags: list):
    """lora.yml 파일을 처리합니다."""
    yml_data = yaml_handler.load(yml_path)
    if yml_data is None:
        return None, 0, 0
    
    modified_count = 0
    total_removed_tags = 0
    
    for key, value in yml_data.items():
        if not isinstance(value, dict):
            continue
        
        if 'positive' in value and isinstance(value['positive'], dict):
            positive_dict = value['positive']
            
            for positive_key, positive_value in positive_dict.items():
                if isinstance(positive_value, str):
                    filtered_tags, removed_count = TagProcessor.remove_excluded_tags_from_string(
                        positive_value, excluded_tags, dress_tags=None
                    )
                    
                    if filtered_tags != positive_value:
                        yml_data[key]['positive'][positive_key] = filtered_tags
                        modified_count += 1
                        total_removed_tags += removed_count
                        
                        if removed_count > 0:
                            print(f"    - {key}.positive.{positive_key}: {removed_count}개 태그 제거")
    
    return yml_data, modified_count, total_removed_tags

def process_type(type_name: str):
    """각 타입에 대해 lora.yml 파일을 처리합니다."""
    print(f"\n{'='*80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'='*80}")
    
    yml_path = os.path.join(base_dir, 'ComfyU-auto-script_data', type_name, 'lora', 'lora.yml')
    
    if not excluded_tags:
        print(f"  경고: 제외 태그 목록이 비어있습니다.")
        return
    
    print(f"  제외 태그 개수: {len(excluded_tags)}개")
    
    modified_data, modified_count, total_removed_tags = process_lora_yml(
        yml_path, excluded_tags
    )
    
    if modified_data is None:
        return
    
    if modified_count == 0:
        print(f"  [OK] 수정할 항목이 없습니다.")
        return
    
    print(f"\n  수정된 내용 저장 중...")
    if yaml_handler.save(yml_path, modified_data):
        print(f"  [OK] {modified_count}개 키에서 총 {total_removed_tags}개 태그 제거")
    else:
        print(f"  [실패] 파일 저장에 실패했습니다.")

if __name__ == "__main__":
    print("="*80)
    print("lora.yml 파일의 positive 필드에서 제외 태그 제거")
    print("="*80)
    
    for type_name in types:
        try:
            process_type(type_name)
        except Exception as e:
            print(f"\n  [오류] {type_name} 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("처리 완료")
    print(f"{'='*80}")

