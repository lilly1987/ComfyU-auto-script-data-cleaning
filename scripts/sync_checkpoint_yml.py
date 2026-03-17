# -*- coding: utf-8 -*-
"""
checkpoint.yml 동기화 통합 스크립트.

현재 역할:
1. models/checkpoints/<type> 기준으로 누락된 checkpoint 키 추가
2. safetensors 메타데이터에서 prompt/workflow 를 읽어
   - negative.checkpoint
   - negative.quality
   - positive.checkpoint
   - positive.quality
   - positive.anime
   - steps / cfg / sampler_name
   을 자동 채움
3. 메타데이터가 없으면 새 항목의 positive/negative 블록은 주석 형태로 추가
4. 기존 항목의 기본 구조 보정
"""
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from safetensors import safe_open


script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils import ConfigLoader, TagProcessor, YAMLHandler


DEFAULT_SKIP = False
DEFAULT_WEIGHT = 3
DEFAULT_FAVORITES = 1
DEFAULT_STEPS = [30]
DEFAULT_CFG = [4.0]
DEFAULT_SAMPLER = ["euler_ancestral"]

POSITIVE_QUALITY_HINTS = {
    "masterpiece",
    "best quality",
    "high quality",
    "amazing quality",
    "very aesthetic",
    "aesthetic",
    "absurdres",
    "highres",
    "hi res",
    "ultra detailed",
    "extremely detailed",
    "highly detailed",
    "detailed",
    "newest",
    "official art",
    "official style",
}

NEGATIVE_QUALITY_HINTS = {
    "worst quality",
    "low quality",
    "normal quality",
    "bad quality",
    "lowres",
    "blurry",
    "out of focus",
    "jpeg artifacts",
    "compression artifacts",
    "bad anatomy",
    "bad proportions",
    "bad hands",
    "deformed",
    "mutated",
    "ugly",
}

ANIME_HINTS = {
    "anime",
    "anime screencap",
    "anime coloring",
    "2d",
    "cel shading",
    "official art",
    "official style",
}


def configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def get_checkpoint_file_map(checkpoint_dir: str) -> Dict[str, str]:
    if not os.path.exists(checkpoint_dir):
        return {}

    file_map: Dict[str, str] = {}
    for filename in os.listdir(checkpoint_dir):
        if filename.endswith(".safetensors"):
            file_map[filename[:-len(".safetensors")]] = os.path.join(checkpoint_dir, filename)
    return dict(sorted(file_map.items()))


def split_prompt_tags(text: str) -> List[str]:
    if not text:
        return []

    normalized_text = text.replace("\r", "\n").replace("\n", ",")
    tags = [part.strip() for part in normalized_text.split(",") if part.strip()]
    return tags


def join_tags(tags: List[str], fallback: str = "") -> str:
    tags = [tag for tag in tags if tag and tag.strip()]
    if not tags:
        return fallback
    return ", ".join(tags)


def is_positive_quality_tag(tag: str) -> bool:
    normalized = TagProcessor.normalize_tag(tag)
    return normalized in POSITIVE_QUALITY_HINTS or "quality" in normalized or normalized in {"absurdres", "highres", "hi res", "newest"}


def is_negative_quality_tag(tag: str) -> bool:
    normalized = TagProcessor.normalize_tag(tag)
    return normalized in NEGATIVE_QUALITY_HINTS or "quality" in normalized or normalized in {"lowres", "blurry"}


def is_anime_tag(tag: str) -> bool:
    normalized = TagProcessor.normalize_tag(tag)
    return normalized in ANIME_HINTS


def split_positive_prompt(text: str) -> Dict[str, str]:
    checkpoint_tags: List[str] = []
    quality_tags: List[str] = []
    anime_tags: List[str] = []

    for tag in split_prompt_tags(text):
        if is_anime_tag(tag):
            anime_tags.append(tag)
            continue
        if is_positive_quality_tag(tag):
            quality_tags.append(tag)
            continue
        checkpoint_tags.append(tag)

    return {
        "checkpoint": join_tags(checkpoint_tags, " "),
        "quality": join_tags(quality_tags, " "),
        "anime": join_tags(anime_tags, ""),
    }


