"""Container health check: exit 0 if /v1/health answers 200, else 1.

Used by the Dockerfile HEALTHCHECK and by Coolify's CMD health check. It is a file rather
than an inline `python -c` because Coolify rejects quotes and brackets in health check
commands. Standard library only, so the slim runtime image needs no curl or wget.
"""

import os
import sys
import urllib.request

# Same rule as start.sh's ${PORT:-8000}: an empty PORT counts as unset.
port = os.environ.get("PORT") or "8000"
url = f"http://127.0.0.1:{port}/v1/health"
# Connect directly: a stray http_proxy (without 127.0.0.1 in no_proxy) must not send
# the local probe through a proxy.
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open(url, timeout=4) as response:  # noqa: S310 (fixed local URL)
        sys.exit(0 if response.status == 200 else 1)
except Exception:  # noqa: BLE001 (any failure means unhealthy)
    sys.exit(1)
