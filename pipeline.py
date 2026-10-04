"""Reconstruct inherited Rajasthan tables and audit their source lineage."""

import argparse
import csv
import hashlib
import json
import re
import tarfile
import zipfile
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

FIELDS = [
    "original_filename",
    "page",
    "sr_no",
    "current_gp_name",
    "old_gp_villages",
    "new_or_reconstituted_gp_name",
    "new_gp_villages",
]
CLEANUP = {
    "sr_no": "क्र.सं.",
    "old_gp_villages": "वर्तमान ग्रा ० प ० में",
    "new_gp_villages": "नवसृजित ग्रा 0 प 0 में",
    "current_gp_name": "वर्तमान\nग्रा 0 प 0 का\nनाम",
    "new_or_reconstituted_gp_name": (
        "पुनर्गठित /\nपुनर्सीमांकित / नवसृजित\nग्रा ० प ० का नाम"
    ),
}
PDFS = {2014: "delimitation_2014.pdf", 2019: "GP_Delimitation_2019_Final.pdf"}
ARCHIVES = {
    2014: "gp_delimitation_2014.tar.gz",
    2019: "GP_Delimitation_2019_Final_json.tar.gz",
}


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        fields = next(reader)
        if len(set(fields)) != len(fields):
            raise ValueError(f"Duplicate columns: {path}")
        rows = []
        for number, values in enumerate(reader, 1):
            if len(values) != len(fields):
                raise ValueError(f"Wrong column count in {path}, data row {number}")
            rows.append(dict(zip(fields, values)))
    return fields, rows


