"""Container health check: exit 0 if /v1/health answers 200, else 1.

Used by the Dockerfile HEALTHCHECK and by Coolify's CMD health check. It is a file rather
than an inline `python -c` because Coolify rejects quotes and brackets in health check
commands. Standard library only, so the slim runtime image needs no curl or wget.
"""

import os
import sys
import urllib.request

url = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}/v1/health"
try:
    with urllib.request.urlopen(url, timeout=4) as response:  # noqa: S310 (fixed local URL)
        sys.exit(0 if response.status == 200 else 1)
except Exception:  # noqa: BLE001 (any failure means unhealthy)
    sys.exit(1)
