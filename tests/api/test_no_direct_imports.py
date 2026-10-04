"""Chỉ `ports.py` được nhập mã của người dữ liệu và người AI (spec 01, mục 2.2)."""
import re
from pathlib import Path

API = Path(__file__).resolve().parents[2] / "src" / "floodrisk" / "api"
FORBIDDEN = re.compile(r"^\s*(?:from|import)\s+floodrisk\.(?:model|data|jobs)\b", re.MULTILINE)


def test_only_ports_imports_other_peoples_code():
    offenders = [p.name for p in API.glob("*.py") if p.name != "ports.py" and FORBIDDEN.search(p.read_text(encoding="utf-8"))]
    assert offenders == []
