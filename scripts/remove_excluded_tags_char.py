# -*- coding: utf-8 -*-
"""
char.yml 파일의 'char' 필드에서 제외 태그를 제거하는 스크립트
"""
import sys
import os
import re

# 스크립트 디렉토리를 Python 경로에 추가
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, TagProcessor, YAMLHandler

# 설정 로드
config = ConfigLoader()
base_dir = config.get_base_dir()
types = config.get_types()
excluded_tags = config.get_excluded_tags('char')
dress_tags = config.get_dress_tags()

# YAML 핸들러 생성
yaml_handler = YAMLHandler(allow_duplicate_keys=True)

def extract_dress_structure_from_field(dress_value: str) -> str:
    """dress 필드 값에서 {||} 구조를 추출합니다."""
    if not dress_value or not isinstance(dress_value, str):
        return ''
    
    # {  {tag1,tag2|tag3,tag4|...}  |4::__dress__}, 형태에서 내부 {} 블록 추출
    match = re.search(r'\{\s*\{([^}]+)\}\s*\|', dress_value)
    if match:
        inner_content = match.group(1).strip()
        return inner_content
    
    # 기존 형식 지원: {tag1,tag2|...} 형태
    match = re.search(r'\{([^|]+)\|', dress_value)
    if match:
        tags_str = match.group(1).strip()
        return tags_str
    
    return ''

def extract_dress_structure_from_char(char_value: str, dress_tags: list) -> str:
    """char 필드에서 dress 태그가 포함된 {||} 구조를 추출합니다."""
    if not char_value or not dress_tags:
        return ''
    
    # {tag1,tag2|tag3,tag4|...} 구조에서 dress 태그가 포함된 부분 찾기
    brace_pattern = r'\{([^}]*)\}'
    matches = list(re.finditer(brace_pattern, char_value))
    
    for match in matches:
        brace_content = match.group(1).strip()
        if not brace_content:
            continue
        
        # |로 분리된 각 부분 확인
        parts = [p.strip() for p in brace_content.split('|')]
        dress_parts = []
        
        for part in parts:
            part_tags = [t.strip() for t in part.split(',') if t.strip()]
            # 이 부분에 dress 태그가 있는지 확인
            has_dress_tag = False
            for tag in part_tags:
                if TagProcessor.is_tag_excluded(tag, dress_tags):
                    has_dress_tag = True
                    break
            
            if has_dress_tag:
                # dress 태그만 남기기
                filtered_tags = [tag for tag in part_tags if TagProcessor.is_tag_excluded(tag, dress_tags)]
                if filtered_tags:
                    dress_parts.append(', '.join(filtered_tags))
        
        if dress_parts:
            # {||} 구조 유지
            return '|'.join(dress_parts)
    
    # {||} 구조가 아닌 일반 태그에서 dress 태그 추출 (단일 그룹)
    dress_tag_list = TagProcessor.extract_dress_tags_from_string(char_value, dress_tags)
    if dress_tag_list:
        return ', '.join(dress_tag_list)
    
    return ''

def merge_dress_tags(existing_tags: list, new_tags: list) -> list:
    """기존 dress 태그와 새로운 dress 태그를 병합합니다."""
    merged_tags = []
    seen_normalized = set()
    
    for tag in existing_tags:
        if not tag:
            continue
        normalized = TagProcessor.normalize_tag(tag)
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            merged_tags.append(tag)
    
    for tag in new_tags:
        if not tag:
            continue
        normalized = TagProcessor.normalize_tag(tag)
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            merged_tags.append(tag)
    
    return merged_tags

