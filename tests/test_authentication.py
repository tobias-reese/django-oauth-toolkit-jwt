from datetime import datetime, timedelta
import json

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from rest_framework.test import APIClient

from oauth2_provider_jwt import utils


class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        User = get_user_model()
        User.objects.create_user(
            'temporary', 'temporary@gmail.com', 'temporary')

    def test_get_no_jwt_header(self):
        """
        If there is no auth, it's part of a different layer if user needs
        to be authenticated. That's why we return a positive response.
        """
        response = self.client.get('/jwt/')
        self.assertEqual(response.status_code, 200)

    def test_get_no_jwt_token_failing_jwt_auth(self):
        response = self.client.get('/jwt/', HTTP_AUTHORIZATION='JWT')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.content,
            b'{"detail":"Invalid Authorization header. No credentials provided."}')  # noqa

    def test_get_invalid_jwt_header(self):
        response = self.client.get('/jwt/', HTTP_AUTHORIZATION='JWT bla bla')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.content,
            b'{"detail":"Invalid Authorization header. Credentials string should not contain spaces."}')  # noqa

    def test_get_invalid_jwt_header_one_arg(self):
        response = self.client.get('/jwt/', HTTP_AUTHORIZATION='JWT bla.bla')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.content,
            b'{"detail":"Incorrect authentication credentials."}')

    @override_settings(JWT_AUTH_DISABLED=True)
    def test_post_valid_jwt_header(self):
        now = datetime.utcnow()
        payload = {
            'iss': 'issuer',
            'exp': now + timedelta(seconds=100),
            'iat': now,
            'sub': 'subject',
            'usr': 'some_usr',
            'org': 'some_org',
        }
        jwt_value = utils.encode_jwt(payload)

        response = self.client.post(
            '/jwt/', {'example': 'example'},
            HTTP_AUTHORIZATION='JWT {}'.format(jwt_value),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        sessionkeys_expected = {}
        try:
            items = payload.iteritems()
        except AttributeError:  # python 3.6
            items = payload.items()
        for k, v in items:
            if k not in ('exp', 'iat'):
                sessionkeys_expected['jwt_{}'.format(k)] = v
        self.assertEqual(json.loads(response.content), sessionkeys_expected)

    def test_post_valid_jwt_with_auth(self):
        now = datetime.utcnow()
        payload = {
            'iss': 'issuer',
            'exp': now + timedelta(seconds=100),
            'iat': now,
            'username': 'temporary',
        }
        jwt_value = utils.encode_jwt(payload)

        with override_settings(JWT_AUTH_DISABLED=False):
            response = self.client.post(
                '/jwt_auth/', {'example': 'example'},
                HTTP_AUTHORIZATION='JWT {}'.format(jwt_value),
                content_type='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                json.loads(response.content), {'username': 'temporary'})

        with override_settings(JWT_AUTH_DISABLED=True):
            response = self.client.post(
                '/jwt_auth/', {'example': 'example'},
                HTTP_AUTHORIZATION='JWT {}'.format(jwt_value),
                content_type='application/json')
            self.assertEqual(response.status_code, 403)

    def test_post_valid_jwt_with_auth_and_scope_not_valid(self):
        now = datetime.utcnow()
        payload = {
            'iss': 'issuer',
            'exp': now + timedelta(seconds=100),
            'iat': now,
            'username': 'temporary',
            'scope': 'read',  # Incorrect scope
        }
        jwt_value = utils.encode_jwt(payload)
        response = self.client.post(
            '/jwt_auth_scope/', {'example': 'example'},
            HTTP_AUTHORIZATION='JWT {}'.format(jwt_value),
            content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_post_valid_jwt_with_auth_and_scope_is_valid(self):
        now = datetime.utcnow()
        payload = {
            'iss': 'issuer',
            'exp': now + timedelta(seconds=100),
            'iat': now,
            'username': 'temporary',
            'scope': 'write',  # Correct scope
        }
        jwt_value = utils.encode_jwt(payload)
        response = self.client.post(
            '/jwt_auth_scope/', {'example': 'example'},
            HTTP_AUTHORIZATION='JWT {}'.format(jwt_value),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)


class ECDSAJWTAuth(JWTAuthenticationTests):
    @override_settings(JWT_ENC_ALGORITHM="ES256")
    @override_settings(JWT_PRIVATE_KEY_ISSUER="""-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAaAAAABNlY2RzYS
1zaGEyLW5pc3RwMjU2AAAACG5pc3RwMjU2AAAAQQTRAzrSN7dFmGa05mrQaKfP2xplEFo/
1InJc3P+pcy1zgN427Y96mmPMMkx1zBk9S0uDFX5WlEJ9UuRxmf+yceVAAAAsJLFlSOSxZ
UjAAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNEDOtI3t0WYZrTm
atBop8/bGmUQWj/Uiclzc/6lzLXOA3jbtj3qaY8wyTHXMGT1LS4MVflaUQn1S5HGZ/7Jx5
UAAAAhAJlPEfG7s+7zces2RHc1txeyyjwZxCqUqs25kvtO36nrAAAAFnRob21hc0B3b3Jr
c3RhdGlvbi1kZWIB
-----END OPENSSH PRIVATE KEY-----""")
    @override_settings(JWT_PUBLIC_KEY_ISSUER="ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNEDOtI3t0WYZrTmatBop8/bGmUQWj/Uiclzc/6lzLXOA3jbtj3qaY8wyTHXMGT1LS4MVflaUQn1S5HGZ/7Jx5U= thomas@workstation-deb")  # noqa: E501
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        User = get_user_model()
        User.objects.create_user(
            'temporary', 'temporary@gmail.com', 'temporary')
