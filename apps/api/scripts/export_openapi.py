"""Write the OpenAPI schema into packages/api-client. Run via `just gen-client`."""

import json
import sys
from pathlib import Path

from app.main import create_app

# Resolved from this file, not the working directory, so the export lands in
# packages/api-client no matter where the module is invoked from.
DEFAULT_OUT = Path(__file__).resolve().parents[3] / "packages" / "api-client" / "openapi.json"


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    _ = out.write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
