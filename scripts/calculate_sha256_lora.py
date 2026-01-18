# -*- coding: utf-8 -*-
"""
LoRA 및 Checkpoint 파일의 SHA256 해시를 계산하고 YAML로 저장하는 스크립트
병렬 처리 및 점진적 업데이트 지원
"""
import sys
import os
import glob
import hashlib
import threading
import signal
from typing import Dict, Optional

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, YAMLHandler


# 전역 변수 - 취소 신호 처리
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    """Ctrl+C 신호 처리"""
    print("\n\n취소 신호를 받았습니다. 진행 중인 작업을 완료한 후 종료합니다...")
    shutdown_event.set()


def calculate_sha256(file_path: str, chunk_size: int = 65536) -> Optional[str]:
    """파일의 SHA256 해시를 계산합니다."""
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                if shutdown_event.is_set():
                    return None
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"  오류: SHA256 계산 실패 - {file_path}: {e}")
        return None


def load_existing_sha256(output_path: str, yaml_handler: YAMLHandler) -> Dict[str, str]:
    """기존 YAML 파일에서 SHA256 정보를 로드합니다."""
    if os.path.exists(output_path):
        try:
            data = yaml_handler.load(output_path)
            if isinstance(data, dict):
                return data
        except Exception as e:
            print(f"  경고: 기존 파일 읽기 실패 - {e}")
    return {}


def get_safetensors_sha256(folder_dir: str, existing_sha256: Dict[str, str], 
                          yaml_handler: YAMLHandler, output_path: str, save_cnt: int=10) -> Dict[str, str]:
    """폴더의 safetensors 파일들의 SHA256을 계산합니다 (점진적 업데이트)."""
    sha256_dict = existing_sha256.copy()
    
    if not os.path.exists(folder_dir):
        print(f"  경고: 디렉토리가 존재하지 않습니다: {folder_dir}")
        return sha256_dict
    
    pattern = os.path.join(folder_dir, '*.safetensors')
    safetensors_files = glob.glob(pattern)
    
    total_files = len(safetensors_files)
    new_files = 0
    
    print(f"  발견된 파일: {total_files}개")
    
    sorted_files = sorted(safetensors_files)
    
    for idx, file_path in enumerate(sorted_files, 1):
        if shutdown_event.is_set():
            print(f"  취소됨: {idx-1}/{total_files}개 처리 후 중단")
            break
        
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]
        
        # 이미 계산된 파일 건너띄기
        if name_without_ext in existing_sha256:
            print(f"    [{idx}/{total_files}] {name_without_ext} (기존)")
            continue
        
        # SHA256 계산
        sha256_value = calculate_sha256(file_path)
        
        if sha256_value:
            sha256_dict[name_without_ext] = sha256_value
            new_files += 1
            print(f"    [{idx}/{total_files}] {name_without_ext} (신규)")
            
            # 주기적으로 저장 (취소 시에도 부분 저장 가능)
            if new_files % save_cnt == 0:
                save_sha256_yaml(sha256_dict, output_path, yaml_handler)
        else:
            print(f"    [{idx}/{total_files}] {name_without_ext} (실패)")
    
    return sha256_dict


def save_sha256_yaml(sha256_dict: Dict[str, str], output_path: str, yaml_handler: YAMLHandler) -> bool:
    """SHA256 딕셔너리를 YAML 파일로 저장합니다."""
    try:
        # 디렉토리 생성
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"  디렉토리 생성: {output_dir}")
        
        # YAML 저장
        yaml_handler.save(output_path, sha256_dict)
        print(f"  저장 완료: {output_path} ({len(sha256_dict)}개 항목)")
        return True
    except Exception as e:
        print(f"  오류: YAML 저장 실패 - {e}")
        return False


