# Data dictionary

The schemas below describe inherited files, not a harmonized panel. Every CSV
column is read as text. Empty and whitespace-only values are reported as blank;
no source codebook establishes whether each blank means a merged cell, missing
OCR, an inapplicable field, or an omitted edit. Literal dashes, `NA`, and numeric
strings are retained. Missingness, common values, lengths, and exact duplicates
are regenerated in `build/report.json`.

## Intermediate extraction tables

`data/intermediate/gp_YEAR_delim_orig_sub.csv` has one inherited extracted table
row per record, including headings and non-village text. Its unnamed first column
is the preserved CSV export index. It is not a village ID. A source PDF page can
contain multiple tables and many rows.

| Column | Meaning and source | Values and qualifications |
| --- | --- | --- |
| unnamed first column | Original export index | Text containing a numeric index; preserved without renumbering |
| `original_filename` | PDF or split-file label from extraction | Full 2014 PDF; first 400-page split or numbered chunks for 2019 |
| `page` | Page position within that file | Zero-based integer text; bounds checked before mapping |
| `col1` | First extracted cell, generally the table's serial number | Includes headings, blanks, punctuation, and OCR errors |
| `col2` | Generally the existing Gram Panchayat name | Inferred from source table headings; shifted columns and merged cells occur |
| `col3` | Generally villages in the existing Gram Panchayat | May contain multiline lists, wrapped names, headers, or blanks |
| `col4` | Generally the reconstituted/new Gram Panchayat name | Same extraction qualifications as `col2` |
| `col5` | Generally villages in the reconstituted/new Gram Panchayat | Often a multiline list; not a unique village key |
| `col6` through `col8` | Additional extraction columns in both years | Preserved; their meanings vary with table layout or extraction errors |
| `col9`, `col10` | Additional extraction columns in 2019 | Preserved even when empty; historical processing omits them |

The first five table headings were checked visually against the 2014 PDF's first
page and the 2019 PDF's third page. That establishes the usual layout, not the
correctness of every extracted row. The extraction index identifies a record only
within a fixed file snapshot. No substantive unique village key is established.

## Historical seven-column outputs

`data/processed/gp_2019_delim_processed.csv` and the reconstructed files in `build/`
use this schema. A record is a retained line from the old-village cell after the
historical expansion and deduplication. It is not necessarily one village and
must not be interpreted as an old-to-new village match.

| Column | Source or transformation | Unit and values |
| --- | --- | --- |
| `original_filename` | Copied from extraction | Original full/split PDF label |
| `page` | Copied from extraction | Zero-based position within the labeled file |
| `sr_no` | `col1`, removing literal `क्र.सं.` | Table-local serial text; not globally unique |
| `current_gp_name` | `col2`, with one literal heading removal | Existing GP text; may be blank or a residual heading |
| `old_gp_villages` | Expanded `col3`; prefix stripping and one literal heading removal | One text line, including possible fragments and debris |
| `new_or_reconstituted_gp_name` | `col4`, with one literal heading removal | New/reconstituted GP text; may be blank or a heading |
| `new_gp_villages` | `col5`, with one literal heading removal | Entire new-village cell, repeated for each expanded old-village line |

The explicit strings and order of operations are in `pipeline.CLEANUP` and the
[processing ledger](provenance.md). The generated lineage table supplies a record
key within each build; it does not create a stable geographic identifier.

## Preserved enriched 2014 snapshot

`data/processed/gp_2014_delim_processed.csv` is the pre-cleanup local working copy.
Its apparent unit is an old-village/GP record with later annotations, inferred from
its values and names. The editing process and intended coverage have not been
recovered. It differs from the historical seven-column output and is not used as
that output's reproduction target.

| Column | Apparent meaning | Provenance and limitations |
| --- | --- | --- |
| `current_gp_name` | Existing GP name in Hindi | Inherited enrichment file; no row-level link to the extraction survives |
| `old_gp_villages` | Existing village name/text in Hindi | As above; exact derivation is not established |
| `old_gp_village_fixed` | Corrected Hindi village text | Inferred from name and values; correction method unknown |
| `district` | District name in Latin script | Assignment method unknown; blanks remain |
| `ps` | Panchayat Samiti name, generally in Hindi | Inferred expansion of abbreviation; assignment method unknown |
| `order` | Ordering/index field | Not unique and sometimes blank; do not use as a join key |
| `gp_goog_translate` | Latin-script rendering of GP name | Column name suggests Google translation; service/version/settings unverified |
| `gp_village_goog_translate` | Latin-script rendering of village name | Same provenance gap; not a verified transliteration standard |
| `ps_goog_translate` | Latin-script rendering of Panchayat Samiti name | Same provenance gap; blanks remain |
| `gp_village_fixed` | Sparse Latin-script village corrections | Inferred from observed entries; do not assume it replaces the Hindi correction field |

The inherited district and Panchayat Samiti labels are annotations, not validated
boundary identifiers. No population coverage claim, cross-year equivalence, or
census-geography linkage follows from these fields.

## Generated evidence

| Output | Record unit and key |
| --- | --- |
| `lineage_YEAR.csv` | An expanded source-cell line; `(source_csv, source_row, old_village_line)` identifies a contribution; several contributions may share `output_row` |
| `recovered_ocr_YEAR.csv` | An OCR table row; `(json_member, table, table_row)` identifies the row; `colN` preserves the cell text |
| `reconciliation_YEAR.json` | A differing `(source_pdf_page, cell values)` tuple and its multiplicity |
| `report.json` | Per-file profiles and per-year processing/page/reconciliation counts |

The census ZIP contains the Rajasthan Census 2001 village shapefile and its
attribute table. Its columns have not been assigned meanings or joined to these
records. The archive is retained and integrity-checked as geographic reference
material.
