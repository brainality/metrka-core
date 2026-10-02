from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from metrka_core.quality.checks.xlsx import xlsx_package_integrity
from metrka_core.quality.models import QualityCheckInput, QualityGate
from metrka_core.quality.registry import create_default_quality_registry

VALID_MEMBERS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/worksheets/sheet1.xml",
}


def _write_package(path: Path) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        for member in VALID_MEMBERS:
            archive.writestr(member, b"<xml />")


def _check_input(path: Path) -> QualityCheckInput:
    return QualityCheckInput(
        context={
            "landed_file": path,
            "storage_zone": "landing",
            "landing_path": f"files/bronze/landing/{path.name}",
        },
        params={},
        check_id="xlsx-package-integrity",
        quality_gate=QualityGate.PRE_BRONZE,
        applies_to={},
    )


def test_valid_xlsx_package_passes(tmp_path: Path) -> None:
    path = tmp_path / "valid.xlsx"
    _write_package(path)

    result = xlsx_package_integrity(_check_input(path))

    assert result.status == "passed"
    assert result.actual["valid_xlsx_package"] is True
    assert result.actual["worksheet_count"] == 1


def test_invalid_xlsx_package_fails(tmp_path: Path) -> None:
    path = tmp_path / "invalid.xlsx"
    path.write_text("not an XLSX package", encoding="utf-8")

    result = xlsx_package_integrity(_check_input(path))

    assert result.status == "failed"
    assert result.actual["valid_xlsx_package"] is False
    assert result.actual["error"] == "not a valid ZIP-based XLSX package"


def test_non_xlsx_file_is_skipped(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    path.write_text("value\n1\n", encoding="utf-8")

    result = xlsx_package_integrity(_check_input(path))

    assert result.status == "skipped"
    assert result.actual["skipped_reason"] == "not_xlsx"


def test_result_does_not_expose_absolute_path(tmp_path: Path) -> None:
    path = tmp_path / "valid.xlsx"
    _write_package(path)

    result = xlsx_package_integrity(_check_input(path))
    evidence = repr((result.actual, result.details))

    assert str(tmp_path) not in evidence


def test_xlsx_package_integrity_is_registered() -> None:
    registry = create_default_quality_registry()

    assert registry.resolve("xlsx_package_integrity") is xlsx_package_integrity