def table_digest(fields, rows):
    values = [[row[field] for field in fields] for row in rows]
    encoded = json.dumps([fields, values], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def reconstruct(rows):
    """Replay notebook 03, including its exclusions and pre-cleanup deduplication."""
    output, lineage, seen = [], [], {}
    excluded = expanded = 0
    for source_row, row in enumerate(rows, 1):
        if row["col3"] == "":
            excluded += 1
            continue
        values = [row["original_filename"], row["page"]]
        values += [row[f"col{i}"] for i in range(1, 6)]
        for line, village in enumerate(row["col3"].split("\n"), 1):
            record = values.copy()
            record[4] = village.split(". ", 1)[-1].strip()
            key = tuple(record)
            expanded += 1
            if key not in seen:
                seen[key] = len(output) + 1
                output.append(
                    {
                        field: (
                            value.replace(CLEANUP[field], "")
                            if field in CLEANUP
                            else value
                        )
                        for field, value in zip(FIELDS, record)
                    }
                )
            lineage.append(
                {
                    "output_row": seen[key],
                    "source_row": source_row,
                    "old_village_line": line,
                }
            )
    return (
        output,
        lineage,
        {
            "input_rows": len(rows),
            "excluded_empty_old_village_cells": excluded,
            "expanded_rows_before_deduplication": expanded,
            "duplicates_removed_before_cleanup": expanded - len(output),
            "output_rows": len(output),
        },
    )


def source_page(filename, page, year, page_count):
    """Return a one-based PDF page; split offsets are inferred from filenames."""
    if not re.fullmatch(r"[0-9]+", str(page)):
        raise ValueError(f"Invalid zero-based page: {page!r}")
    index = int(page)
    if filename == PDFS[year]:
        start, end = 1, page_count
    elif year == 2019 and filename == "GP_Delimitation_2019_Final-1-400.pdf":
        start, end = 1, 400
    elif year == 2019 and (match := re.fullmatch(r"chunk_(\d+)-(\d+)\.pdf", filename)):
        start, end = map(int, match.groups())
    else:
        raise ValueError(f"Unknown source filename: {filename}")
    if not 1 <= start <= end <= page_count or index >= end - start + 1:
        raise ValueError(f"Page outside source range: {filename}, {page}")
    return start + index


def read_ocr_archive(path, page_count, width):
    """Read cell JSON without extracting archive paths or propagating cell spans."""
    records, pages = [], set()
    with tarfile.open(path) as archive:
        members = [
            member
            for member in archive.getmembers()
            if member.isfile()
            and Path(member.name).suffix == ".json"
            and Path(member.name).stem.isdigit()
        ]
        for member in sorted(members, key=lambda item: int(Path(item.name).stem)):
            page = int(Path(member.name).stem)
            if page in pages or not 1 <= page <= page_count:
                raise ValueError(f"Duplicate or invalid OCR page: {member.name}")
            pages.add(page)
            with archive.extractfile(member) as stream:
                blocks = json.load(stream)
            for table_index, block in enumerate(blocks, 1):
                rows = {}
                for cell in block.get("cells", []):
                    row_id, col = cell["row"], cell["col"]
                    if row_id < 1 or not 1 <= col <= width:
                        raise ValueError(f"Unexpected cell coordinates: {member.name}")
                    row = rows.setdefault(row_id, {})
                    if col in row:
                        raise ValueError(f"Duplicate cell coordinates: {member.name}")
                    if not isinstance(cell["text"], str):
                        raise ValueError(f"Non-text OCR cell: {member.name}")
                    row[col] = cell["text"]
                for row_id, row in sorted(rows.items()):
                    records.append(
                        {
                            "source_pdf_page": page,
                            "json_member": member.name,
                            "table": table_index,
                            "table_row": row_id,
                            **{f"col{i}": row.get(i, "") for i in range(1, width + 1)},
                        }
                    )
    if pages != set(range(1, page_count + 1)):
        raise ValueError(f"OCR page coverage incomplete: {path}")
    return records


def reconcile(raw, recovered, year, page_count, width):
    columns = [f"col{i}" for i in range(1, width + 1)]
    expected = Counter(
        (source_page(row["original_filename"], row["page"], year, page_count),)
        + tuple(row[col] for col in columns)
        for row in raw
    )
    observed = Counter(
        (row["source_pdf_page"],) + tuple(row[col] for col in columns)
        for row in recovered
    )

    def differences(counter):
        return [
            {"source_pdf_page": key[0], "values": list(key[1:]), "count": count}
            for key, count in sorted(counter.items())
        ]

    return {
        "columns": columns,
        "comparison": "Exact cell strings and inferred PDF page; unordered multiset",
        "inherited_rows": len(raw),
        "recovered_rows": len(recovered),
        "matching_rows": sum((expected & observed).values()),
        "only_in_inherited": differences(expected - observed),
        "only_in_archive": differences(observed - expected),
    }


def profile(fields, rows):
    result = {"rows": len(rows), "columns": {}}
    for field in fields:
        values = [row[field] for row in rows]
        counts = Counter(values)
        nonempty = [value for value in values if value.strip()]
        result["columns"][field] = {
            "blank": sum(not value.strip() for value in values),
            "distinct": len(counts),
            "surrounding_whitespace": sum(value != value.strip() for value in values),
            "common_values": counts.most_common(5),
            "min_length_nonblank": min(map(len, nonempty), default=0),
            "max_length": max(map(len, values), default=0),
            "numeric_only": sum(bool(re.fullmatch(r"\d+", value)) for value in values),
        }
    result["exact_duplicate_rows"] = len(rows) - len(
        {tuple(row[field] for field in fields) for row in rows}
    )
    return result


def verify_files(root, manifest):
    profiles = {}
    for entry in manifest["files"]:
        path = root / entry["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Source checksum changed: {path}")
        if path.stat().st_size != entry["bytes"]:
            raise ValueError(f"Source size changed: {path}")
        if entry["kind"] == "pdf":
            if len(PdfReader(path).pages) != entry["pages"]:
                raise ValueError(f"PDF page count changed: {path}")
        elif entry["kind"] == "zip":
            with zipfile.ZipFile(path) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f"Corrupt ZIP: {path}")
        elif entry["kind"] == "csv":
            fields, rows = read_csv(path)
            if fields != entry["fields"] or len(rows) != entry["rows"]:
                raise ValueError(f"CSV schema or row count changed: {path}")
            profiles[entry["path"]] = profile(fields, rows)
    expected = {entry["path"] for entry in manifest["files"]}
    actual = {
        str(path.relative_to(root))
        for folder in ("sources", "intermediate", "processed")
        for path in (root / "data" / folder).rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    }
    if actual != expected:
        raise ValueError(f"Uncatalogued or missing data files: {actual ^ expected}")
    return profiles


