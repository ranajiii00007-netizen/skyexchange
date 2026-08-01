# Force Vercel Redeploy
from collector_web.app import app

class VercelPathMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        forwarded_path = environ.get('HTTP_X_FORWARDED_PATH')
        if forwarded_path:
            environ['PATH_INFO'] = forwarded_path
        else:
            forwarded_uri = environ.get('HTTP_X_FORWARDED_URI')
            if forwarded_uri:
                environ['PATH_INFO'] = forwarded_uri.split('?')[0]
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
