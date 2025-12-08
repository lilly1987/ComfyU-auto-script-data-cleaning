# -*- coding: utf-8 -*-
"""
lora.yml 파일에 누락된 키를 추가하고 태그를 채워넣는 스크립트
"""
import sys
import os
import glob
import copy

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, TagProcessor, SafeTensorsReader, YAMLHandler

# 설정 로드
config = ConfigLoader()
base_dir = config.get_base_dir()
types = config.get_types()
excluded_tags = config.get_excluded_tags('lora')
max_tags = config.get_max_tags('lora')

# YAML 핸들러 생성
yaml_handler = YAMLHandler(allow_duplicate_keys=True)

def create_template(key: str, tags: str = None) -> dict:
    """키에 대한 기본 템플릿을 생성합니다."""
    tag_value = tags if tags else " ,"
    return {
        'tag': [],
        'positive': {
            key: tag_value
        },
        'skip': False,
    }

def get_existing_keys_from_yml_files(lora_folder_path: str) -> set:
    """lora 폴더의 yml 파일들(char.yml 제외)에서 키를 추출합니다."""
    keys = set()
    
    if not os.path.exists(lora_folder_path):
        return keys
    
    pattern = os.path.join(lora_folder_path, '*.yml')
    yml_files = glob.glob(pattern)
    
    for yml_file in yml_files:
        filename = os.path.basename(yml_file)
        if filename == 'char.yml':
            continue
        
        yml_data = YAMLHandler.load_simple(yml_file)
        if yml_data and isinstance(yml_data, dict):
            keys.update(yml_data.keys())
    
    return keys

def process_type(type_name: str):
    """각 타입에 대해 누락된 키를 찾아 lora.yml에 추가"""
    print(f"\n{'='*80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'='*80}")
    
    safetensors_folder = os.path.join(base_dir, 'ComfyUI', 'models', 'loras', type_name, 'etc')
    lora_folder = os.path.join(base_dir, 'ComfyU-auto-script_data', type_name, 'lora')
    lora_yml_path = os.path.join(lora_folder, 'lora.yml')
    
    # safetensors 파일에서 키 추출
    print(f"  safetensors 파일 읽는 중: {safetensors_folder}")
    safetensors_keys, key_to_file = SafeTensorsReader.get_keys_from_folder(safetensors_folder)
    print(f"  safetensors 키 개수: {len(safetensors_keys)}개")
    
    if not safetensors_keys:
        print(f"  경고: safetensors 파일이 없거나 키를 찾을 수 없습니다.")
        return
    
    # yml 파일들에서 기존 키 추출
    print(f"  yml 파일들 읽는 중: {lora_folder}")
    existing_keys = get_existing_keys_from_yml_files(lora_folder)
    print(f"  기존 yml 키 개수: {len(existing_keys)}개")
    
    # lora.yml에서 기존 키 추출
    lora_yml_data = yaml_handler.load(lora_yml_path) or {}
    lora_yml_keys = set(lora_yml_data.keys()) if lora_yml_data else set()
    print(f"  lora.yml 키 개수: {len(lora_yml_keys)}개")
    
    # 모든 기존 키 통합
    all_existing_keys = existing_keys | lora_yml_keys
    
    # 누락된 키 찾기
    missing_keys = safetensors_keys - all_existing_keys
    
    if not missing_keys:
        print(f"  [OK] 누락된 키가 없습니다.")
        return
    
    print(f"  누락된 키 개수: {len(missing_keys)}개")
    
    # lora.yml에 누락된 키 추가
    added_count = 0
    no_tag_count = 0
    
    for key in sorted(missing_keys):
        if key not in lora_yml_data:
            file_path = key_to_file.get(key)
            tags = None
            
            if file_path:
                tag_frequency = SafeTensorsReader.extract_ss_tag_frequency(file_path)
                
                if tag_frequency:
                    tags = TagProcessor.process_tag_frequency(
                        tag_frequency, max_tags=max_tags, excluded_tags=excluded_tags
                    )
                    
                    if tags:
                        filtered_tags, _ = TagProcessor.remove_excluded_tags_from_string(
                            tags, excluded_tags=[], dress_tags=None
                        )
                        tags = filtered_tags if filtered_tags and filtered_tags.strip() else tags
            
            lora_yml_data[key] = create_template(key, tags)
            added_count += 1
            
            if not tags or tags == " ,":
                no_tag_count += 1
    
    if added_count == 0:
        print(f"  [OK] 추가할 키가 없습니다.")
        return
    
    # lora.yml 저장
    print(f"\n  lora.yml 파일 저장 중...")
    if yaml_handler.save(lora_yml_path, lora_yml_data):
        tag_count = added_count - no_tag_count
        messages = [f"{added_count}개의 누락된 키가 lora.yml에 추가되었습니다"]
        if tag_count > 0:
            messages.append(f"태그 포함: {tag_count}개")
        if no_tag_count > 0:
            messages.append(f"태그 없음: {no_tag_count}개")
        print(f"  [OK] {', '.join(messages)}")
    else:
        print(f"  [실패] 파일 저장에 실패했습니다.")

if __name__ == "__main__":
    print("="*80)
    print("safetensors 파일의 키를 확인하고 lora.yml에 추가")
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

