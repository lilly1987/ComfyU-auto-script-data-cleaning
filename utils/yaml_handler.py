# -*- coding: utf-8 -*-
"""
YAML 파일 처리 유틸리티
"""
import os
from typing import Dict, Any, Optional
from ruamel.yaml import YAML


class YAMLHandler:
    """YAML 파일을 읽고 쓰는 클래스 (주석 보존)"""
    
    def __init__(self, allow_duplicate_keys: bool = True):
        """
        Args:
            allow_duplicate_keys: 중복 키 허용 여부
        """
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.width = 1000000  # 줄바꿈 방지
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.allow_duplicate_keys = allow_duplicate_keys
    
    def load(self, yml_path: str) -> Optional[Dict[str, Any]]:
        """
        YAML 파일을 로드합니다.
        
        Args:
            yml_path: YAML 파일 경로
        
        Returns:
            YAML 데이터 또는 None
        """
        if not os.path.exists(yml_path):
            print(f"  경고: YML 파일이 존재하지 않습니다: {yml_path}")
            return None
        
        try:
            with open(yml_path, 'r', encoding='utf-8') as f:
                return self.yaml.load(f)
        except Exception as e:
            print(f"  오류: YML 파일 읽기 실패: {e}")
            return None
    
    def save(self, yml_path: str, yml_data: Dict[str, Any]) -> bool:
        """
        YAML 파일을 저장합니다.
        
        Args:
            yml_path: YAML 파일 경로
            yml_data: 저장할 YAML 데이터
        
        Returns:
            성공 여부
        """
        import tempfile
        import os
        import shutil
        
        try:
            os.makedirs(os.path.dirname(yml_path), exist_ok=True)
            # 임시 파일을 같은 디렉토리에 생성
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=os.path.dirname(yml_path),
                delete=False,
                suffix='.tmp'
            ) as temp_file:
                self.yaml.dump(yml_data, temp_file)
                temp_path = temp_file.name
            
            # 임시 파일을 원본 파일로 atomic하게 교체
            try:
                os.replace(temp_path, yml_path)
            except PermissionError:
                # Windows에서 파일이 열려있을 경우, 수동으로 복사 후 삭제
                shutil.copy2(temp_path, yml_path)
                os.remove(temp_path)
            return True
        except Exception as e:
            print(f"  오류: YML 파일 저장 실패: {e}")
            return False
    
    @staticmethod
    def load_simple(yml_path: str) -> Optional[Dict[str, Any]]:
        """
        간단한 YAML 파일 로드 (PyYAML 사용, 주석 보존 안함)
        
        Args:
            yml_path: YAML 파일 경로
        
        Returns:
            YAML 데이터 또는 None
        """
        import yaml as yaml_lib
        
        if not os.path.exists(yml_path):
            return None
        
        try:
            with open(yml_path, 'r', encoding='utf-8') as f:
                return yaml_lib.safe_load(f)
        except Exception as e:
            print(f"  오류: YML 파일 읽기 실패: {e}")
            return None

