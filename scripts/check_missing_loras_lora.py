# -*- coding: utf-8 -*-
"""
WeightLora.yml에 등록되지 않은 LoRA 파일 검사 스크립트
"""
import sys
import os
import glob

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, YAMLHandler


def get_safetensors_files(lora_dir: str) -> set:
    """
    폴더에서 safetensors 파일명 목록을 가져옵니다 (경로, 확장자 제거).
    
    Args:
        lora_dir: LoRA 파일이 있는 디렉토리
    
    Returns:
        파일명 집합 (확장자 제외)
    """
    files = set()
    if not os.path.exists(lora_dir):
        print(f"  경고: 디렉토리가 존재하지 않습니다: {lora_dir}")
        return files
    
    pattern = os.path.join(lora_dir, '*.safetensors')
    safetensors_files = glob.glob(pattern)
    
    for file_path in safetensors_files:
        filename = os.path.basename(file_path)
        name_without_ext = os.path.splitext(filename)[0]
        files.add(name_without_ext)
    
    return files


def extract_loras_from_yaml(yaml_data: dict) -> set:
    """
    WeightLora.yml에서 loras 이름 목록을 추출합니다.
    구조: 단계1 -> dic -> 단계2 -> loras (dict or list)
    
    Args:
        yaml_data: YAML 파일에서 로드한 데이터
    
    Returns:
        LoRA 파일명 집합
    """
    loras = set()
    
    if not isinstance(yaml_data, dict):
        return loras
    
    # 단계1 레벨 순회
    for step1_key, step1_value in yaml_data.items():
        if not isinstance(step1_value, dict):
            continue
        
        # dic 키 확인
        if 'dic' not in step1_value:
            continue
        
        dic_value = step1_value['dic']
        if not isinstance(dic_value, dict):
            continue
        
        # 단계2 레벨 순회
        for step2_key, step2_value in dic_value.items():
            if not isinstance(step2_value, dict):
                continue
            
            # loras 키 확인
            if 'loras' not in step2_value:
                continue
            
            loras_value = step2_value['loras']
            
            # loras가 dict인 경우 (키 추출)
            if isinstance(loras_value, dict):
                for lora_name in loras_value.keys():
                    if isinstance(lora_name, str):
                        loras.add(lora_name)
            
            # loras가 list인 경우 (각 항목 추출)
            elif isinstance(loras_value, list):
                for lora_name in loras_value:
                    if isinstance(lora_name, str):
                        loras.add(lora_name)
    
    return loras


def check_missing_loras(type_name: str, config: ConfigLoader, yaml_handler: YAMLHandler):
    """
    특정 타입의 누락된 LoRA를 확인합니다.
    
    Args:
        type_name: 타입 이름 (예: 'IL')
        config: 설정 로더
        yaml_handler: YAML 핸들러
    """
    comfui_dir = config.get_comfui_dir()
    data_dir = config.get_data_dir()
    
    # 경로 생성
    lora_dir = os.path.join(comfui_dir,  'models', 'loras', type_name, 'etc')
    weight_lora_path = os.path.join(data_dir, type_name, 'WeightLora.yml')
    
    print(f"\n{'='*60}")
    print(f"타입: {type_name}")
    print(f"{'='*60}")
    
    # 1. safetensors 파일 목록 가져오기
    safetensors_files = get_safetensors_files(lora_dir)
    print(f"\n[1] SafeTensors 파일 목록 ({len(safetensors_files)}개):")
    if safetensors_files:
        for fname in sorted(safetensors_files)[:10]:
            print(f"    - {fname}")
        if len(safetensors_files) > 10:
            print(f"    ... 그 외 {len(safetensors_files) - 10}개")
    else:
        print("    (없음)")
    
    # 2. WeightLora.yml에서 등록된 loras 가져오기
    if not os.path.exists(weight_lora_path):
        print(f"\n경고: WeightLora.yml 파일이 없습니다: {weight_lora_path}")
        return
    
    yaml_data = yaml_handler.load(weight_lora_path)
    if yaml_data is None:
        print(f"\n오류: WeightLora.yml 읽기 실패")
        return
    
    registered_loras = extract_loras_from_yaml(yaml_data)
    print(f"\n[2] 등록된 LoRA 목록 ({len(registered_loras)}개):")
    if registered_loras:
        for fname in sorted(registered_loras)[:10]:
            print(f"    - {fname}")
        if len(registered_loras) > 10:
            print(f"    ... 그 외 {len(registered_loras) - 10}개")
    else:
        print("    (없음)")
    
    # 3. 누락된 파일 찾기
    missing_loras = safetensors_files - registered_loras
    
    print(f"\n[3] 등록되지 않은 LoRA 파일 ({len(missing_loras)}개):")
    if missing_loras:
        for fname in sorted(missing_loras):
            print(f"    - {fname}")
    else:
        print("    (없음)")
    
    return {
        'type': type_name,
        'missing_count': len(missing_loras),
        'missing_loras': sorted(missing_loras)
    }


def main():
    """메인 함수"""
    print("WeightLora.yml 등록 현황 검사")
    
    # 설정 로드
    config = ConfigLoader()
    types = config.get_types()
    
    if not types:
        print("오류: config.yml에서 types을 찾을 수 없습니다.")
        return
    
    # YAML 핸들러 생성
    yaml_handler = YAMLHandler()
    
    # 각 타입별 검사
    results = []
    for type_name in types:
        result = check_missing_loras(type_name, config, yaml_handler)
        if result:
            results.append(result)
    
    # 파일로 저장
    output_file = os.path.join(script_dir, 'missing_loras_report.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("WeightLora.yml 등록 현황 검사 보고서\n")
        f.write("="*60 + "\n\n")
        
        for result in results:
            type_name = result['type']
            missing_count = result['missing_count']
            missing_loras = result['missing_loras']
            
            f.write(f"타입: {type_name}\n")
            f.write(f"등록되지 않은 LoRA: {missing_count}개\n")
            
            if missing_loras:
                f.write("\n파일 목록:\n")
                for lora_name in missing_loras:
                    f.write(f"  - {lora_name}\n")
            else:
                f.write("(없음)\n")
            
            f.write("\n" + "-"*60 + "\n\n")
    
    print(f"\n\n보고서가 저장되었습니다: {output_file}")


if __name__ == '__main__':
    main()
