"""Write the OpenAPI schema into packages/api-client. Run via `just gen-client`."""

import json
import sys
from pathlib import Path

from app.main import create_app

out = Path(sys.argv[1] if len(sys.argv) > 1 else "../../packages/api-client/openapi.json")
_ = out.write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
print(f"wrote {out}")
