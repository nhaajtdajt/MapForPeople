"""Quy tắc chọn bản thật hay bản giả của `ports` (spec 01, mục 2.2)."""
import importlib
import sys
import textwrap

import pytest

from floodrisk.api import fakes, ports


def _reload_with(monkeypatch, fake_import):
    monkeypatch.setattr(importlib, "import_module", fake_import)
    ports._status.clear()
    ports._objects.clear()
    for part in ports.PARTS:
        ports._load(part)


@pytest.fixture(autouse=True)
def restore_ports():
    yield
    ports._status.clear()
    ports._objects.clear()
    for part in ports.PARTS:
        ports._load(part)


def test_missing_floodrisk_module_falls_back_to_fake(monkeypatch):
    def missing(name, *args, **kwargs):
        raise ModuleNotFoundError(f"No module named '{name}'", name=name)

    _reload_with(monkeypatch, missing)
    assert ports.status() == {"risk": "real", "evidence": "fake", "scenarios": "fake"}
    assert ports._objects["apply_evidence"] is fakes.apply_evidence
    assert ports._objects["make_synthetic"] is fakes.make_synthetic


def test_missing_third_party_library_is_not_hidden(monkeypatch):
    def broken(name, *args, **kwargs):
        raise ModuleNotFoundError("No module named 'lightgbm'", name="lightgbm")

    with pytest.raises(ModuleNotFoundError, match="lightgbm"):
        _reload_with(monkeypatch, broken)


def test_syntax_error_in_real_module_stops_the_server(monkeypatch):
    def broken(name, *args, **kwargs):
        raise SyntaxError("lỗi cú pháp trong module thật")

    with pytest.raises(SyntaxError):
        _reload_with(monkeypatch, broken)


def test_real_module_missing_a_contract_name_is_reported(monkeypatch):
    class Empty:
        pass

    with pytest.raises(RuntimeError, match="thiếu"):
        _reload_with(monkeypatch, lambda name, *a, **k: Empty())


def test_real_module_is_used_when_present(monkeypatch, tmp_path):
    module = tmp_path / "evidence_probe.py"
    module.write_text(textwrap.dedent("""
        from dataclasses import dataclass
        @dataclass(frozen=True)
        class Report: pass
        @dataclass(frozen=True)
        class EvidenceResult: pass
        def apply_evidence(prior, reports, now): return "thật"
    """), encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    real_import = importlib.import_module

    def only_evidence(name, *args, **kwargs):
        if name == "floodrisk.model.evidence":
            return real_import("evidence_probe")
        raise ModuleNotFoundError(f"No module named '{name}'", name=name)

    _reload_with(monkeypatch, only_evidence)
    assert ports.status()["evidence"] == "real" and ports.status()["scenarios"] == "fake"
    # tên công khai của `ports` được gán một lần lúc nhập module; ở đây kiểm cái mà `_load` đã chọn
    assert ports._objects["apply_evidence"](0, [], None) == "thật"
    sys.modules.pop("evidence_probe", None)