def split_negative_prompt(text: str) -> Dict[str, str]:
    checkpoint_tags: List[str] = []
    quality_tags: List[str] = []

    for tag in split_prompt_tags(text):
        if is_negative_quality_tag(tag):
            quality_tags.append(tag)
            continue
        checkpoint_tags.append(tag)

    return {
        "checkpoint": join_tags(checkpoint_tags, "  "),
        "quality": join_tags(quality_tags, " ,"),
    }


def extract_prompts_from_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    positive_candidates: List[str] = []
    negative_candidates: List[str] = []

    for node in workflow.get("nodes", []):
        node_type = str(node.get("type", ""))
        values = node.get("widgets_values", []) or []

        if node_type == "CheckpointLoaderSimple" and values:
            result["source_checkpoint"] = os.path.splitext(str(values[0]))[0]

        if node_type == "KSampler" and len(values) >= 5:
            result["steps"] = [values[2]]
            result["cfg"] = [values[3]]
            result["sampler_name"] = [values[4]]

        if node_type == "CLIPTextEncode" and values and isinstance(values[0], str):
            text = values[0].strip()
            if not text:
                continue

            normalized = TagProcessor.normalize_tag(text)
            if any(hint in normalized for hint in ("worst quality", "low quality", "bad anatomy", "negative")):
                negative_candidates.append(text)
            else:
                positive_candidates.append(text)

    if positive_candidates:
        result["positive_prompt"] = max(positive_candidates, key=len)
    if negative_candidates:
        result["negative_prompt"] = max(negative_candidates, key=len)

    return result


