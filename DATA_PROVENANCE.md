# Data provenance

The files in `backend/data/` are copied from the original DATATHON Track 4 dataset supplied to the team.

Runtime behavior:
- Dashboard values come from the FastAPI backend only.
- No silent mock-data fallback is used.
- Uploading five CSVs to `POST /analyze` replaces the active analysis in memory and retrains the Isolation Forest.
- `dev_tools/generate_data.py` is retained only as a development utility and is not part of the normal demo path.
