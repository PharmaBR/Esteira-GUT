from django_htmx.http import HttpResponseClientRedirect

# Every script and stylesheet is served from our own static files, so the
# policy can forbid inline code and third-party origins outright.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "img-src 'self' data:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        return response


class HtmxRedirectMiddleware:
    """Turn redirects answering htmx requests into full-page navigations.

    Without this, an expired session would swap the login page into the
    middle of the board instead of sending the browser to it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.htmx and response.status_code in (301, 302, 303, 307, 308):
            return HttpResponseClientRedirect(response.headers["Location"])
        return response
