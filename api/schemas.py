"""drf-spectacular OpenApi extensions for the API.

Registers security-scheme extensions for custom authentication classes so the
generated OpenAPI schema can describe them instead of warning "could not
resolve authenticator".
"""

from __future__ import annotations

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .authentication import ExpiringTokenAuthentication, SessionAuthentication


class SessionAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = SessionAuthentication
    name = "sessionAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "sessionid",
            "description": "Django session cookie for the sales admin website.",
        }


class ExpiringTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = ExpiringTokenAuthentication
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Token",
            "description": "Expiring bearer token used by the Android app.",
        }