def extract_prompts_from_prompt_json(prompt_json: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    for node in prompt_json.values():
        if not isinstance(node, dict):
            continue

        node_type = str(node.get("class_type", ""))
        inputs = node.get("inputs", {}) or {}

        if node_type == "CheckpointLoaderSimple":
            ckpt_name = inputs.get("ckpt_name")
            if ckpt_name:
                result["source_checkpoint"] = os.path.splitext(str(ckpt_name))[0]

    return result


def extract_metadata_from_file(file_path: str) -> Dict[str, Any]:
    metadata_result: Dict[str, Any] = {}

    try:
        with safe_open(file_path, framework="pt") as f:
            metadata = f.metadata() or {}
    except Exception:
        return metadata_result

    prompt_raw = metadata.get("prompt")
    workflow_raw = metadata.get("workflow")

    if workflow_raw:
        try:
            workflow_data = json.loads(workflow_raw)
            metadata_result.update(extract_prompts_from_workflow(workflow_data))
        except Exception:
            pass

    if prompt_raw:
        try:
            prompt_data = json.loads(prompt_raw)
            for key, value in extract_prompts_from_prompt_json(prompt_data).items():
                metadata_result.setdefault(key, value)
        except Exception:
            pass

    if metadata_result.get("positive_prompt"):
        metadata_result["positive"] = split_positive_prompt(metadata_result["positive_prompt"])
    if metadata_result.get("negative_prompt"):
        metadata_result["negative"] = split_negative_prompt(metadata_result["negative_prompt"])

    return metadata_result


def ensure_scalar(parent: Dict[str, Any], key: str, default: Any) -> bool:
    if key in parent:
        return False
    parent[key] = default
    return True


def ensure_list(parent: Dict[str, Any], key: str, default: List[Any]) -> bool:
    value = parent.get(key)
    if isinstance(value, list) and value:
        return False
    parent[key] = list(default)
    return True


def ensure_mapping(parent: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        parent[key] = {}
    return parent[key]


def is_placeholder_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    return normalized in {"", ",", " ,"}


def apply_metadata_to_entry(entry: Dict[str, Any], metadata: Dict[str, Any]) -> int:
    changes = 0

    if metadata.get("steps"):
        changes += int(ensure_list(entry, "steps", metadata["steps"]))
    else:
        changes += int(ensure_list(entry, "steps", DEFAULT_STEPS))

    if metadata.get("cfg"):
        changes += int(ensure_list(entry, "cfg", metadata["cfg"]))
    else:
        changes += int(ensure_list(entry, "cfg", DEFAULT_CFG))

    if metadata.get("sampler_name"):
        changes += int(ensure_list(entry, "sampler_name", metadata["sampler_name"]))
    else:
        changes += int(ensure_list(entry, "sampler_name", DEFAULT_SAMPLER))

    has_prompt_metadata = bool(metadata.get("positive") or metadata.get("negative"))
    if not has_prompt_metadata:
        return changes

    negative = ensure_mapping(entry, "negative")
    negative_meta = metadata.get("negative", {})
    if negative_meta:
        if "checkpoint" not in negative or is_placeholder_text(negative.get("checkpoint")):
            negative["checkpoint"] = negative_meta.get("checkpoint", "  ")
            changes += 1
        if "quality" not in negative or is_placeholder_text(negative.get("quality")):
            negative["quality"] = negative_meta.get("quality", " ,")
            changes += 1

    positive = ensure_mapping(entry, "positive")
    positive_meta = metadata.get("positive", {})
    if positive_meta:
        if "checkpoint" not in positive or is_placeholder_text(positive.get("checkpoint")):
            positive["checkpoint"] = positive_meta.get("checkpoint", " ")
            changes += 1
        if "quality" not in positive or is_placeholder_text(positive.get("quality")):
            positive["quality"] = positive_meta.get("quality", " ")
            changes += 1
        if "anime" not in positive or is_placeholder_text(positive.get("anime")):
            positive["anime"] = positive_meta.get("anime", "")
            changes += 1

    return changes


def normalize_entry(entry: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> int:
    changes = 0
    metadata = metadata or {}

    changes += int(ensure_scalar(entry, "skip", DEFAULT_SKIP))
    changes += int(ensure_scalar(entry, "weight", DEFAULT_WEIGHT))
    changes += int(ensure_scalar(entry, "favorites", DEFAULT_FAVORITES))
    changes += apply_metadata_to_entry(entry, metadata)
    return changes


def render_new_entry_text(key: str, metadata: Dict[str, Any]) -> str:
    lines = [
        f"'{key}':",
        f"  skip: {str(DEFAULT_SKIP).lower()}",
        f"  weight: {DEFAULT_WEIGHT}",
        f"  favorites: {DEFAULT_FAVORITES}",
    ]

    steps = metadata.get("steps") or DEFAULT_STEPS
    cfg = metadata.get("cfg") or DEFAULT_CFG
    sampler = metadata.get("sampler_name") or DEFAULT_SAMPLER

    lines.append("  steps:")
    for item in steps:
        lines.append(f"  - {item}")

    lines.append("  cfg:")
    for item in cfg:
        lines.append(f"  - {item}")

    negative_meta = metadata.get("negative")
    positive_meta = metadata.get("positive")

    if negative_meta:
        negative_checkpoint = negative_meta.get("checkpoint", "  ").replace("'", "''")
        negative_quality = negative_meta.get("quality", " ,").replace("'", "''")
        lines.append("  negative:")
        lines.append(f"    checkpoint: '{negative_checkpoint}'")
        lines.append(f"    quality: '{negative_quality}'")
    else:
        lines.append("  #negative:")
        lines.append("    #checkpoint: '  '")
        lines.append("    #quality: ' ,'")

    if positive_meta:
        positive_checkpoint = positive_meta.get("checkpoint", " ").replace("'", "''")
        positive_quality = positive_meta.get("quality", " ").replace("'", "''")
        positive_anime = positive_meta.get("anime", "").replace("'", "''")
        lines.append("  positive:")
        lines.append(f"    checkpoint: '{positive_checkpoint}'")
        lines.append(f"    quality: '{positive_quality}'")
        lines.append(f"    anime: '{positive_anime}'")
    else:
        lines.append("  #positive:")
        lines.append("    #checkpoint: ' '")
        lines.append("    #quality: ' '")
        lines.append("    #anime: ''")

    lines.append("  sampler_name:")
    for item in sampler:
        lines.append(f"  - {item}")
    lines.append("")

    return "\n".join(lines) + "\n"


def append_missing_entries(
    yml_path: str,
    missing_keys: List[str],
    file_map: Dict[str, str],
    metadata_cache: Dict[str, Dict[str, Any]],
    dry_run: bool = False,
) -> int:
    if not missing_keys:
        return 0

    if dry_run:
        for key in missing_keys:
            state = "메타 있음" if metadata_cache.get(key) else "메타 없음"
            print(f"    + 추가 예정: {key} ({state})")
        return len(missing_keys)

    with open(yml_path, "a", encoding="utf-8") as f:
        for key in missing_keys:
            text = render_new_entry_text(key, metadata_cache.get(key, {}))
            f.write(text)

    return len(missing_keys)


def sync_type(
    type_name: str,
    comfui_dir: str,
    data_dir: str,
    yaml_handler: YAMLHandler,
    dry_run: bool = False,
) -> Tuple[int, int]:
    print(f"\n{'=' * 80}")
    print(f"[{type_name}] 처리 시작")
    print(f"{'=' * 80}")

    yml_path = os.path.join(data_dir, type_name, "checkpoint", "checkpoint.yml")
    checkpoint_dir = os.path.join(comfui_dir, "models", "checkpoints", type_name)

    if not os.path.exists(yml_path):
        print(f"  경고: checkpoint.yml 이 없습니다: {yml_path}")
        return 0, 0

    if not os.path.exists(checkpoint_dir):
        print(f"  경고: checkpoint 폴더가 없습니다: {checkpoint_dir}")
        return 0, 0

    yml_data = yaml_handler.load(yml_path)
    if yml_data is None:
        print("  오류: checkpoint.yml 로드 실패")
        return 0, 0

    file_map = get_checkpoint_file_map(checkpoint_dir)
    existing_keys = {key for key in yml_data.keys() if key}
    missing_keys = [key for key in file_map.keys() if key not in existing_keys]
    metadata_cache = {key: extract_metadata_from_file(path) for key, path in file_map.items()}

    print(f"  checkpoint 파일: {len(file_map)}개")
    print(f"  yml 키: {len(existing_keys)}개")
    print(f"  누락 키: {len(missing_keys)}개")

    added_count = append_missing_entries(
        yml_path=yml_path,
        missing_keys=missing_keys,
        file_map=file_map,
        metadata_cache=metadata_cache,
        dry_run=dry_run,
    )

    if added_count > 0 and not dry_run:
        yml_data = yaml_handler.load(yml_path)
        if yml_data is None:
            print("  오류: 추가 후 checkpoint.yml 재로드 실패")
            return added_count, 0

    normalized_count = 0
    for key, value in yml_data.items():
        if not isinstance(value, dict):
            continue

        metadata = metadata_cache.get(str(key), {})
        changes = normalize_entry(value, metadata)
        if changes > 0:
            normalized_count += 1
            print(f"    * 구조/메타 보정: {key}")

    if not dry_run and (added_count > 0 or normalized_count > 0):
        if yaml_handler.save(yml_path, yml_data):
            print(f"  [OK] 저장 완료: {yml_path}")
        else:
            print(f"  [ERROR] 저장 실패: {yml_path}")

    if added_count == 0 and normalized_count == 0:
        print("  [OK] 변경할 항목이 없습니다.")
    else:
        print(f"  추가 키: {added_count}개")
        print(f"  구조/메타 보정: {normalized_count}개")
        if dry_run:
            print("  dry-run 이므로 저장하지 않았습니다.")

    return added_count, normalized_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="checkpoint.yml 누락 키 추가와 메타 기반 자동 채우기를 한 번에 수행합니다."
    )
    parser.add_argument(
        "--type",
        dest="type_names",
        action="append",
        help="처리할 타입명. 여러 번 지정 가능. 미지정 시 config.yml 의 types 전체 처리",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파일 저장 없이 변경 예정만 출력",
    )
    return parser.parse_args()


def main() -> int:
    configure_console_encoding()
    args = parse_args()
    config = ConfigLoader()
    yaml_handler = YAMLHandler(allow_duplicate_keys=True)

    comfui_dir = config.get_comfui_dir()
    data_dir = config.get_data_dir()
    type_names = args.type_names or config.get_types()

    print("=" * 80)
    print("checkpoint.yml 통합 동기화")
    print("=" * 80)
    print(f"처리 타입: {', '.join(type_names)}")
    if args.dry_run:
        print("모드: dry-run")

    total_added = 0
    total_normalized = 0

    for type_name in type_names:
        added_count, normalized_count = sync_type(
            type_name=type_name,
            comfui_dir=comfui_dir,
            data_dir=data_dir,
            yaml_handler=yaml_handler,
            dry_run=args.dry_run,
        )
        total_added += added_count
        total_normalized += normalized_count

    print(f"\n{'=' * 80}")
    print("완료")
    print(f"{'=' * 80}")
    print(f"추가 키: {total_added}개")
    print(f"구조/메타 보정: {total_normalized}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
