import json
import os

import numpy as np
from PIL import Image

import build_event_rasters as ber

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(HERE, "..", "annual", "events")
MANIFEST = os.path.join(HERE, "..", "annual", "manifest.json")

EXPECTED_KEYS = {"seasia", "med", "waus", "blob", "spac", "mad", "gbr", "natl", "catl"}


def test_build_writes_nine_pngs_and_merges_manifest():
    # baseline manifest keys that must survive the merge
    with open(MANIFEST) as f:
        before = json.load(f)
    assert "total" in before and "years" in before, "run build_annual_rasters.py first"

    ber.build()

    # 9 PNGs, one per key, all non-empty
    for key in EXPECTED_KEYS:
        p = os.path.join(EVENTS_DIR, f"{key}.png")
        assert os.path.exists(p), f"missing {p}"
        assert os.path.getsize(p) > 0, f"empty {p}"

    # manifest still has the annual fields AND a complete events block
    with open(MANIFEST) as f:
        after = json.load(f)
    assert after["total"] == before["total"]
    assert after["years"] == before["years"]
    assert set(after["events"].keys()) == EXPECTED_KEYS
    for key in EXPECTED_KEYS:
        assert after["events"][key] == f"events/{key}.png"


def test_ocean_outside_footprint_is_transparent():
    ber.build()
    # top-left corner pixel (far from any footprint) must be fully transparent
    im = Image.open(os.path.join(EVENTS_DIR, "blob.png")).convert("RGBA")
    alpha = np.asarray(im)[..., 3]
    assert alpha[0, 0] == 0, "corner pixel should be transparent (mask==0 -> NaN)"
    assert (alpha > 0).any(), "footprint should color at least some pixels"
