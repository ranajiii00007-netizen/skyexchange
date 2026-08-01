# Force Vercel Redeploy v3
from collector_web.app import app
import json

@app.route("/debug-headers")
def debug_headers():
    from flask import request
    import os
    data = {
        "PATH_INFO": request.environ.get("PATH_INFO"),
        "REQUEST_URI": request.environ.get("REQUEST_URI"),
        "RAW_URI": request.environ.get("RAW_URI"),
        "SCRIPT_NAME": request.environ.get("SCRIPT_NAME"),
        "HTTP_headers": {
            k: v for k, v in request.environ.items()
            if k.startswith("HTTP_") or k in ("PATH_INFO", "REQUEST_URI", "RAW_URI", "SCRIPT_NAME", "SERVER_NAME", "SERVER_PORT")
        }
    }
    return json.dumps(data, indent=2, default=str), 200, {"Content-Type": "application/json"}

class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Try multiple Vercel headers to find the original path
        for header in ('HTTP_X_FORWARDED_PATH', 'HTTP_X_FORWARDED_URI', 'HTTP_X_INVOKE_PATH', 'HTTP_X_REAL_PATH', 'HTTP_X_ORIGINAL_URL'):
            val = environ.get(header)
            if val:
                environ['PATH_INFO'] = val.split('?')[0]
                break
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)

