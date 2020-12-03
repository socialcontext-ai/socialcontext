import base64
import dbm
import json
import logging
import urllib
import oauthlib
import requests
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from functools import partial
from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests_oauthlib import OAuth2Session

logger = logging.getLogger('socialcontext')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

class InvalidRequest(Exception):
    ...

class Unauthorized(Exception):
    ...

KEY_DB = Path(__file__).parent / 'key'


all_models = [
    'crime_violence',
    'diversity',
    'injuries',
    'military',
    'political',
    'profanity',
    'sexually_explicit',
    'vice',
]


class SocialcontextClient():

    API_ROOT = 'http://localhost:8000'
    #API_ROOT = 'https://beta.socialcontext.ai'

    VER = {
        '': API_ROOT,
        'v0.1a': f'{API_ROOT}/v0.1a',
        'v0.1': f'{API_ROOT}/v0.1',
    }
    TOKEN_URL = f'{VER["v0.1"]}/token'
    REFRESH_URL = f'{VER["v0.1"]}/token-refresh'
    _news = None

    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
        try:
            token = self.load_saved_token()
        except KeyError:
            token = self.fetch_api_token()
            self.token_saver(token)
        self.client = self.create_client_for_token(token)

    def fetch_api_token(self):
        backend = BackendApplicationClient(client_id=self.app_id)
        oauth = OAuth2Session(client=backend)
        try:
            token = oauth.fetch_token(
                token_url=self.TOKEN_URL,
                client_id=self.app_id,
                client_secret=self.app_secret,
                include_client_id=True)
        except MissingTokenError:
            # oauthlib gives the same error regardless of the problem
            print('Something went wrong, please check your client credentials.')
            exit()
        return token

    def create_client_for_token(self, token):
        return OAuth2Session(
            self.app_id,
            token=token,
            auto_refresh_url=self.REFRESH_URL,
            auto_refresh_kwargs={},
            token_updater=self.token_saver)

    def token_saver(self, token):
        logger.debug('SAVING TOKEN: %s' % str(token))
        code = bytearray(self.app_secret, 'utf8')[:32]
        code = base64.urlsafe_b64encode(code)
        data = json.dumps(token)
        data = data.encode()
        f = Fernet(code)
        _t = f.encrypt(data)
        decrypted = json.loads(f.decrypt(_t))
        with dbm.open(KEY_DB.as_posix(), 'c') as db:
            db[self.app_id] = _t

    def load_saved_token(self):
        with dbm.open(KEY_DB.as_posix(), 'c') as db:
            token = db[self.app_id]
        code = bytearray(self.app_secret, 'utf8')[:32]
        code = base64.urlsafe_b64encode(code)
        f = Fernet(code)
        token = json.loads(f.decrypt(token))
        return token

    def clear_saved_token(self):
        with dbm.open(KEY_DB.as_posix(), 'c') as db:
            if self.app_id in db:
                del(db[self.app_id]) 

    def dispatch(self, method, url, data=None, **query):
        query = urllib.parse.urlencode(query)
        try:
            if method =='get':
                return self.client.get(f'{url}?{query}')
            elif method == 'post':
                return self.client.post(url, json=data)
            else:
                raise Exception('Unsupported dispatch method')
        except oauthlib.oauth2.rfc6749.errors.MissingTokenError:
            logger.error('API Token error. Attempting to re-create client')
            self.clear_saved_token()
            token = self.fetch_api_token()
            self.token_saver(token)
            self.client = self.create_client_for_token(token)
            if method == 'get':
                return self.client.get(f'{url}?{query}')
            elif method == 'post':
                return self.client.post(url, json=data)
            else:
                raise Exception('Unsupported dispatch method')

    def get(self, url, **query):
        return self.dispatch('get', url, **query)

    def post(self, url, data=None):
        return self.dispatch('post', url, data=data)

    def pathget(self, path, version='', **query):
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.get(url, **query) 

    def pathpost(self, path, version='', data=None):
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.post(url, data=data)

    def classify(self, content_type, *, models=None, url=None, text=None, version='v0.1a'):
        if url:
            reqtype = 'url'
            content = url
        elif text:
            reqtype = 'text'
            content = text
        else:
            raise InvalidRequest('url or text parameter required')
        r = self.pathpost(f'{content_type}/classify', version, data={
            reqtype: content, 'models': models
        })
        if r.status_code == 403:
            raise Unauthorized
        return r

    @property
    def news(self):
        if self._news is None:
            self._news = type('news', (object,), {
                'classify': partial(self.classify, 'news')
            })
        return self._news()
