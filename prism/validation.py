"""Validation gate: JSON schema constraint + numeric range verification on raw VLM output."""

from __future__ import annotations

import json
import re

from .metrics import METRIC_KEYS, METRIC_NAMES

_ALIASES = {}
for k in METRIC_KEYS:
    _ALIASES[k] = k
    _ALIASES[METRIC_NAMES[k].lower().replace(" ", "_")] = k
    _ALIASES[METRIC_NAMES[k].lower()] = k
    _ALIASES[k.replace("_", "")] = k


def _json_candidates(text: str):
    """Yield every balanced {...} substring, last one first."""
    spans, stack = [], []
    for i, ch in enumerate(text):
        if ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            start = stack.pop()
            if not stack:
                spans.append((start, i + 1))
    for s, e in reversed(spans):
        yield text[s:e]


def validate_output(text: str):
    """Return (scores | None, errors). scores has exactly the 12 metric keys as floats in [0, 1]."""
    errors = []
    if not text or "{" not in text:
        return None, ["no_json_object"]
    for cand in _json_candidates(text):
        cleaned = re.sub(r",\s*}", "}", cand.replace("'", '"'))
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError:
            errors.append("json_decode_error")
            continue
        if not isinstance(obj, dict):
            errors.append("not_an_object")
            continue
        scores, errs = {}, []
        for raw_k, v in obj.items():
            k = _ALIASES.get(str(raw_k).strip().lower())
            if k is None:
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                errs.append(f"non_numeric:{k}")
                continue
            if not (0.0 <= fv <= 1.0):
                errs.append(f"out_of_range:{k}={fv}")
                continue
            scores[k] = round(fv, 4)
        missing = [k for k in METRIC_KEYS if k not in scores]
        if missing:
            errs.append("missing:" + ",".join(missing))
        if not errs:
            return scores, []
        errors.extend(errs)
    return None, errors or ["no_valid_object"]
