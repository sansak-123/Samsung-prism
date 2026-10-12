"""Shared helpers: config loading, project paths, JSONL io."""

from __future__ import annotations

import json
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path: str | None = None) -> dict:
    path = path or os.path.join(ROOT, "configs", "config.yaml")
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = ROOT
    return cfg


def P(cfg, key, *parts) -> str:
    """Absolute path for a configured directory (+ optional sub-parts)."""
    return os.path.join(ROOT, cfg["paths"][key], *parts)


def abspath(rel: str) -> str:
    rel = rel.replace("\\", "/")  # metadata written on Windows may hold backslashes
    return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(ROOT, rel))


def read_jsonl(path: str) -> list:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(path: str, rows) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
