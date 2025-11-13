# -*- coding: utf-8 -*-
"""
SafeTensors 파일 읽기 유틸리티
"""
import os
import json
import glob
from typing import Dict, Optional, Tuple, Set
from safetensors import safe_open


class SafeTensorsReader:
    """SafeTensors 파일을 읽는 클래스"""
    
    @staticmethod
    def extract_ss_tag_frequency(file_path: str) -> Optional[Dict]:
        """
        safetensors 파일에서 ss_tag_frequency 메타데이터를 추출합니다.
        
        Args:
            file_path: safetensors 파일 경로
        
        Returns:
            ss_tag_frequency 딕셔너리 또는 None
        """
        try:
            with safe_open(file_path, framework='pt') as f:
                metadata = f.metadata()
                
                if metadata and 'ss_tag_frequency' in metadata:
                    tag_frequency_str = metadata['ss_tag_frequency']
                    return json.loads(tag_frequency_str)
                return None
        except Exception:
            return None
    
    @staticmethod
    def get_keys_from_folder(folder_path: str) -> Tuple[Set[str], Dict[str, str]]:
        """
        폴더의 safetensors 파일에서 키를 추출합니다.
        
        Args:
            folder_path: safetensors 파일이 있는 폴더 경로
        
        Returns:
            (키 세트, 키->파일경로 딕셔너리) 튜플
        """
        keys = set()
        key_to_file = {}
        
        if not os.path.exists(folder_path):
            return keys, key_to_file
        
        pattern = os.path.join(folder_path, '*.safetensors')
        safetensors_files = glob.glob(pattern)
        
        for file_path in safetensors_files:
            filename = os.path.basename(file_path)
            key = os.path.splitext(filename)[0]
            keys.add(key)
            key_to_file[key] = file_path
        
        return keys, key_to_file

