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
base_dir = config.get_base_dir()
types = config.get_types()

# YAML 핸들러 생성
yaml_handler = YAMLHandler(allow_duplicate_keys=True)

TEMPLATE = """  steps:
  - 30
  cfg:
  - 4.0
  weight: 150
  #negative:
    #checkpoint: '  '
    #realistic: ','
    #quality: ' ,'
  #positive:    
    #checkpoint: ' ' 
    #quality: ' ' 
    #anime: '' 
  sampler_name:
  - euler_ancestral
  #- dpmpp_2m
  #- dpmpp_2m_sde"""

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
        print(f"  오류: YML 파일을 로드할 수 없습니다: {yml_path}")
        return
    
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
    
    # 추가할 파일들을 정렬하고 YAML에 추가
    for filename in sorted(missing_files):
        # 템플릿을 파싱하여 구조 생성
        template_lines = TEMPLATE.strip().split('\n')
        
        # 딕셔너리 구조로 변환 (간단하게 처리)
        yml_data[filename] = {
            'steps': [30],
            'cfg': [4.0],
            'weight': 150,
            'sampler_name': ['euler_ancestral']
        }
        
        print(f"    - {filename} 추가")
    
    # 파일 저장
    print(f"\n  YML 파일 저장 중...")
    try:
        # 원본 YAML을 로드해서 주석을 보존하면서 저장
        yaml = yaml_handler.yaml
        
        # 원본을 로드 (주석 보존되는 CommentedMap)
        try:
            with open(yml_path, 'r', encoding='utf-8') as f:
                orig = yaml.load(f) or {}
        except Exception:
            orig = {}
        
        # 추가할 파일들을 원본에 추가
        for filename in sorted(missing_files):
            orig[filename] = {
                'steps': [30],
                'cfg': [4.0],
                'weight': 150,
                'sampler_name': ['euler_ancestral']
            }
            # skip: true 주석 추가
            try:
                orig.yaml_add_eol_comment('skip: true', filename)
            except Exception:
                pass
        
        # 저장
        with open(yml_path, 'w', encoding='utf-8') as f:
            yaml.dump(orig, f)
        
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
    
    yml_path = os.path.join(base_dir, 'ComfyU-auto-script_data', checkpoint_type, 'checkpoint', 'checkpoint.yml')
    safetensors_path = os.path.join(base_dir, 'ComfyUI', 'models', 'checkpoints', checkpoint_type)
    
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
