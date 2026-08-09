# -*- coding: utf-8 -*-
"""
SafeTensors 파일 읽기 유틸리티
"""
import os
import json
import glob
import struct
from typing import Dict, Optional, Tuple, Set


class SafeTensorsReader:
    """SafeTensors 파일을 읽는 클래스"""
    
    @staticmethod
    def extract_ss_tag_frequency(file_path: str) -> Optional[Dict]:
        """
        safetensors 파일에서 ss_tag_frequency 메타데이터를 추출합니다.

        safe_open(framework='pt') 는 내부적으로 torch 를 로드해
        오버헤드가 크므로, 파일 헤더(메타데이터)만 직접 읽어 처리합니다.
        tensor 데이터는 메모리에 로드하지 않습니다.

        Args:
            file_path: safetensors 파일 경로

        Returns:
            ss_tag_frequency 딕셔너리 또는 None
        """
        try:
            with open(file_path, "rb") as f:
                # safetensors 헤더: 처음 8바이트는 리틀엔디언 헤더 길이
                header_len = struct.unpack("<Q", f.read(8))[0]
                header = json.loads(f.read(header_len))

            metadata = header.get("__metadata__") or {}
            tag_frequency_str = metadata.get("ss_tag_frequency")
            if tag_frequency_str:
                return json.loads(tag_frequency_str)
            return None
        except Exception:
            return None
    
    @staticmethod
    def read_metadata(file_path: str) -> Dict:
        """
        safetensors 파일의 __metadata__ 를 직접 읽습니다.

        safe_open(framework='pt') 는 내부적으로 torch 를 로드해 오버헤드가 크므로,
        파일 헤더(메타데이터)만 직접 파싱합니다. tensor 데이터는 메모리에 로드하지 않습니다.

        Args:
            file_path: safetensors 파일 경로

        Returns:
            __metadata__ 딕셔너리 (없거나 오류 시 빈 dict)
        """
        try:
            with open(file_path, "rb") as f:
                header_len = struct.unpack("<Q", f.read(8))[0]
                header = json.loads(f.read(header_len))
            return header.get("__metadata__") or {}
        except Exception:
            return {}
    
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

