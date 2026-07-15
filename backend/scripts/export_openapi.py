"""Regenerate shared/openapi.json from the live FastAPI app. Run whenever
routes/schemas change: `python scripts/export_openapi.py` from `backend/`."""

import json
from pathlib import Path

from src.main import app

if __name__ == "__main__":
    output_path = Path(__file__).resolve().parent.parent.parent / "shared" / "openapi.json"
    output_path.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote {output_path}")
