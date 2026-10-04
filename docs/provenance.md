# Provenance and processing ledger

## Preserved evidence

The repository's pre-cleanup snapshot is commit
`55ecb663cf402bac0bd4d0408ad5c28651b1c014`. The PDFs, ZIP, and four working-tree CSVs
were moved into source, intermediate, and processed directories without changing
their bytes. The local `gp_2014_delim_processed.csv` was already modified: it has
10 enrichment columns, whereas the committed historical file has seven extraction
columns. The local enriched version is retained in `data/processed/`.

The historical notebooks are available in that commit's `notebooks/` directory.
Their runnable replacement is `pipeline.py`. The first notebook's whitespace
splitting was exploratory and did not establish a reproducible table extraction.
The second used working-directory-dependent filenames and an obsolete PDF API.
The third's processing sequence is reproduced and tested here.

`data/manifest.json` records every retained artifact's SHA-256 checksum, role, and
provenance. For CSVs it also records column order and row count; for PDFs, page
count. Git line-ending conversion is disabled for `data/` so committing or checking out
the repository preserves these checksums. A changed checksum stops the workflow. Review a legitimate data revision
and its provenance before updating the manifest; do not regenerate baselines just
to make a failed check pass.

## Recovered public extraction evidence

[Harvard Dataverse version 6.0](https://doi.org/10.7910/DVN/SBF7DP), inspected on
2026-10-04, provides these archives:

| Archive | Dataverse file ID | Coverage |
| --- | --- | --- |
| `gp_delimitation_2014.tar.gz` | 7327669 | JSON for PDF pages 1 through 316 |
| `GP_Delimitation_2019_Final_json.tar.gz` | 7317955 | JSON for PDF pages 1 through 701 |

The downloaded archive checksums match the published MD5 values; SHA-256 checksums
are recorded locally. Other retained files with matching Dataverse checksums have
their published identifiers in the manifest, including differently named PDFs.
The dataset also publishes `2014_gp_to_village.tab` and `2019_gp_to_village.tab`.
Those tables have not been equated to the local CSVs or substituted for them.

The archives store table cells, coordinates, spans, text, confidence scores, and
moderation-status labels. Those labels do not establish independent validation.
The OCR provider, version, settings, and moderation history remain unverified.
The workflow reads JSON members in memory, ignores unrelated files in the archive,
and requires exactly one JSON file for each source PDF page.

The reconstructed OCR tables preserve each cell's text at its recorded row and
column. They do not fill merged cells, resolve wrapped names, or merge neighboring
tables. Their row order is numeric PDF page, original JSON table position, and
numeric table row. They are compared with inherited extractions as multisets of
exact cell strings plus inferred PDF page. `build/reconciliation_*.json` retains
all unmatched values and multiplicities for review. The archives and CSVs are
close but not identical; this comparison does not establish which version is
correct.

## Reproduced processing

The following operations replay notebook 03. Their limitations are preserved so
that the historical outputs can be checked. A future corrected village dataset
should have a separate, reviewed transformation and a documented reconciliation.

| Step | Transformation | Validation or consequence |
| --- | --- | --- |
| Select columns | Retain `original_filename`, `page`, and `col1` through `col5` | Extra OCR columns remain available in the inherited extraction |
| Rename | Map `col1` to serial number and `col2` through `col5` to GP/village fields | Historical seven-column schema is retained |
| Exclude | Skip rows with an empty `col3` | Counts are reported; this can drop newly constituted GP entries with no old-village text |
| Expand | Split `col3` on every newline | A wrapped village name may become multiple records; trailing newlines can create blank records |
| Remove prefix | Keep the text after the first literal `. `, then strip surrounding whitespace | This is the notebook rule, not a general bullet-number parser |
| Deduplicate | Keep the first identical seven-field row before cleanup | Every contributing source-row/line position is retained in the lineage table |
| Clean literals | Remove the five exact strings in `pipeline.CLEANUP` | Variant headers remain; no second deduplication occurs |
| Compare | Check column order, ordered values, and row count against historical fingerprints | Both years must reproduce exactly |

Fingerprints encode `[columns, rows]` as compact UTF-8 JSON. They compare table
values and order without treating CSV quoting or line endings as data changes.
The 2019 reference is also present in `data/processed/`; the 2014 reference is the
seven-column CSV in commit `55ecb66`. The enriched 2014 snapshot is checksum-checked
but is not claimed to be regenerated.

Blank fields remain empty strings. Literal `NA`, `-`, and numeric strings are not
converted to missing values or zeros. Reported blank counts also count
whitespace-only strings, but the historical exclusion step uses an exactly empty
cell. All inherited columns are read as text.

## Page and row lineage

`page` in the inherited CSVs is zero-based within `original_filename`. Generated
`source_pdf_page` is one-based within the complete source PDF and is not the page
number printed in the Gazette.

- `delimitation_2014.pdf`: original PDF page is `page + 1`.
- `GP_Delimitation_2019_Final-1-400.pdf`: original PDF page is `page + 1`.
- `chunk_START-END.pdf`: original PDF page is `START + page`.

The split-page offsets are inferred from filenames and supported by the extensive
exact matches with the page-numbered OCR archives. The original split PDFs and
split-generation log have not been recovered. Bounds checks reject unknown names,
negative or noninteger page values, and pages outside either the split or full PDF.
PDF page 400 occurs in both the first split and `chunk_400-402.pdf`; it is reported,
not silently removed. Page coverage alone says nothing about complete table or
village coverage.

In `lineage_*.csv`, `source_row` and `output_row` count data records from one,
excluding the header; they are not physical text-file line numbers. Embedded
newlines make those quantities differ. `old_village_line` is one-based within the
original `col3` string. Multiple lineage records can map to one output row because
the notebook removed duplicates.

## Decisions still requiring evidence

1. Recover the 2014 district, Panchayat Samiti, corrected-name, and translation
   edits. The two similarly named correction fields are not automatically combined.
2. Resolve unmatched OCR rows against the PDFs, including table order, merged
   cells, extra columns, and edits made between archive and CSV creation.
3. Review extraction debris and wrapped names. Do not treat a line count as a
   village count or automatically forward-fill names across table boundaries.
4. Establish the effective dates and coverage of supplementary notifications and
   corrections. Their presence here does not prove they were incorporated.
5. Before joining the Census 2001 shapefile, define the left-hand universe, a stable
   geographic key, expected cardinality, and treatment of unmatched or ambiguous
   names. No join is performed by this workflow; names alone are not verified IDs.

The PDF reader uses the documented
[pypdf page-reading interface](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
Reading text from a PDF is not a replacement for recovering the original OCR
procedure or checking table semantics.
