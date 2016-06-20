# coding: utf-8
from __future__ import absolute_import, unicode_literals

import jwt
from django.contrib.auth import get_user_model
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _
from rest_framework import exceptions
from rest_framework.authentication import (
    BaseAuthentication, get_authorization_header
)

from rest_framework_sso.settings import api_settings

decode_jwt_token = api_settings.DECODE_JWT_TOKEN


class JWTAuthentication(BaseAuthentication):
    """
    JWT token based authentication.

    Clients should authenticate by passing the token key in the "Authorization"
    HTTP header, prepended with the string "JWT ".  For example:

        Authorization: JWT eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJsb2NhbG...
    """

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        authenticate_header = self.authenticate_header(request=request)

        if not auth or smart_text(auth[0].lower()) != authenticate_header.lower():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            payload = decode_jwt_token(token=token)
        except jwt.ExpiredSignature:
            msg = _('Signature has expired.')
            raise exceptions.AuthenticationFailed(msg)
        except jwt.DecodeError:
            msg = _('Error decoding signature.')
            raise exceptions.AuthenticationFailed(msg)
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed()

        return self.authenticate_credentials(payload=payload)

    def authenticate_credentials(self, payload):
        from rest_framework_sso.models import SessionToken

        user_model = get_user_model()

        if api_settings.VERIFY_SESSION_TOKEN:
            try:
                SessionToken.objects.active().get(pk=payload.get('sid'), user_id=payload.get('uid'))
            except SessionToken.DoesNotExist:
                raise exceptions.AuthenticationFailed(_('Invalid token.'))

        try:
            user = user_model.objects.get(pk=payload.get('uid'))
        except user_model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        return user, payload

    def authenticate_header(self, request):
        return api_settings.AUTHENTICATE_HEADER
