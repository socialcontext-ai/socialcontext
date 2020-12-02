import urllib
import requests
from functools import partial
from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests_oauthlib import OAuth2Session


class InvalidRequest(Exception):
    ...

class Unauthorized(Exception):
    ...


def token_saver(token):
    print('SAVING TOKEN:', token)


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


class Classifier:

    def __init__(self, client, namespace):
        self.client = client
        self.namespace = namespace

    def classify(self, *, url=None, text=None, models=None, version='v0.1a'):
        if url:
            reqtype = 'url'
            content = url
        elif text:
            reqtype = 'text'
            content = text
        else:
            raise InvalidRequest('url or text parameter required')
        if models is None:
            models = all_models
        r = self.client.pathpost(f'{self.namespace}/classify', version, data={
            reqtype: content,
            'models': models
        })
        if r.status_code == 403:
            raise Unauthorized
        return r


class APIClient():

    API_ROOT = 'http://localhost:8000'
    #API_ROOT = 'https://beta.socialcontext.ai'

    VER = {
        '': API_ROOT,
        'v0.1a': f'{API_ROOT}/v0.1a',
        'v0.1': f'{API_ROOT}/v0.1',
    }
    TOKEN_URL = f'{VER["v0.1a"]}/token'
    REFRESH_URL = f'{VER["v0.1"]}/token-refresh'

    def __init__(self, app_id, app_secret):
        self.app_id = app_id
        self.app_secret = app_secret
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
        self.client = OAuth2Session(
            self.app_id,
            token=token,
            auto_refresh_url=self.REFRESH_URL,
            auto_refresh_kwargs={},
            token_updater=token_saver)
        print(token)

    def get(self, url, **query):
        q = urllib.parse.urlencode(query)
        return self.client.get(f'{url}?{q}')

    def post(self, url, data=None):
        return self.client.post(url, json=data)

    def pathget(self, path, version='', **query):
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.get(url, **query) 

    def pathpost(self, path, version='', data=None):
        print('VER', self.VER)
        print('version', version)
        v = self.VER[version]
        url = f'{v}/{path}'
        return self.post(url, data=data)


    #def classify(self, content_type, *, url=None, text=None, version='v1.a'):
    #    if url:
    #        reqtype = 'url'
    #        content = url
    #    elif text:
    #        reqtype = 'text'
    #        content = text
    #    else:
    #        raise InvalidRequest('url or text parameter required')
    #    r = self.pathpost(f'{content_type}/classify', version, data={
    #        reqtype: content,
    #        'models': [
    #            'diversity',
    #            'vice',
    #            'political',
    #            'crime_violence',
    #            'injuries',
    #            'military',
    #            'profanity',
    #            'sexually_explicit'
    #        ]
    #    })
    #    if r.status_code == 403:
    #        raise Unauthorized
    #    return r

    #news = type('news', (object,), {
    #    'classify': partialmethod(classify, 'news') })
    #news = Classifier()

class SocialcontextClient():

    def __init__(self, app_id, app_secret):
        self.api = APIClient(app_id, app_secret)
        self.classifiers = {
            'news': Classifier(self.api, 'news')
        }
        self.news = self.classifiers['news']

    def classify(self, content_type, **kwargs):
        return self.classifiers[content_type].classify(**kwargs)

    def openapi(self):
        """Returns the openapi spec."""
        return self.api.pathget('docs/openapi.json')

