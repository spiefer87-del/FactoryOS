"""Regression: Tesseract installed but absent from a venv-only service PATH."""
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from factoryos.modules.masterdata.materials.services.material_scan_service import resolve_tesseract,engine_info,ScanUnavailable

with patch.dict(os.environ,{"PATH":"/does-not-contain-system-binaries"}):
    executable,languages=engine_info()
    assert executable in ("/usr/bin/tesseract","/usr/local/bin/tesseract","/bin/tesseract")
    assert languages
    # The actual process invocation uses the resolved absolute path too.
    response=subprocess.run([executable,"--version"],capture_output=True,text=True,timeout=5,check=True)
    assert "tesseract" in response.stdout.lower()
with patch.dict(os.environ,{"FACTORYOS_TESSERACT_CMD":"/usr/bin/tesseract"}):
    assert resolve_tesseract()=="/usr/bin/tesseract"
for invalid in ("tesseract","/not-installed/tesseract"):
    with patch.dict(os.environ,{"FACTORYOS_TESSERACT_CMD":invalid}):
        try:resolve_tesseract()
        except ScanUnavailable:pass
        else:raise AssertionError("Invalid configured executable silently ignored")
with patch.dict(os.environ,{"FACTORYOS_TESSERACT_CMD":""}),patch("factoryos.modules.masterdata.materials.services.material_scan_service.shutil.which",return_value=None),patch.object(Path,"is_file",return_value=False):
    try:resolve_tesseract()
    except ScanUnavailable as exc:assert "check_material_scan.py" in str(exc)
    else:raise AssertionError("Absent binary accepted")
print("PASS: real Tesseract probe/invocation with restricted PATH, absolute fallback, explicit configuration validation and accurate missing-binary diagnostic.")
