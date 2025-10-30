# Local Testing Guide

## Quick Start

```bash
# Run with local-only output (no GCS upload)
python test_local.py

# Edit the script to enable GCS upload:
# Change: UPLOAD_TO_GCS = False
# To:     UPLOAD_TO_GCS = True
```

## Configuration

Edit these variables in `test_local.py`:

```python
UPLOAD_TO_GCS = False  # Set to True to upload to Google Cloud Storage
LOCAL_OUTPUT_DIR = "output"  # Directory to save JSON files locally
```

## Test Specific Dates

Uncomment and modify these lines in the `fetch_contracts()` function:

```python
# posted_from = "10/29/2025"
# posted_to = "10/29/2025"
```

## Output

- **Local files**: Saved to `output/` directory
- **GCS files**: Uploaded to `gs://your-bucket/contracts/` (if enabled)
- **Filenames**: Based on contract posting date (e.g., `contracts_20251029.json`)

## Requirements

- `.env` file with `SAM_API_KEY` (always required)
- `.env` file with `GCS_BUCKET_NAME` (only if `UPLOAD_TO_GCS = True`)
- Dependencies: `pip install -r requirements.txt`