# HRD Genomic Scar Score

> **Domain:** Medical Oncology & Cancer Staging Systems
> **Reference Guidelines & Standards:** AJCC Cancer Staging Manual & NCCN Clinical Practice Guidelines

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

Homologous Recombination Deficiency (HRD) Scar Score combines Loss of Heterozygosity (LOH), Telomeric Allelic Imbalance (TAI), and Large-scale State Transitions (LST) into a unified genomic scar score.

Zero-dependency Python implementation with single and batch evaluation capabilities.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Key Features

### Core Algorithm (`hrd_scar.py`)

- **`calculate_metrics(**kwargs)`** — Core scoring algorithm that evaluates numeric parameters and produces a composite score with clinical classification.
- **`process_single(args)`** — Evaluate a single case from CLI arguments.
- **`process_batch(input_csv, output_csv)`** — Process batch CSV records and append score columns.

### Enterprise Agent System (`agents/`)

- **Zero-PHI Outbound Interceptor** — Active regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
- **Tamper-Evident HMAC-SHA256 Audit Trail** — Chained, cryptographically signed logs for every evaluation.
- **Multi-Worker Evaluation** — InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker.
- **FastAPI REST API** — OpenAPI 3.1 REST endpoints with `/health`, `/metrics`, `/api/audit`, `/api/chat`.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/hrd-genomic-scar-score.git
cd hrd-genomic-scar-score

# Install core (zero dependencies)
pip install -e .

# Install with web API support
pip install -e ".[web]"

# Install with all dependencies (including tests)
pip install -e ".[all]"
```

---

## Usage

### Core CLI (`hrd_scar.py`)

**Single evaluation:**
```bash
python hrd_scar.py single --v1 14.5 --v2 4.2 --v3 1.8
```

**Batch processing:**
```bash
python hrd_scar.py batch -i sample.csv -o results.csv
```

### Enterprise CLI (`cli.py`)

**Run audit evaluation:**
```bash
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2
```

**Batch processing:**
```bash
python cli.py batch -i input.csv -o output.csv
```

**Verify audit trail:**
```bash
python cli.py verify-audit
```

**Launch REST API server:**
```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `Patient_ID` | Patient identifier | Required |
| `v1` | Primary measurement (LOH) | Required |
| `v2` | Secondary measurement (TAI) | Required |
| `v3` | Tertiary measurement (LST) | Required |

---

## Mathematical Formulation

The composite score is calculated as:

```
score = v1 + v2/2 + v3/3 + ...
```

Classification tiers:
- **Low / Standard** (score < 10.0): Standard monitoring
- **Moderate / Intermediate** (10.0 <= score < 25.0): Close observation
- **High / Severe** (score >= 25.0): Urgent clinical intervention

---

## Security

- **Zero-PHI Outbound Guard:** Blocks SSNs, MRNs, phone numbers, emails, and patient names from outbound data.
- **HMAC-SHA256 Audit Trail:** Cryptographic chain of signed log entries.
- **Secure Key Generation:** Uses `secrets.token_hex()` for cryptographically secure random key generation when no `AUDIT_SECRET_KEY` environment variable is set.

Set a persistent audit key via environment variable:
```bash
export AUDIT_SECRET_KEY="your-secure-key-here"
```

---

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov

# Run simulation benchmark
python simulator.py 1000
```

---

## Docker Deployment

```bash
# Build and run with Docker Compose
docker compose up --build

# Or manually
docker build -t hrd-genomic-scar-score .
docker run -p 8000:8000 --env AUDIT_SECRET_KEY=your-key hrd-genomic-scar-score
```

---

## Project Structure

```
hrd-genomic-scar-score/
├── hrd_scar.py          # Core algorithm (zero dependencies)
├── cli.py               # Enterprise CLI interface
├── simulator.py         # Stress testing simulator
├── enrichment.py        # Feature enrichment engines
├── agents/
│   ├── __init__.py      # Package init
│   ├── base.py          # Security, PHI guard, audit trail
│   ├── models.py        # Pydantic data models
│   ├── supervisor.py    # Multi-worker orchestrator
│   ├── workers.py       # Specialized evaluation workers
│   ├── api.py           # FastAPI REST endpoints
│   ├── llm_factory.py   # LLM provider factory
│   ├── metrics.py       # Prometheus metrics collector
│   ├── streamer.py      # WebSocket telemetry
│   └── learning.py      # Bayesian calibration engine
├── tests/               # Test suite
├── web/                 # Web operations console
├── sample.csv           # Sample input data
├── benchmark_dataset.json # Benchmark test cases
├── Dockerfile           # Container build
├── docker-compose.yml   # Container orchestration
└── pyproject.toml       # Project metadata and dependencies
```
