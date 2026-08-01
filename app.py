# Debug Vercel Headers v4
from collector_web.app import app
import json

@app.route("/app.py")
@app.route("/debug-headers")
def debug_headers():
    from flask import request
    data = {}
    for k, v in sorted(request.environ.items()):
        if k.startswith("HTTP_") or k in ("PATH_INFO", "REQUEST_URI", "RAW_URI", "SCRIPT_NAME", "SERVER_NAME", "SERVER_PORT", "REQUEST_METHOD", "QUERY_STRING"):
            try:
                data[k] = str(v)
            except Exception:
                data[k] = repr(v)
    return json.dumps(data, indent=2), 200, {"Content-Type": "application/json"}


