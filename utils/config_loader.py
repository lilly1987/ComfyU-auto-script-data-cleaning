# -*- coding: utf-8 -*-
"""
설정 파일 로더
"""
import os
import yaml
from typing import Dict, List, Optional, Any


class ConfigLoader:
    """설정 파일을 로드하고 관리하는 클래스"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 설정 파일 경로 (None이면 스크립트 디렉토리의 config.yml 사용)
        """
        if config_path is None:
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(script_dir, 'config.yml')
        
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> Dict[str, Any]:
        """설정 파일을 로드합니다."""
        if not os.path.exists(self.config_path):
            print(f"  경고: 설정 파일이 존재하지 않습니다: {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            return self._config
        except Exception as e:
            print(f"  오류: 설정 파일 읽기 실패: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값을 가져옵니다."""
        return self._config.get(key, default)
    
    def get_base_dir(self) -> str:
        """작업 디렉토리를 가져옵니다."""
        return self.get('base_dir', r'W:\ComfyUI_windows_portable')
    
    def get_types(self) -> List[str]:
        """처리할 타입 리스트를 가져옵니다."""
        return self.get('types', ['IL', 'Pony'])
    
    def get_excluded_tags(self, section: str = 'char') -> List[str]:
        """
        제외 태그 목록을 가져옵니다.
        
        Args:
            section: 섹션 이름 ('char' 또는 'lora')
        """
        if section == 'char':
            return self.get('char', {}).get('excluded_tags', [])
        elif section == 'lora':
            return self.get('lora', {}).get('excluded_tags', [])
        return []
    
    def get_dress_tags(self) -> List[str]:
        """dress 태그 목록을 가져옵니다."""
        return self.get('char', {}).get('dress_tags', [])
    
    def get_max_tags(self, section: str = 'lora') -> int:
        """
        태그 최대 개수를 가져옵니다.
        
        Args:
            section: 섹션 이름 ('char' 또는 'lora')
        """
        if section == 'lora':
            return self.get('lora', {}).get('max_tags', 64)
        return 64

