import base64
import dbm
import json
import logging
import urllib
import oauthlib
import os
import requests
import sys
from pathlib import Path
from cryptography.fernet import Fernet
from functools import partial
from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests_oauthlib import OAuth2Session

DEFAULT_BATCH_SIZE = 1000
MIN_BATCH_SIZE = 500
MAX_BATCH_SIZE = 5000

logger = logging.getLogger('socialcontext')
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

class InvalidRequest(Exception):
    ...

class Unauthorized(Exception):
    ...

class MissingToken(Exception):
    ...


KEY_DB = Path(__file__).parent / 'key'


models = [
    'antivax',
    'climate_action',
    'crime_violence',
    'diversity',
    'elite',
    'emerging',
    'fake_news',
    'female_sports',
    'fetch_error',
    'gender_equality',
    'injuries',
    'latinx',
    'lgbt',
    'low_cred',
    'male_sports',
    'mental_health',
    'military',
    'online_partisan',
    'political',
    'profanity',
    'provax',
    'renewable_energy',
    'sexually_explicit',
    'traditional',
    'vice',
    'wire'
]


class SocialcontextClient():

    API_ROOT = os.environ.get(
        'SOCIALCONTEXT_API_ROOT',
        'https://beta.socialcontext.ai')

    VER = {
        '': API_ROOT,
        'v0.1a': f'{API_ROOT}/v0.1a',
        'v0.1': f'{API_ROOT}/v0.1',
        'v1': f'{API_ROOT}/v1'
    }
    TOKEN_URL = f'{VER["v1"]}/token'
    REFRESH_URL = f'{VER["v1"]}/token-refresh'
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
            raise
            exit()
        return token

    def create_client_for_token(self, token):
        return OAuth2Session(
            self.app_id,
            token=token,
            auto_refresh_url=self.REFRESH_URL,
            auto_refresh_kwargs={},
            token_updater=self.token_saver)

    def fernet(self, key):
        _key = key + "=" * (len(key) % 4)
        _key = base64.urlsafe_b64encode(base64.urlsafe_b64decode(_key))
        return Fernet(_key)

    def encrypt(self, data):
        return self.fernet(self.app_secret).encrypt(data.encode())

    def decrypt(self, data):
        return self.fernet(self.app_secret).decrypt(data)

    def token_saver(self, token):
        logger.debug('SAVING TOKEN: %s' % str(token))
        data = json.dumps(token)
        _t = self.encrypt(data)
        with dbm.open(KEY_DB.as_posix(), 'c') as db:
            db[self.app_id] = _t

    def load_saved_token(self):
        with dbm.open(KEY_DB.as_posix(), 'c') as db:
            try:
                token = db[self.app_id]
            except KeyError:
                return None
        token = json.loads(self.decrypt(token))
        return token

    def clear_saved_token(self):
        with dbm.open(KEY_DB.as_posix(), 'c') as db:
            if self.app_id in db:
                del(db[self.app_id]) 

    def dispatch(self, method, url, data=None, **query):
        query = urllib.parse.urlencode(query)
        try:
            if method =='get':
                resp = self.client.get(f'{url}?{query}')
            elif method == 'post':
                resp = self.client.post(url, json=data)
            elif method == 'put':
                resp = self.client.put(url, json=data)
            elif method == 'delete':
                resp = self.client.delete(url, json=data)
            else:
                raise Exception('Unsupported dispatch method')
            if resp.status_code == 400:
                raise MissingToken
            return resp
        except (oauthlib.oauth2.rfc6749.errors.MissingTokenError, MissingToken):
            self.clear_saved_token()
            token = self.fetch_api_token()
            self.token_saver(token)
            self.client = self.create_client_for_token(token)
            if method == 'get':
                return self.client.get(f'{url}?{query}')
            elif method == 'post':
                return self.client.post(url, json=data)
            elif method == 'put':
                return self.client.put(url, json=data)
            elif method == 'delete':
                return self.client.delete(url, json=data)
            else:
                raise Exception('Unsupported dispatch method')

    def get(self, url, **query):
        r = self.dispatch('get', url, **query)
        return r

    def post(self, url, data=None):
        return self.dispatch('post', url, data=data)

    def put(self, url, data=None):
        return self.dispatch('put', url, data=data)

    def delete(self, url):
        return self.dispatch('delete', url)

    def pathget(self, path, version='', **query):
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.get(url, **query) 

    def pathpost(self, path, version='', data=None):
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.post(url, data=data)

    def pathput(self, path, version='', data=None):
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.put(url, data=data)

    def pathdelete(self, path, version=''):
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.delete(url)

    # API endpoints

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

    def account_info(self, version='v0.1a'):
        """Get info for user account."""
        r = self.pathget('account', version)
        return r


    def create_job(self, *, content_type='news', input_file=None,
              output_path=None, models=None, batch_size=DEFAULT_BATCH_SIZE,
              options=None, version='v1'):
        """Create a batch processing job."""
        if models is None:
            models = []
        if options is None:
            options = []
        if input_file is None:
            raise Exception('Input file required.')
        r = self.pathpost('jobs', version, data={
            'content_type': content_type,
            'input_file': input_file,
            'output_path': output_path,
            'batch_size': batch_size,
            'options': options,
            'models': models
        })
        return r

    #def run_job(self, job_name, *, version='v0.1a'):
    #    """Create a job execution for a pre-defined job."""
    #    r = self.pathpost('executions', version, data={
    #        'job_name': job_name
    #    }) 
    #    return r

    def update_job(self, job_name, *, version='v1', **data):
        """Update a pre-defined job."""
        r = self.pathput(f'jobs/{job_name}', version, data=data)
        return r

    def delete_job(self, job_name, *, version='v1'):
        """Delete a job."""
        r = self.pathdelete(f'jobs/{job_name}', version)
        return r

    def jobs(self, *, job_name=None, version='v1'):
        """List jobs or show details of a specified job."""
        if job_name:
            r = self.pathget(f'jobs/{job_name}', version)
        else:
            r = self.pathget(f'jobs', version)
        return r

    def makeclient(self, client_name, version='v0.1'):
        r = self.pathpost('clients', version, data={
            'name': client_name}) 
        if r.status_code == 403:
            raise Unauthorized
        return r

    def clients(self, version='v0.1'):
        r = self.pathget('clients', version)
        if r.status_code == 403:
            raise Unauthorized
        return r

    @property
    def news(self):
        if self._news is None:
            self._news = type('news', (object,), {
                'classify': partial(self.classify, 'news'),
                'batch': partial(self.batch, 'news')
            })
        return self._news()
