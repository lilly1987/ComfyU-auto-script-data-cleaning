#!/usr/bin/env python3
"""remove_empty_output_dirs.py

재귀적으로 `W:\ComfyUI_windows_portable\output` 아래의 빈 하위 폴더를 찾아 삭제합니다.
기본 동작: 실제 삭제
옵션: --dry 를 사용하면 삭제 예정 항목만 출력합니다.
"""
import os
import sys
import argparse


def find_and_remove_empty_dirs(root: str, dry: bool = False):
    if not os.path.exists(root):
        print(f"Target folder not found: {root}")
        return 2

    removed = 0
    would = []

    # os.walk with topdown=False visits children first so parent emptiness can be detected
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # do not remove the root itself
        if os.path.abspath(dirpath) == os.path.abspath(root):
            continue

        # If directory contains no files and no subdirectories, it's empty
        if not dirnames and not filenames:
            if dry:
                would.append(dirpath)
            else:
                try:
                    os.rmdir(dirpath)
                    print(f"Removed: {dirpath}")
                    removed += 1
                except OSError as e:
                    print(f"Failed to remove {dirpath}: {e}")

    if dry:
        if would:
            print("Dry run - directories that would be removed:")
            for p in would:
                print("  ", p)
        else:
            print("Dry run - no empty directories found.")
        return 0

    print(f"Done. Removed {removed} directories.")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="Remove empty subdirectories under a target folder")
    parser.add_argument("path", nargs="?", default=r"W:\\ComfyUI_windows_portable\\output",
                        help="Target base folder (default: W:\\ComfyUI_windows_portable\\output)")
    parser.add_argument("--dry", action="store_true", help="Dry run: show directories that would be removed")
    return parser.parse_args()


def main():
    args = parse_args()
    rc = find_and_remove_empty_dirs(args.path, dry=args.dry)
    sys.exit(rc)


if __name__ == "__main__":
    main()
