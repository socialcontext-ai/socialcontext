import requests

API_ROOT = 'http://localhost:8000'
VER = {
    'v1.a': f'{API_ROOT}/v1.a'
}


class SocialcontextClient():

    def classify(self, url, version='v1.a'):
        _api = f'{VER[version]}/news/classify'
        return requests.post(_api, json={
            'url': url,
            'models': ['diversity']
        })
