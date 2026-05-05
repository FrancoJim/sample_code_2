# BEA Economic Data Pipeline

![CI](https://github.com/kjlang/sample_code_2/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python automation pipeline that pulls economic datasets from the [Bureau of Economic Analysis (BEA) REST API](https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf), writes timestamped snapshots to disk as CSV and Pickle, and uploads them to AWS S3.

Demonstrates practical patterns for:
- Wrapping an external REST API with clean error handling and type hints
- Managing cloud storage (S3) via `boto3` with full create / list / upload / teardown lifecycle
- Parameterized CLI tooling (`argparse`) in place of hardcoded config
- Integration testing with mocked AWS (`moto`) and mocked HTTP (`unittest.mock`) — no live credentials required
- Containerized dev environment with LocalStack for local S3 (no AWS account needed to develop)
- GitHub Actions CI pipeline: lint → test → docker build, gated in sequence

---

## Quick Start

**Fastest path — devcontainer (recommended):**

```bash
git clone <repo>
cd sample_code_2

cp example.env .env
# Add your BEA_API_KEY to .env (free — see Prerequisites below)

# Open in Cursor or VS Code → Cmd+Shift+P → "Dev Containers: Reopen in Container"
# LocalStack S3 starts automatically. AWS credentials are pre-configured.
```

**Without Docker:**

```bash
cp example.env .env          # fill in BEA_API_KEY and AWS credentials
make install
make test
python -m sample_2.main --bucket my-bucket --dataset gdp --year 2023
```

---

## Project Structure

```
sample_code_2/
├── sample_2/
│   ├── main.py               # CLI entrypoint (argparse)
│   └── libs/
│       ├── utils.py          # BEA_Wrapper — REST API client + DataFrame output
│       └── storages.py       # AwsS3 — create / upload / list / delete
├── tests/
│   └── test_sample.py        # 14 tests: BEA API (mocked HTTP) + S3 (moto)
├── .devcontainer/
│   ├── Dockerfile            # Ubuntu 22.04 + Python + Docker CLI + AWS CLI
│   ├── docker-compose.yml    # devcontainer service + LocalStack S3
│   └── scripts/
│       ├── post-create.sh    # installs deps, configures AWS CLI, seeds S3 bucket
│       └── devcontainer-ps1.sh  # custom PS1: repo | branch | path
├── .github/workflows/ci.yml  # lint → test → docker build
├── Dockerfile-{dev,prod,test}
├── docker-compose.yml        # app profiles: dev / prod / test
├── Makefile
├── pyproject.toml            # ruff + black + isort config
└── .pre-commit-config.yaml
```

---

## Architecture

```
BEA REST API  (https://apps.bea.gov/api/data)
      │
      ▼
BEA_Wrapper                      sample_2/libs/utils.py
      │  list_datasets()          → DataFrame of all available datasets
      │  fetch_gdp_by_industry()  → DataFrame of GDP by industry for a given year
      │
      ▼
Local disk                        ./data/<timestamp>.<dataset>.{csv,pkl}
      │
      ▼
AwsS3                            sample_2/libs/storages.py
      │  create_bucket()
      │  copy_to_bucket()
      │  list_bucket_files()
      │  delete_bucket_and_contents()
      │
      ▼
AWS S3  (or LocalStack in dev)
```

---

## Stack

| Layer | Tech |
|---|---|
| Language | Python 3.10 |
| HTTP client | `requests` |
| Data | `pandas` |
| Cloud storage | `boto3` / AWS S3 |
| Local AWS | LocalStack 3 (S3) |
| Packaging | Docker (Alpine), docker compose |
| Testing | `pytest`, `moto` (S3), `unittest.mock` (BEA API) |
| Linting | `ruff`, `black`, `isort`, `pre-commit` |
| CI/CD | GitHub Actions |
| Dev environment | VS Code / Cursor devcontainer (Ubuntu 22.04) |

---

## Prerequisites

### BEA API key (required, free)

1. Register at [apps.bea.gov/API/signup](https://apps.bea.gov/API/signup/)
2. Click the activation link in the confirmation email
3. Add the key to `.env`:
   ```
   BEA_API_KEY=your_key_here
   ```

### AWS credentials

**Devcontainer** — not required. LocalStack provides a local S3 endpoint and credentials are pre-configured as `test`/`test`.

**Local / production** — add real credentials to `.env`:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

---

## Usage

### CLI

```bash
# Fetch GDP by Industry for 2023 → save locally → upload to S3
python -m sample_2.main --bucket my-bucket --dataset gdp --year 2023

# List all available BEA datasets instead
python -m sample_2.main --bucket my-bucket --dataset datasets

# Change output directory
python -m sample_2.main --bucket my-bucket --dataset gdp --dest /tmp/bea

# Tear down the S3 bucket and all objects
python -m sample_2.main --bucket my-bucket --delete-bucket
```

| Flag | Default | Description |
|---|---|---|
| `--bucket` | *(required)* | S3 bucket name |
| `--dest` | `./data` | Local output directory |
| `--dataset` | `gdp` | `gdp` or `datasets` |
| `--year` | `2023` | Year for GDP data |
| `--delete-bucket` | — | Delete bucket and all objects, then exit |

### Docker (app images)

```bash
make run-dev      # development — source mounted for live edits
make run-prod     # production build
make docker-test  # run test suite in container
```

---

## Testing

```bash
make test
```

No live AWS credentials or BEA API key needed. All external calls are mocked.

| Class | What's tested |
|---|---|
| `TestBEAWrapper` | `list_datasets()` parses response into DataFrame; request URL is HTTPS and contains no `&amp;` entities; `fetch_gdp_by_industry()` extracts rows correctly |
| `TestAwsS3` | `create_bucket()` creates and is idempotent; `copy_to_bucket()` + `list_bucket_files()` round-trip; `delete_bucket_and_contents()` tears down; safe no-op on missing bucket |

---

## Devcontainer

A fully configured [devcontainer](https://containers.dev/) is included for VS Code and Cursor. Opens into a ready-to-use Ubuntu 22.04 environment — LocalStack S3 starts automatically, AWS CLI is pre-pointed at it, and a default bucket is created.

**What's inside the image:**

| | |
|---|---|
| OS | Ubuntu 22.04 |
| Python | 3.10, pip, poetry |
| AWS | CLI v2 + boto3; LocalStack S3 at `http://localstack:4566` |
| Docker | CLI + Compose plugin (mounts OrbStack / Docker socket) |
| Linting | ruff, black, isort, pre-commit |
| Shell | `repo \| branch \| path $` prompt |

**Open:**

```
Cmd+Shift+P → "Dev Containers: Reopen in Container"
```

Or via Make:

```bash
make dc-build   # build image
make dc-up      # start devcontainer + localstack
make dc-shell   # attach a bash shell
make dc-down    # stop and remove containers
```

**LocalStack S3 inside the container:**

`AWS_ENDPOINT_URL=http://localstack:4566` is set automatically — both `aws` CLI and `boto3` use it without extra flags:

```bash
aws s3 ls                                                        # list buckets
aws s3 ls s3://sample-sized-bucket-local                        # list objects

python -m sample_2.main --bucket sample-sized-bucket-local --dataset gdp
```

Port `4566` is forwarded to the host, so you can also hit LocalStack from outside the container:

```bash
aws --endpoint-url http://localhost:4566 s3 ls
```

To switch to real AWS, set `AWS_ENDPOINT_URL=` (empty string) in `.env`.

---

## Linting & pre-commit

```bash
make lint            # ruff + black --check + isort --check
make lint-fix        # auto-fix everything
make pre-commit-install   # install git hooks
```

Hooks run on every `git commit`: ruff (with autofix), black, isort.

Config lives in [`pyproject.toml`](pyproject.toml) (`[tool.ruff]`, `[tool.black]`, `[tool.isort]`).

---

## CI/CD

GitHub Actions runs on every push and pull request to `master`. Jobs are gated in sequence:

```
lint  →  test  →  docker build
```

1. **lint** — `ruff check`, `black --check`, `isort --check`
2. **test** — `pytest` with mocked AWS and BEA API (no credentials needed)
3. **docker-build** — builds `Dockerfile-prod` and `Dockerfile-test`

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