def run(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or output.is_relative_to(root / "data"):
        raise ValueError("Generated outputs must be outside the inherited data folders")
    manifest = json.loads((root / "data/manifest.json").read_text())
    report = {"files_verified": len(manifest["files"])}
    report["profiles"] = verify_files(root, manifest)
    report["years"] = {}
    output.mkdir(parents=True, exist_ok=True)
    for year in (2014, 2019):
        source = root / f"data/intermediate/gp_{year}_delim_orig_sub.csv"
        _, raw = read_csv(source)
        rebuilt, lineage, counts = reconstruct(raw)
        reference = manifest["reconstructions"][str(year)]
        if (
            len(rebuilt) != reference["rows"]
            or FIELDS != reference["fields"]
            or table_digest(FIELDS, rebuilt) != reference["table_sha256"]
        ):
            raise ValueError(f"{year} reconstruction differs from the historical table")
        page_count = next(
            entry["pages"]
            for entry in manifest["files"]
            if entry["path"] == f"data/sources/{PDFS[year]}"
        )
        page_files = {}
        for row in raw:
            page = source_page(row["original_filename"], row["page"], year, page_count)
            page_files.setdefault(page, set()).add(row["original_filename"])
        for record in lineage:
            row = raw[record["source_row"] - 1]
            record.update(
                source_csv=source.name,
                source_pdf=PDFS[year],
                source_pdf_page=source_page(
                    row["original_filename"], row["page"], year, page_count
                ),
                page_mapping="inferred_from_filename_and_zero_based_page",
            )
        width = 8 if year == 2014 else 10
        recovered = read_ocr_archive(
            root / "data/sources" / ARCHIVES[year], page_count, width
        )
        comparison = reconcile(raw, recovered, year, page_count, width)
        write_csv(output / f"gp_{year}_delim_reconstructed.csv", FIELDS, rebuilt)
        write_csv(output / f"lineage_{year}.csv", list(lineage[0]), lineage)
        write_csv(output / f"recovered_ocr_{year}.csv", list(recovered[0]), recovered)
        write_json(output / f"reconciliation_{year}.json", comparison)
        report["years"][str(year)] = {
            **counts,
            "historical_table_matches": True,
            "inherited_pdf_pages_covered": len(page_files),
            "pdf_pages": page_count,
            "missing_inherited_pdf_pages": sorted(
                set(range(1, page_count + 1)) - page_files.keys()
            ),
            "pages_with_multiple_split_files": {
                str(page): sorted(names)
                for page, names in sorted(page_files.items())
                if len(names) > 1
            },
            "ocr_matching_rows": comparison["matching_rows"],
            "ocr_archive_only_rows": len(recovered) - comparison["matching_rows"],
            "ocr_inherited_only_rows": len(raw) - comparison["matching_rows"],
        }
    report["limitations"] = [
        "Historical outputs retain headers, blanks, OCR errors and "
        "wrapped-name fragments.",
        "The enriched 2014 snapshot has no recovered enrichment or "
        "translation workflow.",
        "Archived OCR differs from inherited extractions; "
        "reconciliation is diagnostic.",
        "OCR engine, settings and moderation history have not been recovered.",
        "Supplementary notifications are not confirmed as incorporated "
        "into these tables.",
        "No census-village join or stable cross-year village key is established.",
    ]
    write_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    report = run(args.root, args.output_dir or args.root / "build")
    print(f"Verified {report['files_verified']} source artifacts.")
    for year, values in report["years"].items():
        print(f"{year}: reproduced {values['output_rows']:,} historical rows exactly.")
    print(
        f"Data-quality limitations and OCR differences: "
        f"{args.output_dir or args.root / 'build'}/report.json"
    )


if __name__ == "__main__":
    main()
