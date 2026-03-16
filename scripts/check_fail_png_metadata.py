# -*- coding: utf-8 -*-
"""
Read PNG metadata from files inside W:\\fail.
"""
from __future__ import annotations

import json
import sqlite3
import struct
import sys
import zlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TARGET_DIR = Path(r"W:\fail")
DB_PATH = Path(__file__).resolve().parent.parent / "error.db"


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _parse_text_chunk(chunk_type: bytes, data: bytes) -> tuple[str, str]:
    if chunk_type == b"tEXt":
        keyword, text = data.split(b"\x00", 1)
        return _decode_text(keyword), _decode_text(text)

    if chunk_type == b"zTXt":
        keyword, rest = data.split(b"\x00", 1)
        compression_method = rest[0]
        compressed_text = rest[1:]
        if compression_method != 0:
            raise ValueError(f"Unsupported zTXt compression method: {compression_method}")
        text = zlib.decompress(compressed_text)
        return _decode_text(keyword), _decode_text(text)

    if chunk_type == b"iTXt":
        keyword, rest = data.split(b"\x00", 1)
        compression_flag = rest[0]
        compression_method = rest[1]
        rest = rest[2:]

        _, rest = rest.split(b"\x00", 1)  # language tag
        _, text = rest.split(b"\x00", 1)  # translated keyword

        if compression_flag:
            if compression_method != 0:
                raise ValueError(f"Unsupported iTXt compression method: {compression_method}")
            text = zlib.decompress(text)

        return _decode_text(keyword), _decode_text(text)

    raise ValueError(f"Unsupported chunk type: {chunk_type!r}")


def read_png_metadata(file_path: Path) -> Dict[str, List[str]]:
    metadata: Dict[str, List[str]] = {}

    with file_path.open("rb") as handle:
        signature = handle.read(len(PNG_SIGNATURE))
        if signature != PNG_SIGNATURE:
            raise ValueError("Not a valid PNG file")

        while True:
            raw_length = handle.read(4)
            if not raw_length:
                break
            if len(raw_length) != 4:
                raise ValueError("Unexpected end of file while reading chunk length")

            length = struct.unpack(">I", raw_length)[0]
            chunk_type = handle.read(4)
            chunk_data = handle.read(length)
            handle.read(4)  # CRC

            if len(chunk_type) != 4 or len(chunk_data) != length:
                raise ValueError("Unexpected end of file while reading chunk data")

            if chunk_type in {b"tEXt", b"zTXt", b"iTXt"}:
                key, value = _parse_text_chunk(chunk_type, chunk_data)
                metadata.setdefault(key, []).append(value)

            if chunk_type == b"IEND":
                break

    return metadata


def ensure_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS LoraLoader (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lora_key TEXT NOT NULL,
            strength_model REAL,
            strength_clip REAL,
            A REAL,
            B REAL,
            block_vector TEXT,
            recorded_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def get_table_columns(connection: sqlite3.Connection, table_name: str) -> List[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def extract_lora_records(file_path: Path, metadata: Dict[str, List[str]]) -> List[Dict[str, object]]:
    prompt_values = metadata.get("prompt", [])
    if not prompt_values:
        return []

    prompt_data = json.loads(prompt_values[0])
    recorded_at = datetime.now().isoformat(timespec="seconds")
    records: List[Dict[str, object]] = []

    for node_key, node_value in sorted(prompt_data.items()):
        if not node_key.startswith("LoraLoader"):
            continue

        inputs = node_value.get("inputs", {})
        lora_name = inputs.get("lora_name")
        if not lora_name:
            continue

        lora_key = Path(str(lora_name)).stem
        records.append(
            {
                "png_file": file_path.name,
                "lora_key": lora_key,
                "lora_name": lora_name,
                "strength_model": inputs.get("strength_model"),
                "strength_clip": inputs.get("strength_clip"),
                "A": inputs.get("A"),
                "B": inputs.get("B"),
                "block_vector": inputs.get("block_vector"),
                "recorded_at": recorded_at,
            }
        )

    return records


def insert_lora_records(connection: sqlite3.Connection, records: List[Dict[str, object]]) -> None:
    if not records:
        return

    table_columns = get_table_columns(connection, "LoraLoader")
    insert_columns = [
        column
        for column in (
            "png_file",
            "lora_key",
            "lora_name",
            "strength_model",
            "strength_clip",
            "A",
            "B",
            "block_vector",
            "recorded_at",
        )
        if column in table_columns
    ]
    column_sql = ",\n            ".join(insert_columns)
    value_sql = ",\n            ".join(f":{column}" for column in insert_columns)

    connection.executemany(
        f"""
        INSERT INTO LoraLoader (
            {column_sql}
        ) VALUES (
            {value_sql}
        )
        """,
        records,
    )
    connection.commit()


def main() -> int:
    if not TARGET_DIR.exists():
        print(f"[ERROR] Folder not found: {TARGET_DIR}")
        return 1

    png_files = sorted(TARGET_DIR.glob("*.png"))
    print("=" * 80)
    print(f"PNG metadata scan: {TARGET_DIR}")
    print(f"PNG files found: {len(png_files)}")
    print("=" * 80)

    if not png_files:
        print("No PNG files found.")
        return 0

    error_count = 0
    total_lora_records = 0

    connection = sqlite3.connect(DB_PATH)
    ensure_database(connection)

    try:
        for index, file_path in enumerate(png_files, start=1):
            print()
            print("-" * 80)
            print(f"[{index}/{len(png_files)}] {file_path.name}")
            print("-" * 80)

            try:
                metadata = read_png_metadata(file_path)
            except Exception as exc:
                error_count += 1
                print(f"[ERROR] Failed to read metadata: {exc}")
                continue

            if not metadata:
                print("No PNG text metadata found.")
                continue

            for key, values in metadata.items():
                for value_index, value in enumerate(values, start=1):
                    suffix = f" #{value_index}" if len(values) > 1 else ""
                    print(f"[{key}{suffix}]")
                    print(value)
                    print()

            try:
                lora_records = extract_lora_records(file_path, metadata)
                insert_lora_records(connection, lora_records)
                total_lora_records += len(lora_records)
                print(f"LoraLoader rows inserted: {len(lora_records)}")
            except Exception as exc:
                error_count += 1
                print(f"[ERROR] Failed to write LoraLoader history: {exc}")
    finally:
        connection.close()

    print("=" * 80)
    print(f"Done. Errors: {error_count}, LoraLoader rows inserted: {total_lora_records}")
    print(f"Database: {DB_PATH}")
    print("=" * 80)
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
