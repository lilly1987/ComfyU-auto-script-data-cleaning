# -*- coding: utf-8 -*-
"""
char.yml 파일에 누락된 키를 추가하고 태그를 채워넣는 스크립트
"""
import sys
import os

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, TagProcessor, SafeTensorsReader

# 설정 로드
config = ConfigLoader()
comfui_dir = config.get_comfui_dir()
data_dir = config.get_data_dir()
types = config.get_types()
excluded_tags = config.get_excluded_tags('char')
dress_tags = config.get_dress_tags()
max_tags = 64

# 기본 템플릿
template = {
    'weight': 150,
    'positive': {
        'char': "1girl , ",
        'dress': "{   |4::__dress__},"
    },
    'skip': False
}

def process_type(type_name: str):
    """각 타입에 대해 누락된 키를 찾아 char.yml에 추가"""
    print(f"\n{'='*80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'='*80}")
    
    folder_path = os.path.join(comfui_dir, 'models', 'loras', type_name, 'char')
    yml_path = os.path.join(data_dir, type_name, 'lora', 'char.yml')
    
    if not os.path.exists(folder_path):
        print(f"  경고: 폴더가 존재하지 않습니다: {folder_path}")
        return
    
    if not os.path.exists(yml_path):
        print(f"  경고: YML 파일이 존재하지 않습니다: {yml_path}")
        return
    
    # YML 파일에서 키 읽기
    print(f"  YML 파일 읽는 중: {yml_path}")
    import yaml
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            yml_data = yaml.safe_load(f)
            yml_keys = set(yml_data.keys()) if yml_data else set()
    except Exception as e:
        print(f"  [오류] YML 파일 읽기 실패: {e}")
        print(f"  작업을 중단합니다.")
        sys.exit(1)
    
    print(f"  YML 키 개수: {len(yml_keys)}")
    
    # safetensors 파일에서 키 추출
    print(f"  폴더 파일 목록 읽는 중: {folder_path}")
    safetensors_keys, key_to_file = SafeTensorsReader.get_keys_from_folder(folder_path)
    print(f"  폴더 파일 개수: {len(safetensors_keys)}")
    
    yml_keys_cleaned = {k for k in yml_keys if k}
    missing = safetensors_keys - yml_keys_cleaned
    matched = safetensors_keys & yml_keys_cleaned
    # return
    print(f"\n  비교 결과:")
    print(f"    - 일치하는 키: {len(matched)}")
    print(f"    - 누락된 키 개수: {len(missing)}")

    cnt=0
    for key in sorted(matched):
        d=yml_data[key]
        if d.get('skip',False):
            cnt+=1

    print(f"    - 스킵된 키 개수: {cnt}")
    print(f"    - 스킵되지 않은 키 개수: {len(matched)-cnt}")

if __name__ == "__main__":
    
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

