# Rajasthan local-election delimitation

Source documents, OCR extractions, and inherited tables for Rajasthan Gram Panchayat
(village council) delimitation in 2014 and 2019. The collection also includes
Panchayat Samiti (block-level body) notifications and Census 2001 village geography.
The linked published dataset is [Rajasthan GP Delimitation on Harvard
Dataverse](https://doi.org/10.7910/DVN/SBF7DP).

The local workflow reconstructs the historical table processing and checks its
provenance. **The inherited tables still contain extraction errors and are not a
validated village crosswalk.** The enriched local 2014 file is preserved separately
from the reconstructed historical 2014 output.

## Files

| Location | Contents |
| --- | --- |
| `data/sources/` | Original PDFs, census shapefile ZIP, and published OCR JSON archives |
| `data/intermediate/` | Inherited table extractions, including the original CSV index column |
| `data/processed/` | Preserved 2014 enriched and 2019 processed snapshots |
| [`data/manifest.json`](data/manifest.json) | Checksums, schemas, provenance, source roles, and Dataverse file identifiers |
| `build/` | Reconstructed tables, row lineage, OCR reconciliation, and profiles; generated locally |
| [`pipeline.py`](pipeline.py) | Reproduction and validation workflow |

Sources formerly held in `local_shape` are consolidated here. Original filenames
and the bytes of all inherited data files are retained.

## Run locally

Use Python 3.13 or newer from the repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make check
make reproduce
```

`make check` runs Black, isort, flake8, and tests, including reconstruction from the
actual data. `make reproduce` verifies source checksums and writes:

- `build/gp_2014_delim_reconstructed.csv` and `build/gp_2019_delim_reconstructed.csv`:
  historical notebook results, checked against ordered table fingerprints.
- `build/lineage_2014.csv` and `build/lineage_2019.csv`: source rows, line positions,
  and inferred original PDF pages for each generated row.
- `build/recovered_ocr_2014.csv` and `build/recovered_ocr_2019.csv`: table rows rebuilt
  from the published cell JSON, without filling merged cells or cleaning text.
- `build/reconciliation_2014.json` and `build/reconciliation_2019.json`: exact row
  differences between those OCR archives and the inherited extraction CSVs.
- `build/report.json`: missingness, duplicate counts, page coverage, processing
  losses, overlapping split files, and remaining limitations.

The workflow also runs from another directory:

```bash
/path/to/.venv/bin/python /path/to/repository/pipeline.py --output-dir /tmp/raj-build
```

No API keys, paid OCR calls, or network access are needed after installing the
Python dependencies. For a standard Python 3.14 container, run `make ci-docker` with a
running Docker daemon. GitHub Actions runs the same local checks.

## Interpretation and further work

Read the [data dictionary](docs/data-dictionary.md) before using either year's
CSV, and the [provenance and processing ledger](docs/provenance.md) before changing
the pipeline. A passing check establishes preservation and reproducibility; it
does not establish that OCR text identifies villages correctly.

The remaining substantive work is to recover the 2014 enrichment history, review
the OCR-to-CSV discrepancies, resolve headers and wrapped village names against
the PDFs, and establish which amendments belong in each dated boundary snapshot.
A census-geography join requires a reviewed key and explicit handling of ambiguous
village names.
