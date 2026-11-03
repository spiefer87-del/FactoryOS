#!/usr/bin/env python3
"""Read-only OCR check: no Flask app/DB, photos, secrets or service changes."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from factoryos.modules.masterdata.materials.services.material_scan_service import engine_info,ScanUnavailable

def run_check():
    executable,languages=engine_info()
    print(f"OCR-Programm: {executable}")
    print(f"OCR-Sprachen: {languages}")
    original=os.environ.get("PATH")
    try:
        # Already-running Python needs no PATH. Emulates a venv-only service.
        os.environ["PATH"]=str(Path(sys.executable).parent)
        restricted,selected=engine_info()
        print(f"Prüfung mit eingeschränktem Dienst-Suchpfad: OK ({restricted}; {selected})")
    finally:
        if original is None:os.environ.pop("PATH",None)
        else:os.environ["PATH"]=original
    print("OCR-Prüfung erfolgreich. Eine zusätzliche systemd-Sandbox wird hier nicht simuliert.")

if __name__=="__main__":
    try:run_check()
    except ScanUnavailable as exc:
        print(f"OCR-Prüfung fehlgeschlagen: {exc}",file=sys.stderr)
        sys.exit(1)
