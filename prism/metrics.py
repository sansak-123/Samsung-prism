"""The 12 frozen PRISM metrics, their categories, and the physical range each one controls.

Convention used everywhere in this project:
    severity s in [0, 1]   -> how strongly an artifact was applied
    score      = 1 - s     -> ground-truth metric score (1.0 = identical to the Original)

Every release image is rendered from a *pre-defined* target score per metric
(Mimat's approach): the renderer turns the target into a physical change, then
measures what was actually realised. The realised value is stored as ground truth.
"""

METRICS = [
    # key                       display name                category
    ("ocr_accuracy",            "OCR Accuracy",             "technical"),
    ("alignment_preservation",  "Alignment Preservation",   "technical"),
    ("font_similarity",         "Font Similarity",          "technical"),
    ("object_preservation",     "Object Preservation",      "technical"),
    ("background_fidelity",     "Background Fidelity",      "visual"),
    ("texture_continuity",      "Texture Continuity",       "visual"),
    ("ghost_text_residue",      "Ghost Text Residue",       "visual"),
    ("lighting_consistency",    "Lighting Consistency",     "visual"),
    ("reading_flow",            "Reading Flow",             "human_perception"),
    ("visual_anchor_integrity", "Visual Anchor Integrity",  "human_perception"),
    ("semantic_emphasis",       "Semantic Emphasis",        "human_perception"),
    ("authenticity",            "Authenticity",             "human_perception"),
]

METRIC_KEYS = [m[0] for m in METRICS]
METRIC_NAMES = {m[0]: m[1] for m in METRICS}
METRIC_CATEGORY = {m[0]: m[2] for m in METRICS}
CATEGORIES = ["technical", "visual", "human_perception"]
CATEGORY_NAMES = {"technical": "Technical", "visual": "Visual", "human_perception": "Human Perception"}
CATEGORY_METRICS = {c: [k for k in METRIC_KEYS if METRIC_CATEGORY[k] == c] for c in CATEGORIES}

# Physical ranges: severity 1.0 maps to these maxima (severity scales linearly).
PHYS = {
    "ocr_max_cer": 0.25,          # 25% of characters substituted
    "align_max_dx": 40.0,         # px horizontal displacement of text blocks
    "align_max_dy": 12.0,         # px vertical displacement
    "font_max_size_delta": 0.35,  # +-35% font size
    "font_w_size": 0.6,           # font severity = 0.6*size_term + 0.4*family_term
    "font_w_family": 0.4,
    "font_w_weight": 0.2,         # ladder only: regular -> bold weight change of a whole block
    "font_w_color": 0.6,          # ladder only: text colour change, scaled by dE2000 / font_color_max_de
    "font_color_max_de": 25.0,
    "obj_max_scale_loss": 0.40,   # objects shrink up to 40%
    "obj_max_shift": 30.0,        # px
    "obj_max_fade": 0.70,         # opacity loss
    "bg_max_delta_e": 25.0,       # CIEDE2000 of inpainted patch vs true background
    "tex_max_sigma": 6.0,         # blur search range used to hit texture-loss targets
    "ghost_max_alpha": 0.45,      # opacity of residual original glyphs
    "light_max_drop": 0.45,       # brightness drop at the dark end of the gradient
    "flow_max_spacing": 0.60,     # +-60% line spacing change
    "flow_max_jitter": 0.15,      # baseline jitter as a fraction of line height
    "anchor_max_shrink": 0.35,    # headings shrink up to 35%
    "anchor_max_shift": 25.0,     # headings shift up to 25px
    "auth_jpeg_q_max": 95,        # JPEG quality at severity 0
    "auth_jpeg_q_min": 20,        # JPEG quality at severity 1
    "auth_max_noise": 6.0,        # gaussian noise std inside edited patches
}

QUALITY_BANDS = [  # used for band-classification accuracy
    ("excellent", 0.90, 1.01),
    ("good", 0.75, 0.90),
    ("fair", 0.50, 0.75),
    ("poor", -0.01, 0.50),
]


def band_of(score: float) -> str:
    for name, lo, hi in QUALITY_BANDS:
        if lo <= score < hi:
            return name
    return "poor"
