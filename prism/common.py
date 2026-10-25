"""Shared helpers: config loading, project paths, JSONL io."""

from __future__ import annotations

import json
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# files of a Hugging Face Qwen2.5-VL checkpoint that a manually downloaded model folder must contain
MODEL_FILES = ["config.json", "generation_config.json", "chat_template.json", "preprocessor_config.json",
               "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "model.safetensors.index.json"]


def load_config(path: str | None = None) -> dict:
    path = path or os.path.join(ROOT, "configs", "config.yaml")
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = ROOT
    local = cfg["model"].get("local_dir")
    if local:
        local = os.path.expanduser(local)
        local = local if os.path.isabs(local) else os.path.join(ROOT, local)
        if os.path.isdir(local):  # a downloaded copy is used instead of the Hub (no internet needed)
            check_model_dir(local)
            cfg["model"]["base"] = local
    return cfg


def check_model_dir(d: str) -> None:
    """Fail early, naming the missing files, if a manually downloaded model folder is incomplete."""
    missing = [f for f in MODEL_FILES if not os.path.isfile(os.path.join(d, f))]
    index = os.path.join(d, "model.safetensors.index.json")
    if os.path.isfile(index):
        with open(index) as f:
            shards = sorted(set(json.load(f)["weight_map"].values()))
        missing += [s for s in shards if not os.path.isfile(os.path.join(d, s))]
    if missing:
        raise SystemExit(f"model folder {d} is incomplete - missing: {', '.join(missing)}")


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
