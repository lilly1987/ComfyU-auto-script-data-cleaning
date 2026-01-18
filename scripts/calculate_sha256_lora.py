# -*- coding: utf-8 -*-
"""
LoRA 및 Checkpoint 파일의 SHA256 해시를 계산하고 YAML로 저장하는 스크립트
"""
import sys
import os
import glob
import hashlib

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, YAMLHandler


def calculate_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """
    파일의 SHA256 해시를 계산합니다.
    
    Args:
        file_path: 파일 경로
        chunk_size: 읽을 청크 크기 (기본값: 64KB)
    
    Returns:
        SHA256 해시값 (16진수 문자열)
    """
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"  오류: SHA256 계산 실패 - {file_path}: {e}")
        return None


def get_safetensors_sha256(lora_dir: str) -> dict:
    """
    폴더의 safetensors 파일들의 SHA256을 계산합니다.
    
    Args:
        lora_dir: LoRA 파일이 있는 디렉토리
    
    Returns:
        {파일명: sha256값} 딕셔너리
    """
    sha256_dict = {}
    
    if not os.path.exists(lora_dir):
        print(f"  경고: 디렉토리가 존재하지 않습니다: {lora_dir}")
        return sha256_dict
    
    pattern = os.path.join(lora_dir, '*.safetensors')
    safetensors_files = glob.glob(pattern)
    
    print(f"  발견된 파일: {len(safetensors_files)}개")
    
    for idx, file_path in enumerate(sorted(safetensors_files), 1):
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # SHA256 계산
        sha256_value = calculate_sha256(file_path)
        
        if sha256_value:
            sha256_dict[name_without_ext] = sha256_value
            print(f"    [{idx}/{len(safetensors_files)}] {name_without_ext}")
        else:
            print(f"    [{idx}/{len(safetensors_files)}] {name_without_ext} (실패)")
    
    return sha256_dict


def save_sha256_yaml(sha256_dict: dict, output_path: str, yaml_handler: YAMLHandler) -> bool:
    """
    SHA256 딕셔너리를 YAML 파일로 저장합니다.
    
    Args:
        sha256_dict: {파일명: sha256값} 딕셔너리
        output_path: 저장할 YAML 파일 경로
        yaml_handler: YAML 핸들러
    
    Returns:
        성공 여부
    """
    try:
        # 디렉토리 생성
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"  디렉토리 생성: {output_dir}")
        
        # YAML 저장
        yaml_handler.save(output_path, sha256_dict)
        print(f"  저장 완료: {output_path}")
        return True
    except Exception as e:
        print(f"  오류: YAML 저장 실패 - {e}")
        return False


def process_type_files(type_name: str, config: ConfigLoader, yaml_handler: YAMLHandler):
    """
    특정 타입의 LoRA 및 Checkpoint 파일들을 처리합니다.
    
    Args:
        type_name: 타입 이름 (예: 'IL')
        config: 설정 로더
        yaml_handler: YAML 핸들러
    """
    comfui_dir = config.get_comfui_dir()
    data_dir = config.get_data_dir()
    
    print(f"\n{'='*60}")
    print(f"타입: {type_name}")
    print(f"{'='*60}")
    
    # LoRA 처리
    print(f"\n[1] LoRA 파일 처리")
    print(f"-" * 60)
    lora_dir = os.path.join(comfui_dir, 'models', 'loras', type_name, 'etc')
    lora_output_yaml = os.path.join(data_dir, type_name, 'sha256_loras.yml')
    
    print(f"원본 경로: {lora_dir}")
    print(f"저장 경로: {lora_output_yaml}")
    print()
    
    print("SHA256 계산 중...")
    lora_sha256_dict = get_safetensors_sha256(lora_dir)
    
    if lora_sha256_dict:
        print(f"총 {len(lora_sha256_dict)}개 파일 처리 완료")
        print("YAML 저장 중...")
        save_sha256_yaml(lora_sha256_dict, lora_output_yaml, yaml_handler)
    else:
        print(f"경고: 처리할 LoRA 파일이 없습니다.")
    
    # Checkpoint 처리
    print(f"\n[2] Checkpoint 파일 처리")
    print(f"-" * 60)
    checkpoint_dir = os.path.join(comfui_dir,  'models', 'checkpoints', type_name)
    checkpoint_output_yaml = os.path.join(data_dir, type_name, 'sha256_checkpoints.yml')
    
    print(f"원본 경로: {checkpoint_dir}")
    print(f"저장 경로: {checkpoint_output_yaml}")
    print()
    
    print("SHA256 계산 중...")
    checkpoint_sha256_dict = get_safetensors_sha256(checkpoint_dir)
    
    if checkpoint_sha256_dict:
        print(f"총 {len(checkpoint_sha256_dict)}개 파일 처리 완료")
        print("YAML 저장 중...")
        save_sha256_yaml(checkpoint_sha256_dict, checkpoint_output_yaml, yaml_handler)
    else:
        print(f"경고: 처리할 Checkpoint 파일이 없습니다.")


def main():
    """메인 함수"""
    print("LoRA 및 Checkpoint SHA256 해시 계산 및 저장")
    print()
    
    # 설정 로드
    config = ConfigLoader()
    types = config.get_types()
    
    if not types:
        print("오류: config.yml에서 types을 찾을 수 없습니다.")
        return
    
    # YAML 핸들러 생성
    yaml_handler = YAMLHandler()
    
    # 각 타입별 처리
    for type_name in types:
        process_type_files(type_name, config, yaml_handler)
    
    print(f"\n{'='*60}")
    print("모든 처리가 완료되었습니다.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
