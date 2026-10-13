# HRD Genomic Scar Score

Research-only calculator for the **arithmetic sum of precomputed genomic scar event counts**: loss of heterozygosity (LOH), telomeric allelic imbalance (TAI), and large-scale state transitions (LST).

**Not a clinical HRD assay or a replacement for a validated genomic pipeline.** This program does not derive genomic events from sequencing data, assess BRCA1/2 pathogenicity, diagnose HRD, predict treatment response, or recommend PARP inhibitors.

## Features

- Single-sample scoring in Python through hrd_scar.py or the installed hrd-scar command.
- CSV input and output with unrelated metadata retained and row-specific validation.
- Dependency-free static browser calculator with local CSV processing and downloadable results (web/).
- Optional FastAPI service and separate **demonstration-only** policy/audit agent workflow, with thresholds that are not clinically validated.
- Process-local HMAC-SHA256 chained audit logs. Durable verification requires a persistent key and external storage.

## Formula and scientific limitations

For non-negative **integer counts** originating from a validated event-calling pipeline:

~~~text
Composite count = LOH + TAI + LST
~~~

The implementation provides this **unweighted sum only**. Definitions and algorithms used to derive LOH/TAI/LST, assay calibration, and clinical thresholds vary among tests. The myChoice CDx genomic instability score is a regulated assay-specific result; this project is **not** its validated implementation. No clinical interpretation or universal cutoff is applied.

Scientific references:
- [FDA myChoice HRD CDx premarket approval (P190014)](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id=P190014)
- [Review: homologous recombination deficiency testing landscape](https://pmc.ncbi.nlm.nih.gov/articles/PMC11846297/)
- [Genomic instability component definitions](https://link.springer.com/article/10.1186/s13073-024-01413-5)

## Browser usage

Open [web/index.html](web/index.html) locally or publish the web/ directory through GitHub Pages using the included workflow. A plain JavaScript implementation is used rather than Pyodide because the operation is straightforward and fully client-side. Assets use relative URLs.

Enter LOH, TAI, and LST counts or upload a CSV with loh, tai, lst columns. Legacy v1, v2, v3 aliases are accepted. Other columns are retained but not included in the score. Files are processed only in your browser, with no network requests or local storage. The browser limits files to 2 MB and 20,000 records.

## Python installation and CLI

Python 3.10+:

~~~bash
python -m pip install -e .
hrd-scar single --loh 15 --tai 12 --lst 8
hrd-scar batch -i sample.csv -o results.csv
~~~

Legacy command-line aliases --v1, --v2, and --v3 are supported. The CSV results include LOH/TAI/LST, their sum, and explicit unvalidated-interpretation fields. Missing, noninteger or negative counts are errors, not implicit zeros. The input CSV cannot be overwritten in place.

### Optional demonstration API

~~~bash
python -m pip install -e ".[web]"
python cli.py serve --host 127.0.0.1 --port 8000
~~~

Visit http://127.0.0.1:8000/docs. POST /api/score calculates the component sum. Other endpoints (/api/audit, /api/chat, /metrics) are a separate **demonstration agent workflow**, not a validated HRD clinical assessment. Chat is a deterministic mock, not a real LLM. Do not expose the API publicly without additional authentication and a security review.

Audit records are in-memory and discarded on process exit. Configure AUDIT_SECRET_KEY for a stable signing key. GET /api/audit/logs is disabled unless AUDIT_LOG_API_TOKEN is set and sent as a Bearer token. Pattern-based identifier checks do not guarantee PHI removal or HIPAA compliance.

## Privacy and security

The static browser has no server calls, analytics, browser storage, or external assets. Avoid processing real patient identifiers. The optional API processes requests in the server process and returns data to the caller; do not assume its regex screening removes all identifying information.

## Testing and deployment

~~~bash
python -m pip install -e ".[all]"
python -m pytest -q
node --test tests/web.test.mjs
~~~

GitHub Actions tests Python 3.10–3.12, the installed CLI, distribution build, and browser scoring module. A separate workflow deploys web/ to GitHub Pages on master **when Pages is enabled and configured to use GitHub Actions**.

## Technology, browser compatibility, license

Python 3.10+, standard-library core, optional Pydantic/FastAPI/Uvicorn, vanilla HTML/CSS/ES modules for current Chromium, Firefox and Safari. MIT license; see [LICENSE](LICENSE).
