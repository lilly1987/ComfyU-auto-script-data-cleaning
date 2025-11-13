# -*- coding: utf-8 -*-
"""
태그 처리 유틸리티
"""
import re
from typing import List, Optional, Tuple
from collections import defaultdict


class TagProcessor:
    """태그 처리 관련 기능을 제공하는 클래스"""
    
    @staticmethod
    def normalize_tag(tag: str) -> str:
        """
        태그를 정규화합니다. 언더스코어를 공백으로 변환하고 소문자로 변환합니다.
        
        Args:
            tag: 정규화할 태그 문자열
        
        Returns:
            정규화된 태그 문자열
        """
        if not tag:
            return ''
        normalized = tag.replace('_', ' ').lower()
        normalized = ' '.join(normalized.split())
        return normalized
    
    @staticmethod
    def is_tag_excluded(tag: str, excluded_patterns: List[str]) -> bool:
        """
        태그가 제외 패턴에 해당하는지 확인합니다.
        
        Args:
            tag: 확인할 태그 문자열
            excluded_patterns: 제외 패턴 리스트
        
        Returns:
            제외되어야 하면 True
        """
        normalized_tag = TagProcessor.normalize_tag(tag)
        
        for pattern in excluded_patterns:
            if isinstance(pattern, re.Pattern):
                if pattern.search(normalized_tag):
                    return True
            elif isinstance(pattern, str) and pattern.startswith('/') and pattern.endswith('/'):
                try:
                    regex_pattern = pattern[1:-1]
                    if re.search(regex_pattern, normalized_tag, re.IGNORECASE):
                        return True
                except re.error:
                    if TagProcessor.normalize_tag(pattern[1:-1]) == normalized_tag:
                        return True
            else:
                if TagProcessor.normalize_tag(pattern) == normalized_tag:
                    return True
        
        return False
    
    @staticmethod
    def remove_excluded_tags_from_string(
        tag_string: str,
        excluded_tags: List[str],
        dress_tags: Optional[List[str]] = None
    ) -> Tuple[str, int]:
        """
        태그 문자열에서 제외 태그와 중복 태그를 제거합니다.
        
        Args:
            tag_string: 쉼표로 구분된 태그 문자열
            excluded_tags: 제외 태그 목록
            dress_tags: dress 태그 목록 (제거할 태그, None이면 제거 안함)
        
        Returns:
            (필터링된 태그 문자열, 제거된 태그 개수)
        """
        if not tag_string or not tag_string.strip():
            return tag_string, 0
        
        tags = [tag.strip() for tag in tag_string.split(',')]
        filtered_tags = []
        seen_normalized = set()
        removed_count = 0
        
        for tag in tags:
            if not tag:
                continue
            
            if TagProcessor.is_tag_excluded(tag, excluded_tags):
                removed_count += 1
                continue
            
            if dress_tags and TagProcessor.is_tag_excluded(tag, dress_tags):
                removed_count += 1
                continue
            
            normalized = TagProcessor.normalize_tag(tag)
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                filtered_tags.append(tag)
            else:
                removed_count += 1
        
        if not filtered_tags:
            if tags and any(tag for tag in tags if tag):
                result = " , "
            else:
                result = tag_string
        else:
            result = ', '.join(filtered_tags)
        
        return result, removed_count
    
    @staticmethod
    def extract_dress_tags_from_string(tag_string: str, dress_tags: List[str]) -> List[str]:
        """
        태그 문자열에서 dress 태그를 추출합니다.
        
        Args:
            tag_string: 쉼표로 구분된 태그 문자열
            dress_tags: dress 태그 목록
        
        Returns:
            추출된 dress 태그 리스트 (중복 제거됨)
        """
        if not tag_string or not tag_string.strip() or not dress_tags:
            return []
        
        tags = [tag.strip() for tag in tag_string.split(',')]
        dress_tag_list = []
        seen_normalized = set()
        
        for tag in tags:
            if not tag:
                continue
            if TagProcessor.is_tag_excluded(tag, dress_tags):
                normalized = TagProcessor.normalize_tag(tag)
                if normalized not in seen_normalized:
                    seen_normalized.add(normalized)
                    dress_tag_list.append(tag)
        
        return dress_tag_list
    
    @staticmethod
    def process_tag_frequency(
        tag_frequency: dict,
        max_tags: int = 64,
        excluded_tags: Optional[List[str]] = None,
        dress_tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        ss_tag_frequency를 처리하여 정렬된 태그 문자열을 반환합니다.
        
        Args:
            tag_frequency: ss_tag_frequency 딕셔너리
            max_tags: 최대 태그 개수
            excluded_tags: 제거할 태그 목록
            dress_tags: dress 태그 목록 (제외하고 반환)
        
        Returns:
            정렬된 태그 문자열 또는 None
        """
        if not tag_frequency:
            return None
        
        if excluded_tags is None:
            excluded_tags = []
        
        tag_counts = defaultdict(int)
        
        for first_key, second_dict in tag_frequency.items():
            if isinstance(second_dict, dict):
                for tag, count in second_dict.items():
                    tag_counts[tag] += count
        
        if not tag_counts:
            return None
        
        tag_counts_filtered = {}
        for tag, count in tag_counts.items():
            if TagProcessor.is_tag_excluded(tag, excluded_tags):
                continue
            if dress_tags and TagProcessor.is_tag_excluded(tag, dress_tags):
                continue
            tag_counts_filtered[tag] = count
        
        if not tag_counts_filtered:
            return None
        
        counts = list(tag_counts_filtered.values())
        average_count = sum(counts) / len(counts) if counts else 0
        
        filtered_tags = [(tag, count) for tag, count in tag_counts_filtered.items() if count >= average_count]
        sorted_tags = sorted(filtered_tags, key=lambda x: x[1], reverse=True)
        sorted_tags = sorted_tags[:max_tags]
        
        tag_names = [tag for tag, count in sorted_tags]
        return ", ".join(tag_names)
    
    @staticmethod
    def extract_dress_tags_from_tag_frequency(
        tag_frequency: dict,
        dress_tags: List[str]
    ) -> List[str]:
        """
        ss_tag_frequency에서 dress 태그를 추출합니다.
        
        Args:
            tag_frequency: ss_tag_frequency 딕셔너리
            dress_tags: dress 태그 목록
        
        Returns:
            dress 태그 리스트
        """
        if not tag_frequency or not dress_tags:
            return []
        
        tag_counts = defaultdict(int)
        
        for first_key, second_dict in tag_frequency.items():
            if isinstance(second_dict, dict):
                for tag, count in second_dict.items():
                    tag_counts[tag] += count
        
        if not tag_counts:
            return []
        
        dress_tag_list = []
        seen_normalized = set()
        
        for tag, count in tag_counts.items():
            if TagProcessor.is_tag_excluded(tag, dress_tags):
                normalized = TagProcessor.normalize_tag(tag)
                if normalized not in seen_normalized:
                    seen_normalized.add(normalized)
                    dress_tag_list.append(tag)
        
        return dress_tag_list

