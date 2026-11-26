"""Capture clean flagship scenes only; no speech service, no publishing."""
import json,zipfile
from pathlib import Path
from cryptography.hazmat.primitives import serialization
import flagship_review_v114 as f
import private_review_v113 as base
import private_review_v111 as encryption
import creative_intelligence_v10 as v
ROOT=Path("private-preview-v115")
SEALED=Path("sealed-review-v115")
original=f.clean_public
def clean(page):
    original(page)
    page.add_style_tag(content="#dl-stats-consent{display:none!important;visibility:hidden!important;pointer-events:none!important}")
    assert not page.locator("#dl-stats-consent").is_visible()
f.clean_public=clean
def main():
    ROOT.mkdir(exist_ok=False)
    f.capture(v,ROOT)
    zpath=ROOT/"shots.zip"
    with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as z:
        for i in range(20):z.write(ROOT/f"shot-{i:02d}.png",f"shot-{i:02d}.png")
        z.write(ROOT/"capture_report.json","capture_report.json")
    SEALED.mkdir(exist_ok=True)
    pub=serialization.load_pem_public_key(base.PUBLIC_KEY)
    (SEALED/"Darkline_V115_clean_capture.dlenc").write_bytes(encryption.seal(zpath.read_bytes(),pub))
    print("V115_CAPTURE_READY 20 consent-free shots; no voice API called; no publishing",flush=True)
if __name__=="__main__":main()
