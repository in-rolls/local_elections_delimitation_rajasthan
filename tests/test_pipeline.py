import io
import json
import tarfile
from pathlib import Path

import pytest

from pipeline import (
    FIELDS,
    read_csv,
    read_ocr_archive,
    reconstruct,
    run,
    source_page,
    table_digest,
    verify_files,
    write_csv,
)

ROOT = Path(__file__).resolve().parents[1]


def raw_row(villages, **changes):
    row = dict(
        zip(
            ["original_filename", "page"] + [f"col{i}" for i in range(1, 6)],
            [
                "delimitation_2014.pdf",
                "0",
                "1",
                "भूडोल",
                villages,
                "भूडोल",
                "1. लाडपुरा",
            ],
        )
    )
    return row | changes


def test_expansion_preserves_missingness_and_lineage():
    rows = [raw_row("1. भूडोल\n2. लाडपुरा\n"), raw_row(""), raw_row("NA")]
    rebuilt, lineage, stats = reconstruct(rows)
    assert [r["old_gp_villages"] for r in rebuilt] == ["भूडोल", "लाडपुरा", "", "NA"]
    assert [r["source_row"] for r in lineage] == [1, 1, 1, 3]
    assert stats["excluded_empty_old_village_cells"] == 1
    assert all(r["new_gp_villages"] == "1. लाडपुरा" for r in rebuilt)


def test_deduplication_precedes_cleanup_and_retains_all_origins():
    rows = [
        raw_row("1. भूडोल"),
        raw_row("1. भूडोल"),
        raw_row("1. भूडोल", col1="क्र.सं.1"),
    ]
    rebuilt, lineage, stats = reconstruct(rows)
    assert len(rebuilt) == 2
    assert rebuilt[0] == rebuilt[1]
    assert [r["output_row"] for r in lineage] == [1, 1, 2]
    assert stats["duplicates_removed_before_cleanup"] == 1


@pytest.mark.parametrize(
    "filename,page,year,total,expected",
    [
        ("delimitation_2014.pdf", "0", 2014, 316, 1),
        ("delimitation_2014.pdf", "315", 2014, 316, 316),
        ("GP_Delimitation_2019_Final-1-400.pdf", "399", 2019, 701, 400),
        ("chunk_400-402.pdf", "0", 2019, 701, 400),
        ("chunk_700-701.pdf", "1", 2019, 701, 701),
    ],
)
def test_original_pdf_page_offsets(filename, page, year, total, expected):
    assert source_page(filename, page, year, total) == expected


@pytest.mark.parametrize(
    "filename,page",
    [
        ("unknown.pdf", "0"),
        ("chunk_400-402.pdf", "3"),
        ("chunk_700-702.pdf", "0"),
        ("chunk_402-400.pdf", "0"),
        ("chunk_400-402.pdf", "-1"),
        ("chunk_400-402.pdf", "1.5"),
    ],
)
def test_invalid_page_mapping_fails(filename, page):
    with pytest.raises(ValueError):
        source_page(filename, page, 2019, 701)


def test_csv_roundtrip_keeps_unicode_newlines_empty_and_literal_na(tmp_path):
    fields = ["name", "notes"]
    rows = [{"name": "भूडोल", "notes": "a\nb"}, {"name": "NA", "notes": ""}]
    path = tmp_path / "table.csv"
    write_csv(path, fields, rows)
    assert read_csv(path) == (fields, rows)
    assert table_digest(fields, rows) == table_digest(*read_csv(path))


def test_malformed_csv_fails(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("a,b\n1,2,3\n")
    with pytest.raises(ValueError, match="column count"):
        read_csv(path)


def make_archive(path, pages):
    with tarfile.open(path, "w:gz") as archive:
        for name, content in pages:
            encoded = json.dumps(content).encode()
            info = tarfile.TarInfo(name)
            info.size = len(encoded)
            archive.addfile(info, io.BytesIO(encoded))


def test_ocr_page_coverage_and_cell_collisions(tmp_path):
    path = tmp_path / "ocr.tar.gz"
    cell = {"row": 1, "col": 1, "text": "भूडोल"}
    make_archive(path, [("json/1.json", [{"cells": [cell, cell]}])])
    with pytest.raises(ValueError, match="Duplicate cell"):
        read_ocr_archive(path, 1, 5)
    make_archive(path, [("json/1.json", [{"cells": [cell]}])])
    with pytest.raises(ValueError, match="coverage"):
        read_ocr_archive(path, 2, 5)
    result = read_ocr_archive(path, 1, 5)
    assert result[0]["col1"] == "भूडोल"
    assert result[0]["col5"] == ""


def test_changed_source_fails_before_processing(tmp_path):
    source = tmp_path / "changed.csv"
    source.write_text("a\nb\n")
    manifest = {"files": [{"path": "changed.csv", "sha256": "incorrect"}]}
    with pytest.raises(ValueError, match="checksum changed"):
        verify_files(tmp_path, manifest)


def test_full_repository_reconstruction(tmp_path):
    report = run(ROOT, tmp_path / "outputs")
    assert report["files_verified"] == 19
    assert report["years"]["2014"]["output_rows"] == 13424
    assert report["years"]["2019"]["output_rows"] == 16787
    fields, rebuilt = read_csv(tmp_path / "outputs/gp_2019_delim_reconstructed.csv")
    assert fields == FIELDS
    assert (fields, rebuilt) == read_csv(
        ROOT / "data/processed/gp_2019_delim_processed.csv"
    )
    for year in (2014, 2019):
        fields, values = read_csv(
            tmp_path / f"outputs/gp_{year}_delim_reconstructed.csv"
        )
        _, lineage = read_csv(tmp_path / f"outputs/lineage_{year}.csv")
        assert {int(r["output_row"]) for r in lineage} == set(range(1, len(values) + 1))
        assert report["years"][str(year)]["historical_table_matches"]
        assert report["years"][str(year)]["ocr_inherited_only_rows"] > 0
    overlap = report["years"]["2019"]["pages_with_multiple_split_files"]
    assert overlap["400"] == [
        "GP_Delimitation_2019_Final-1-400.pdf",
        "chunk_400-402.pdf",
    ]
    assert (
        report["profiles"]["data/processed/gp_2014_delim_processed.csv"]["rows"]
        == 11819
    )


def test_output_cannot_overwrite_inherited_data():
    with pytest.raises(ValueError, match="outside"):
        run(ROOT, ROOT / "data/processed")
