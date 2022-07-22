import base64
import dbm
import json
import logging
import urllib
import oauthlib
import os
import sys
import requests
import urllib.parse
from typing import List, Optional, Union
from pathlib import Path
from cryptography.fernet import Fernet
from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2.rfc6749.errors import MissingTokenError
from requests_oauthlib import OAuth2Session

VERSION = "v1"

DEFAULT_BATCH_SIZE = 1000
MIN_BATCH_SIZE = 500
MAX_BATCH_SIZE = 5000

logger = logging.getLogger("socialcontext")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


class InvalidRequest(Exception):
    ...


class Unauthorized(Exception):
    ...


class MissingToken(Exception):
    ...


KEY_DB = Path(__file__).parent / ".key"


class SocialcontextClient:

    API_ROOT = os.environ.get("SOCIALCONTEXT_API_ROOT", "https://api.socialcontext.ai")
    TOKEN_URL = f"{API_ROOT}/{VERSION}/token"
    REFRESH_URL = f"{API_ROOT}/{VERSION}/token-refresh"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        try:
            token = self.load_saved_token()
        except KeyError:
            token = self.fetch_api_token()
            self.token_saver(token)
        self.client = self.create_client_for_token(token)

    def prefix(self, version: str) -> str:
        return f"{self.API_ROOT}/{version}"

    def fetch_api_token(self) -> dict:
        backend = BackendApplicationClient(client_id=self.app_id)
        oauth = OAuth2Session(client=backend)
        try:
            token = oauth.fetch_token(
                token_url=self.TOKEN_URL,
                client_id=self.app_id,
                client_secret=self.app_secret,
                include_client_id=True,
            )
        except MissingTokenError:
            # oauthlib gives the same error regardless of the problem
            print("Something went wrong, please check your client credentials.")
            raise
        return token

    def create_client_for_token(self, token: dict) -> OAuth2Session:
        return OAuth2Session(
            self.app_id,
            token=token,
            auto_refresh_url=self.REFRESH_URL,
            auto_refresh_kwargs={},
            token_updater=self.token_saver,
        )

    def fernet(self, key: str) -> Fernet:
        key = key + "=" * (len(key) % 4)
        _key = base64.urlsafe_b64encode(base64.urlsafe_b64decode(key))
        return Fernet(_key)

    def encrypt(self, data: str) -> bytes:
        return self.fernet(self.app_secret).encrypt(data.encode())

    def decrypt(self, data: bytes) -> bytes:
        return self.fernet(self.app_secret).decrypt(data)

    def token_saver(self, token: dict) -> None:
        logger.debug("SAVING TOKEN: %s" % str(token))
        data = json.dumps(token)
        _t = self.encrypt(data)
        with dbm.open(KEY_DB.as_posix(), "c") as db:
            db[self.app_id] = _t

    def load_saved_token(self) -> dict:
        with dbm.open(KEY_DB.as_posix(), "c") as db:
            _token = db[self.app_id]
        token = json.loads(self.decrypt(_token))
        return token

    def clear_saved_token(self) -> None:
        with dbm.open(KEY_DB.as_posix(), "c") as db:
            if self.app_id in db:
                del db[self.app_id]

    def dispatch(
        self, _method: str, _url: str, data: dict = None, **query
    ) -> requests.Response:
        logger.debug(f"Fetching URL {_url}; method: {_method}")
        if data is not None:
            logger.debug(f"data: {data}")
        if query:
            logger.debug(f"query: {query}")
        querystr = urllib.parse.urlencode(query)
        try:
            if _method == "get":
                resp = self.client.get(f"{_url}?{querystr}")
            elif _method == "post":
                resp = self.client.post(_url, json=data)
            elif _method == "put":
                resp = self.client.put(_url, json=data)
            elif _method == "delete":
                resp = self.client.delete(_url, json=data)
            else:
                raise Exception("Unsupported dispatch method")
            if resp.status_code in [400, 401, 403]:
                raise MissingToken
            return resp
        except (oauthlib.oauth2.rfc6749.errors.MissingTokenError, MissingToken):
            self.clear_saved_token()
            token = self.fetch_api_token()
            self.token_saver(token)
            self.client = self.create_client_for_token(token)
            if _method == "get":
                return self.client.get(f"{_url}?{querystr}")
            elif _method == "post":
                return self.client.post(_url, json=data)
            elif _method == "put":
                return self.client.put(_url, json=data)
            elif _method == "delete":
                return self.client.delete(_url, json=data)
            else:
                raise Exception("Unsupported dispatch method")

    def get(self, _url: str, **query) -> requests.Response:
        r = self.dispatch("get", _url, **query)
        return r

    def post(self, _url: str, data=None) -> requests.Response:
        return self.dispatch("post", _url, data=data)

    def put(self, _url: str, data=None) -> requests.Response:
        return self.dispatch("put", _url, data=data)

    def delete(self, _url: str) -> requests.Response:
        return self.dispatch("delete", _url)

    def pathget(self, path: str, version: str = VERSION, **query) -> requests.Response:
        prefix = self.prefix(version)
        _url = f"{prefix}/{path}"
        return self.get(_url, **query)

    def pathpost(
        self, path: str, version: str = VERSION, data: dict = None
    ) -> requests.Response:
        prefix = self.prefix(version)
        url = f"{prefix}/{path}"
        print("POST:", data)
        return self.post(url, data=data)

    def pathput(
        self, path: str, version: str = VERSION, data: dict = None
    ) -> requests.Response:
        prefix = self.prefix(version)
        url = f"{prefix}/{path}"
        return self.put(url, data=data)

    def pathdelete(self, path: str, version: str = VERSION) -> requests.Response:
        prefix = self.prefix(version)
        url = f"{prefix}/{path}"
        return self.delete(url)

    # API endpoints

    def create_job(
        self,
        *,
        job_name:str = "",
        content_models: List[str] = None,
        domain_models: List[str] = None,
        options: List[str] = None,
        version: str = VERSION,
        urls: List[str]
    ) -> requests.Response:
        """Create a batch processing job."""
        if content_models is None:
            content_models = []
        if domain_models is None:
            domain_models = []
        if options is None:
            options = []
        r = self.pathpost(
            "jobs",
            version,
            data={
                "job_name": job_name,
                "options": options,
                "content_models": content_models,
                "domain_models": domain_models,
                "urls": urls
            }
        )
        return r

    def update_job(
        self, job_id: str, *, version: str = VERSION, **data
    ) -> requests.Response:
        """Update a pre-defined job."""
        r = self.pathput(f"jobs/{job_id}", version, data=data)
        return r

    def delete_job(self, job_id: str, *, version: str = VERSION) -> requests.Response:
        """Delete a job."""
        r = self.pathdelete(f"jobs/{job_id}", version)
        return r

    def jobs(
        self, *, job_id: str = None, version: str = VERSION
    ) -> requests.Response:
        """List jobs or show details of a specified job."""
        if job_id:
            r = self.pathget(f"jobs/{job_id}", version)
        else:
            r = self.pathget(f"jobs", version)
        return r

    def models(self) -> requests.Response:
        """List supported inference models."""
        return self.pathget("classification/models")

    def classify(self, content_type, content_models=None, domain_models=None, url=None, text=None) -> requests.Response:
        """Classify a url for the given models."""
        if not content_models and not domain_models:
            raise InvalidRequest("At least one of content_models or domain_models must be provided.")
        if url:
            return self.pathpost("classification/classify-content", data={
                "url": url,
                "text": text,
                "content_models": content_models,
                "domain_models": domain_models
            }
        )
        elif text:
            if domain_models:
                raise InvalidRequest("url must be specified in order to include domain_models.")
            return self.pathpost("classification/classify-content", data={
                "text": text,
                "content_models": content_models })
        else:
            raise InvalidRequest("Either url or text must be provided.")
