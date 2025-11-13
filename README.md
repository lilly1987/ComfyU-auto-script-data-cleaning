# ComfyU-auto-script5

최적화 및 재설계된 ComfyUI 자동화 스크립트

## 구조

```
ComfyU-auto-script5/
├── utils/                    # 유틸리티 모듈
│   ├── __init__.py
│   ├── config_loader.py      # 설정 파일 로더
│   ├── tag_processor.py      # 태그 처리 유틸리티
│   ├── yaml_handler.py       # YAML 파일 처리
│   └── safetensors_reader.py # SafeTensors 파일 읽기
├── scripts/                   # 실행 스크립트
│   ├── add_missing_keys_char.py      # char.yml에 키 추가
│   ├── remove_excluded_tags_char.py # char.yml에서 태그 제거
│   ├── add_missing_keys_lora.py     # lora.yml에 키 추가
│   └── remove_excluded_tags_lora.py # lora.yml에서 태그 제거
├── config.yml                # 통합 설정 파일
└── README.md                 # 이 파일
```

## 주요 개선사항

### 1. 모듈화
- 공통 기능을 `utils` 모듈로 분리
- 코드 재사용성 향상
- 유지보수 용이

### 2. 설정 통합
- `config.yml`과 `config_lora.yml`을 하나의 `config.yml`로 통합
- 섹션별로 구분 (`char`, `lora`)

### 3. 클래스 기반 설계
- 각 기능을 클래스로 캡슐화
- 타입 힌팅 추가
- 문서화 개선

### 4. 에러 처리 개선
- try-except 블록 추가
- 명확한 에러 메시지

### 5. 코드 중복 제거
- 공통 로직 함수화
- 일관된 인터페이스

## 사용 방법

### 설정 파일 수정
`config.yml` 파일을 열어서 설정을 수정합니다.

### 스크립트 실행

#### char.yml 관련
```bash
# 누락된 키 추가
python scripts/add_missing_keys_char.py

# 제외 태그 제거
python scripts/remove_excluded_tags_char.py
```

#### lora.yml 관련
```bash
# 누락된 키 추가
python scripts/add_missing_keys_lora.py

# 제외 태그 제거
python scripts/remove_excluded_tags_lora.py
```

## 설정 파일 구조

```yaml
base_dir: W:\ComfyUI_windows_portable  # 작업 디렉토리
types:                                  # 처리할 타입 리스트
  - IL
  - Pony

char:                                   # char.yml 관련 설정
  excluded_tags: []                     # 제외할 태그 목록
  dress_tags: []                        # dress 필드로 이동할 태그 목록

lora:                                   # lora.yml 관련 설정
  max_tags: 64                          # 태그 최대 개수
  excluded_tags: []                     # 제외할 태그 목록
```

## 유틸리티 모듈

### ConfigLoader
설정 파일을 로드하고 관리합니다.

### TagProcessor
태그 처리 관련 기능을 제공합니다.
- 태그 정규화
- 제외 태그 확인
- 태그 필터링
- 태그 빈도 처리

### YAMLHandler
YAML 파일을 읽고 쓰는 기능을 제공합니다.
- 주석 보존
- 중복 키 허용 옵션

### SafeTensorsReader
SafeTensors 파일을 읽는 기능을 제공합니다.
- ss_tag_frequency 추출
- 키 추출

## 주의사항

- 스크립트 실행 전에 `config.yml` 파일을 확인하세요.
- 백업을 권장합니다.
- YAML 파일의 주석은 보존됩니다.

