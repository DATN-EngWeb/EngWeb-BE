from .models import User

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken


class CustomTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            decoded_token = AccessToken(token)
            user_id = decoded_token.payload.get("user_id")

            if not user_id:
                raise AuthenticationFailed("Token does not contain user_id")

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise AuthenticationFailed("User does not exist")

            if user.status == "D":
                raise AuthenticationFailed("Account has been disabled")

            return (user, None)

        except Exception as e:
            raise AuthenticationFailed(f"Token expired or invalid: {str(e)}")
