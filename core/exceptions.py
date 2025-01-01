from rest_framework.exceptions import APIException
from rest_framework import status

class TokenError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Invalid or expired token'
    default_code = 'token_invalid'

class TokenMissing(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication credentials were not provided'
    default_code = 'token_missing'