def process_char_yml(yml_path: str, excluded_tags: list, dress_tags: list):
    """char.yml 파일을 처리합니다."""
    yml_data = yaml_handler.load(yml_path)
    if yml_data is None:
        return None, 0, 0, 0
    
    modified_count = 0
    total_removed_tags = 0
    modified_dress_count = 0
    # modified_keys -> dict: key -> list of removed tags
    modified_keys = {}
    
    for key, value in yml_data.items():
        if not isinstance(value, dict):
            continue
        
        if 'positive' in value and isinstance(value['positive'], dict):
            positive_dict = value['positive']
            
            if 'char' in positive_dict:
                char_value = positive_dict['char']
                
                if isinstance(char_value, str):
                    # dress 태그 추출
                    dress_tag_list = TagProcessor.extract_dress_tags_from_string(
                        char_value, dress_tags
                    ) if dress_tags else []
                    
                    # 제외 태그 및 dress 태그 제거 (제거된 태그 목록 포함)
                    filtered_char, removed_count, removed_tags = TagProcessor.remove_excluded_tags_from_string_with_list(
                        char_value, excluded_tags, dress_tags
                    )
                    
                    char_modified = False
                    if removed_count > 0 or dress_tag_list:
                        yml_data[key]['positive']['char'] = filtered_char
                        char_modified = True
                        modified_count += 1
                        total_removed_tags += removed_count
                        # 기록된 제거 태그 누적 (dress로 이동한 태그는 제외)
                        if removed_tags:
                            # dress_tag_list에 포함된 태그(정규화된)를 제거
                            dress_norm = set()
                            if dress_tag_list:
                                for dt in dress_tag_list:
                                    dress_norm.add(TagProcessor.normalize_tag(dt))

                            filtered_removed = []
                            for t in removed_tags:
                                if dress_norm and TagProcessor.normalize_tag(t) in dress_norm:
                                    continue
                                filtered_removed.append(t)

                            if filtered_removed:
                                modified_keys.setdefault(key, []).extend(filtered_removed)
                        
                        if dress_tag_list:
                            print(f"    - {key}: {removed_count}개 태그 제거, {len(dress_tag_list)}개 dress 태그 이동")
                        else:
                            print(f"    - {key}: {removed_count}개 태그 제거")
                    
                    # dress 필드 처리
                    has_dress = 'dress' in positive_dict
                    existing_dress_value = positive_dict.get('dress', '')
                    
                    if dress_tag_list:
                        # 원본 char_value에서 dress 태그 구조 추출
                        new_dress_structure = extract_dress_structure_from_char(char_value, dress_tags)
                        
                        # 기존 dress 필드 구조 추출
                        existing_dress_structure = ''
                        if has_dress and existing_dress_value:
                            existing_dress_structure = extract_dress_structure_from_field(existing_dress_value)
                        
                        # 구조 병합
                        if existing_dress_structure and new_dress_structure:
                            merged_structure = f'{existing_dress_structure}|{new_dress_structure}'
                        elif new_dress_structure:
                            merged_structure = new_dress_structure
                        elif existing_dress_structure:
                            merged_structure = existing_dress_structure
                        else:
                            merged_structure = ''
                        
                        if merged_structure:
                            dress_value = f'{{  {{{merged_structure}}}  |4::__dress__}},'
                        else:
                            dress_value = '{   |4::__dress__},'
                        
                        # 변경 여부 확인 (기존 구조와 비교)
                        should_update = False
                        if not has_dress:
                            should_update = True
                        elif existing_dress_structure != merged_structure:
                            should_update = True
                        
                        if should_update:
                            yml_data[key]['positive']['dress'] = dress_value
                            modified_dress_count += 1
                            if existing_dress_structure:
                                print(f"      → dress 필드 업데이트: 기존 구조 + 신규 구조 병합")
                            else:
                                print(f"      → dress 필드 추가: {len(dress_tag_list)}개 태그")
                    elif not has_dress:
                        yml_data[key]['positive']['dress'] = '{   |4::__dress__},'
                        modified_dress_count += 1
                        if not char_modified:
                            print(f"    - {key}: dress 키 추가")
                        else:
                            print(f"      → dress 키 추가 (기본값)")

                    # 수정된 키 기록
                    if char_modified or (dress_tag_list or (not has_dress and modified_dress_count > 0)):
                        # ensure key exists in modified_keys even if no removed tags
                        modified_keys.setdefault(key, modified_keys.get(key, []))
    
    return yml_data, modified_count, total_removed_tags, modified_dress_count, modified_keys

def process_type(type_name: str):
    """각 타입에 대해 char.yml 파일을 처리합니다."""
    print(f"\n{'='*80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'='*80}")
    
    yml_path = os.path.join(base_dir, 'ComfyU-auto-script_data', type_name, 'lora', 'char.yml')
    
    if not excluded_tags:
        print(f"  경고: 제외 태그 목록이 비어있습니다.")
        return
    
    print(f"  제외 태그 개수: {len(excluded_tags)}개")
    print(f"  dress 태그 개수: {len(dress_tags)}개")
    
    modified_data, modified_count, total_removed_tags, modified_dress_count, modified_keys = process_char_yml(
        yml_path, excluded_tags, dress_tags
    )
    
    if modified_data is None:
        return
    
    if modified_count == 0 and modified_dress_count == 0:
        print(f"  [OK] 수정할 항목이 없습니다.")
        return
    
    print(f"\n  수정된 내용 저장 중...")
    # 기존 YAML을 로드해서 수정된 키에 대해 '# auto' 주석을 추가하고 저장
    try:
        yaml = yaml_handler.yaml
        # 원본을 로드 (주석 보존되는 CommentedMap)
        orig = None
        try:
            with open(yml_path, 'r', encoding='utf-8') as f:
                orig = yaml.load(f) or {}
        except Exception:
            orig = {}

        # ensure orig is a mapping-like object
        for k, removed_list in modified_keys.items():
            try:
                orig[k] = modified_data.get(k, {})
                # 주석 문자열 구성
                if removed_list:
                    # 중복 제거 및 정렬된 표현
                    uniq = []
                    seen = set()
                    for t in removed_list:
                        n = TagProcessor.normalize_tag(t)
                        if n not in seen:
                            seen.add(n)
                            uniq.append(t)
                    comment_text = 'auto removed: ' + ', '.join(uniq)
                else:
                    comment_text = 'auto'

                # ruamel CommentedMap에 eol 코멘트 추가
                try:
                    orig.yaml_add_eol_comment(comment_text, k)
                except Exception:
                    # 일부 경우에는 orig이 일반 dict일 수 있으므로 무시
                    pass
            except Exception:
                pass

        # 덮어쓰기 저장
        with open(yml_path, 'w', encoding='utf-8') as f:
            yaml.dump(orig, f)
        saved_ok = True
    except Exception as e:
        print(f"  오류: YML 파일 저장 실패: {e}")
        saved_ok = False

    if saved_ok:
        messages = []
        if modified_count > 0:
            messages.append(f"{modified_count}개 키에서 총 {total_removed_tags}개 태그 제거")
        if modified_dress_count > 0:
            messages.append(f"{modified_dress_count}개 키의 dress 필드 추가/수정")
        print(f"  [OK] {', '.join(messages)}")
    else:
        print(f"  [실패] 파일 저장에 실패했습니다.")

if __name__ == "__main__":
    print("="*80)
    print("char.yml 파일에서 제외 태그 제거")
    print("="*80)
    
    for type_name in types:
        try:
            process_type(type_name)
        except Exception as e:
            print(f"\n  [오류] {type_name} 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("모든 처리 완료!")
    print(f"{'='*80}")

