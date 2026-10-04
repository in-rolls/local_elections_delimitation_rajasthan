# Rajasthan Gram Panchayat Delimitation

Data and source documents on the reorganization of Gram Panchayats (village
councils) in Rajasthan in 2014 and 2019. The Gazette notifications list existing
and newly constituted Panchayats and the villages assigned to them. This
repository contains the notifications, extracted tables, and code for reproducing
the table processing.

**[Download the published dataset from Harvard Dataverse](https://doi.org/10.7910/DVN/SBF7DP).**

## Data

The published dataset includes `2014_gp_to_village.tab` and
`2019_gp_to_village.tab`. The working files in this repository are:

| File | Contents |
| --- | --- |
| [2014 table](data/processed/gp_2014_delim_processed.csv) | Existing Panchayat and village names, district and Panchayat Samiti labels, corrected names, and Latin-script name renderings |
| [2019 table](data/processed/gp_2019_delim_processed.csv) | Existing and new Panchayat names, village lists, and source-file/page references |
| [Extraction tables](data/intermediate/) | OCR table rows before village-list expansion and text cleanup |
| [Source documents](data/sources/) | Gazette PDFs, supplementary notifications, OCR JSON archives, and Census 2001 Rajasthan village geography |

See the [data dictionary](docs/data-dictionary.md) for column definitions and the
[provenance notes](docs/provenance.md) for processing details. The local tables
have not been reconciled with the published village tables on Dataverse.

## Using the tables

Read the CSVs as UTF-8 text. For example, from the repository directory:

```python
import csv
from pathlib import Path

path = Path("data/processed/gp_2019_delim_processed.csv")
with path.open(encoding="utf-8", newline="") as stream:
    rows = list(csv.DictReader(stream))

print(rows[0])
```

The 2019 processing splits the old-village field into lines and repeats the
new-village list alongside each line. A row therefore does **not** establish a
one-to-one match between an old and a new village. Headers, wrapped names, and OCR
errors remain in the extracted data and need review against the PDFs.

The 2014 table includes later name and geographic annotations whose editing
history is not available here. Supplementary notifications and census geography
are included as source material; their incorporation into the tables has not been
established.

## Reproduce the processing

With Python 3.13 or newer, run these commands from the repository directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
make reproduce
```

This writes reconstructed tables and source-row references to `build/`, together
with reports comparing the published OCR archives with the extraction CSVs. The
2019 reconstruction matches the checked-in table. The 2014 reconstruction matches
the earlier seven-column output, before the additional annotations in the current
2014 table. See [generated outputs](docs/provenance.md#generated-outputs) for the
file list and page-number conventions.

`make check` runs linting and tests, including exact reproduction of both historical
outputs. `make ci-docker` runs the same checks in a standard Python 3.14 container.
Source checksums and schemas are recorded in [the manifest](data/manifest.json).

## Cite the data

Use the citation and version supplied by
[Harvard Dataverse](https://doi.org/10.7910/DVN/SBF7DP). For results based on the
repository's working tables, also record the Git commit used.
