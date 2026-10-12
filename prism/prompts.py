"""Prompt variants P1-P4 (zero-shot study) + the training/inference prompt (P4) + retry prompt."""

from .metrics import METRIC_KEYS

SYSTEM = ("You are a meticulous document-image quality inspector. You compare an edited RELEASE image "
          "against its ORIGINAL and score how faithfully the release preserves the original.")

RUBRIC = """Score each metric from 0.00 to 1.00 against the ORIGINAL (1.00 = indistinguishable from the original, 0.00 = completely broken):
- ocr_accuracy: are all characters identical? (typos, swapped letters/digits lower the score)
- alignment_preservation: are text blocks in the same positions?
- font_similarity: same typeface and size?
- object_preservation: logos, stamps, QR codes, photos, icons unchanged in size/position/opacity?
- background_fidelity: do edited text regions keep the original background colour?
- texture_continuity: is the paper grain/texture continuous inside edited regions?
- ghost_text_residue: is the release free of faint leftover glyphs? (1.00 = no residue)
- lighting_consistency: is illumination as uniform as the original?
- reading_flow: are line spacing and baselines unchanged?
- visual_anchor_integrity: are titles, headings, rules and borders intact?
- semantic_emphasis: do bold/coloured emphasised phrases keep their styling?
- authenticity: is the release free of compression/noise/synthetic artifacts?"""

KEYS_LINE = ", ".join(METRIC_KEYS)
JSON_SPEC = ('Return the JSON object with exactly these 12 keys and numbers between 0 and 1 (two decimals): '
             + KEYS_LINE + ".")

PROMPTS = {
    "P1": "The first image is the ORIGINAL, the second is an edited RELEASE. Rate the release on each of these "
          f"metrics from 0 to 1: {KEYS_LINE}. Answer with a JSON object.",
    "P2": RUBRIC + "\n\nThe first image is the ORIGINAL and the second is the RELEASE. " + JSON_SPEC,
    "P3": RUBRIC + "\n\nCompare the RELEASE strictly against the ORIGINAL. Output ONLY a single JSON object, no "
          "other text. " + JSON_SPEC,
    "P4": RUBRIC + "\n\nCompare the RELEASE strictly against the ORIGINAL. First write <analysis> with exactly one "
          "line per metric in the order above, in the form '- <observation> -> <score>', then close </analysis>. "
          "Then output ONLY the JSON object. " + JSON_SPEC,
}
TRAIN_PROMPT = "P4"

RETRY = ("Your previous answer could not be parsed. Output ONLY one JSON object with exactly these 12 keys and "
         "numeric values between 0 and 1: " + KEYS_LINE + ". No other text.")


def build_messages(original_path: str, release_path: str, prompt: str, target: str | None = None,
                   min_pixels: int | None = None, max_pixels: int | None = None):
    img = {}
    if min_pixels:
        img["min_pixels"] = min_pixels
    if max_pixels:
        img["max_pixels"] = max_pixels
    msgs = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
        {"role": "user", "content": [
            {"type": "text", "text": "ORIGINAL:"},
            {"type": "image", "image": original_path, **img},
            {"type": "text", "text": "RELEASE:"},
            {"type": "image", "image": release_path, **img},
            {"type": "text", "text": prompt},
        ]},
    ]
    if target is not None:
        msgs.append({"role": "assistant", "content": [{"type": "text", "text": target}]})
    return msgs
