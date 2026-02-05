from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CustomTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CustomTokenAuthentication"
    name = "CustomBearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }

class CustomBasicAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CustomBasicAuthentication"
    name = "CustomBasicAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "basic",
        }