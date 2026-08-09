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
        
        temp_path = None
        try:
            os.makedirs(os.path.dirname(yml_path), exist_ok=True)
            # 임시 파일을 같은 디렉토리에 생성하고 완전히 작성합니다.
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
            # 임시 파일이 남아 있으면 삭제
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
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


def _parse_skip_value(raw: str) -> Any:
    """YAML `skip:` 스칼라 값을 원시 문자열에서 Python 값으로 변환합니다."""
    val = raw.strip()
    if " #" in val:  # 인라인 주석 제거
        val = val.split(" #", 1)[0].strip()
    val = val.strip().strip("'\"")
    low = val.lower()
    if low in ("", "null", "none", "~"):
        return None
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low == "auto":
        return "auto"
    # 정수 해석 (PyYAML 스칼라 규칙과 동일하게)
    neg = val[:1] in ("-", "+")
    digits = val[1:] if neg else val
    if digits.isdigit():
        return int(val)
    return val


def _parse_yaml_key(raw: str) -> str:
    """YAML 키 스칼라를 디코딩합니다.

    - 비인용(plain) 키: 그대로 반환
    - 단일 인용('...'): 감싼 따옴표 제거 + `''`(YAML 이스케이프) → `'`
    - 이중 인용("..."): 감싼 따옴표 제거 + `\\"`/`\\\\` 이스케이프 처리
    """
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        inner = raw[1:-1]
        return inner.replace('\\"', '"').replace('\\\\', '\\')
    return raw


def scan_top_level_keys(yml_path: str) -> set:
    """최상위 키를 텍스트 스캔으로 빠르게 수집합니다 (전체 YAML 파싱 회피).

    들여쓰기 0(공백/탭으로 시작하지 않는) 라인만 읽어 키를 추출하므로
    8MB 이상 대용량 파일에서도 수십 ms 안에 끝납니다.
    """
    keys = set()
    with open(yml_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line or line[:1] in (' ', '\t'):
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('- '):
                continue
            if ':' not in stripped:
                continue
            key = _parse_yaml_key(stripped.split(':', 1)[0])
            if key:
                keys.add(key)
    return keys


def scan_yaml_skip_values(yml_path: str, indent_size: int = 2) -> Dict[str, Any]:
    """최상위 키와 각 키의 `skip` 값을 텍스트 스캔으로 수집합니다.

    전체 YAML 파싱 없이 최상위 키(들여쓰기 0)와 해당 블록 내부의
    `skip:`(들여쓰기 indent_size) 값을 빠르게 얻습니다. skip 라인이 없는
    키는 기본값 None으로 기록됩니다.
    """
    result: Dict[str, Any] = {}
    current_key = None
    seen_skip = False
    skip_prefix = ' ' * indent_size + 'skip:'

    def flush() -> None:
        if current_key is not None and not seen_skip:
            result[current_key] = None

    with open(yml_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line:
                continue
            if line[:1] in (' ', '\t'):
                # 들여쓰기된 라인 → 현재 키의 skip 값 확인
                if current_key is not None and not seen_skip and line.startswith(skip_prefix):
                    result[current_key] = _parse_skip_value(line[len(skip_prefix):])
                    seen_skip = True
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('- '):
                continue
            if ':' not in stripped:
                continue
            key = _parse_yaml_key(stripped.split(':', 1)[0])
            # 새 최상위 키로 전환
            flush()
            current_key = key if key else None
            seen_skip = False
    flush()
    return result

