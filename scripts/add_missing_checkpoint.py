# -*- coding: utf-8 -*-
"""
checkpoint.yml 파일에 없는 safetensors 파일을 추가하는 스크립트
"""
import sys
import os
from pathlib import Path

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, YAMLHandler

# 설정 로드
config = ConfigLoader()
comfui_dir = config.get_comfui_dir()
data_dir = config.get_data_dir()
types = config.get_types()

# YAML 핸들러 생성
yaml_handler = YAMLHandler(allow_duplicate_keys=True)

def get_safetensors_files(checkpoint_path: str) -> set:
    """
    Checkpoint 디렉토리에서 모든 .safetensors 파일을 가져옵니다.
    
    Args:
        checkpoint_path: checkpoint 디렉토리 경로
    
    Returns:
        .safetensors 파일 이름 집합 (확장자 제거)
    """
    if not os.path.exists(checkpoint_path):
        print(f"  경고: 디렉토리가 없습니다: {checkpoint_path}")
        return set()
    
    files = set()
    try:
        for file in os.listdir(checkpoint_path):
            if file.endswith('.safetensors'):
                # 확장자 제거
                name = file[:-len('.safetensors')]
                files.add(name)
    except Exception as e:
        print(f"  오류: 파일 목록 읽기 실패: {e}")
    
    return files

def add_missing_checkpoints(yml_path: str, checkpoint_path: str):
    """
    checkpoint.yml에 없는 safetensors 파일을 추가합니다.
    
    Args:
        yml_path: checkpoint.yml 파일 경로
        checkpoint_path: safetensors 파일이 있는 디렉토리 경로
    """
    # YAML 로드
    yml_data = yaml_handler.load(yml_path)
    if yml_data is None:
        print(f"  [오류] YML 파일을 로드할 수 없습니다: {yml_path}")
        print(f"  작업을 중단합니다.")
        sys.exit(1)
    
    # safetensors 파일 목록 가져오기
    safetensors_files = get_safetensors_files(checkpoint_path)
    if not safetensors_files:
        print(f"  경고: safetensors 파일을 찾을 수 없습니다: {checkpoint_path}")
        return
    
    # 현재 YML에 있는 키들
    existing_keys = set(yml_data.keys())
    
    # 추가할 키들 (파일 목록 - 기존 키)
    missing_files = safetensors_files - existing_keys
    
    if not missing_files:
        print(f"  [OK] 추가할 파일이 없습니다.")
        return
    
    print(f"  추가할 파일: {len(missing_files)}개")
    
    # 파일에 직접 추가 (주석 포함)
    print(f"\n  YML 파일에 추가 중...")
    try:
        with open(yml_path, 'a', encoding='utf-8') as f:
            for filename in sorted(missing_files):
                # 각 파일마다 템플릿 추가
                f.write(f"'{filename}':\n")
                f.write(f"  skip: false\n")
                f.write(f"  weight: 150\n")
                f.write(f"  steps:\n")
                f.write(f"  - 30\n")
                f.write(f"  cfg:\n")
                f.write(f"  - 4.0\n")
                f.write(f"  #negative:\n")
                f.write(f"    #checkpoint: '  '\n")
                f.write(f"    #realistic: ','\n")
                f.write(f"    #quality: ' ,'\n")
                f.write(f"  #positive:\n")
                f.write(f"    #checkpoint: ' '\n")
                f.write(f"    #quality: ' '\n")
                f.write(f"    #anime: ''\n")
                f.write(f"  sampler_name:\n")
                f.write(f"  - euler_ancestral\n")
                f.write(f"  #- dpmpp_2m\n")
                f.write(f"  #- dpmpp_2m_sde\n")
                f.write(f"\n")
                
                print(f"    - {filename} 추가")
        
        print(f"  [OK] {len(missing_files)}개 파일이 추가되었습니다.")
    except Exception as e:
        print(f"  [실패] 파일 저장 중 오류: {e}")

def main():
    """메인 함수"""
    print("="*80)
    print("checkpoint.yml에 누락된 safetensors 파일 추가")
    print("="*80)
    
    for checkpoint_type in types:
        try:
            process_type(checkpoint_type)
        except Exception as e:
            print(f"\n  [오류] {checkpoint_type} 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("모든 처리 완료!")
    print(f"{'='*80}")


def process_type(checkpoint_type: str):
    """각 checkpoint 타입에 대해 누락된 파일을 찾아 checkpoint.yml에 추가"""
    print(f"\n{'='*80}")
    print(f"[{checkpoint_type}] 처리 시작")
    print(f"{'='*80}")
    
    yml_path = os.path.join(data_dir, checkpoint_type, 'checkpoint', 'checkpoint.yml')
    safetensors_path = os.path.join(comfui_dir, 'models', 'checkpoints', checkpoint_type)
    
    if not os.path.exists(yml_path):
        print(f"  경고: YML 파일이 존재하지 않습니다: {yml_path}")
        return
    
    if not os.path.exists(safetensors_path):
        print(f"  경고: 체크포인트 디렉토리가 존재하지 않습니다: {safetensors_path}")
        return
    
    print(f"  YML 파일: {yml_path}")
    print(f"  파일 경로: {safetensors_path}")
    
    add_missing_checkpoints(yml_path, safetensors_path)


if __name__ == "__main__":
    main()