def process_lora(type_name: str, config: ConfigLoader, yaml_handler: YAMLHandler):
    """LoRA 파일을 처리합니다 (별도 스레드)."""
    try:
        comfui_dir = config.get_comfui_dir()
        data_dir = config.get_data_dir()
        
        lora_dir = os.path.join(comfui_dir,   'models', 'loras', type_name, 'etc')
        lora_output_yaml = os.path.join(data_dir, type_name, 'sha256_loras.yml')
        
        print(f"\n[LoRA] {type_name} 처리 시작")
        print(f"  원본 경로: {lora_dir}")
        print(f"  저장 경로: {lora_output_yaml}")
        
        # 기존 데이터 로드
        existing_loras = load_existing_sha256(lora_output_yaml, yaml_handler)
        if existing_loras:
            print(f"  기존 데이터 로드: {len(existing_loras)}개")
        
        # SHA256 계산
        print("  SHA256 계산 중...")
        lora_sha256_dict = get_safetensors_sha256(
            lora_dir, existing_loras, yaml_handler, lora_output_yaml
        )
        
        # 최종 저장
        if lora_sha256_dict:
            save_sha256_yaml(lora_sha256_dict, lora_output_yaml, yaml_handler)
            print(f"[LoRA] {type_name} 처리 완료")
        else:
            print(f"[LoRA] {type_name}: 처리할 파일이 없습니다.")
    
    except Exception as e:
        print(f"[LoRA] {type_name} 처리 중 오류: {e}")


def process_checkpoint(type_name: str, config: ConfigLoader, yaml_handler: YAMLHandler):
    """Checkpoint 파일을 처리합니다 (별도 스레드)."""
    try:
        comfui_dir = config.get_comfui_dir()
        data_dir = config.get_data_dir()
        
        checkpoint_dir = os.path.join(comfui_dir,  'models', 'checkpoints', type_name)
        checkpoint_output_yaml = os.path.join(data_dir, type_name, 'sha256_checkpoints.yml')
        
        print(f"\n[Checkpoint] {type_name} 처리 시작")
        print(f"  원본 경로: {checkpoint_dir}")
        print(f"  저장 경로: {checkpoint_output_yaml}")
        
        # 기존 데이터 로드
        existing_checkpoints = load_existing_sha256(checkpoint_output_yaml, yaml_handler)
        if existing_checkpoints:
            print(f"  기존 데이터 로드: {len(existing_checkpoints)}개")
        
        # SHA256 계산
        print("  SHA256 계산 중...")
        checkpoint_sha256_dict = get_safetensors_sha256(
            checkpoint_dir, existing_checkpoints, yaml_handler, checkpoint_output_yaml, save_cnt=1
        )
        
        # 최종 저장
        if checkpoint_sha256_dict:
            save_sha256_yaml(checkpoint_sha256_dict, checkpoint_output_yaml, yaml_handler)
            print(f"[Checkpoint] {type_name} 처리 완료")
        else:
            print(f"[Checkpoint] {type_name}: 처리할 파일이 없습니다.")
    
    except Exception as e:
        print(f"[Checkpoint] {type_name} 처리 중 오류: {e}")


def main():
    """메인 함수"""
    print("LoRA 및 Checkpoint SHA256 해시 계산 및 저장 (병렬 처리)")
    print("(Ctrl+C로 중단 가능, 진행 중인 작업은 완료 후 저장됨)\n")
    
    # Ctrl+C 신호 처리 등록
    signal.signal(signal.SIGINT, signal_handler)
    
    # 설정 로드
    config = ConfigLoader()
    types = config.get_types()
    
    if not types:
        print("오류: config.yml에서 types을 찾을 수 없습니다.")
        return
    
    # YAML 핸들러 생성
    yaml_handler = YAMLHandler()
    
    # 스레드 목록
    threads = []
    
    print(f"{'='*60}")
    print(f"처리할 타입: {', '.join(types)}")
    print(f"{'='*60}\n")
    
    # 각 타입별로 LoRA와 Checkpoint를 병렬로 처리
    for type_name in types:
        # LoRA 스레드
        lora_thread = threading.Thread(
            target=process_lora,
            args=(type_name, config, yaml_handler),
            name=f"LoRA-{type_name}"
        )
        threads.append(lora_thread)
        lora_thread.start()
        
        # Checkpoint 스레드
        checkpoint_thread = threading.Thread(
            target=process_checkpoint,
            args=(type_name, config, yaml_handler),
            name=f"Checkpoint-{type_name}"
        )
        threads.append(checkpoint_thread)
        checkpoint_thread.start()
    
    # 모든 스레드가 완료될 때까지 대기
    for thread in threads:
        thread.join()
    
    print(f"\n{'='*60}")
    if shutdown_event.is_set():
        print("작업이 사용자에 의해 취소되었습니다.")
        print("진행된 분량까지는 저장되었습니다.")
    else:
        print("모든 처리가 완료되었습니다.")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
