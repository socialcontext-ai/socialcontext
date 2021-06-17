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
logger.setLevel(logging.DEBUG)


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
        self, method: str, url: str, data: dict = None, **query
    ) -> requests.Response:
        logger.debug(f"Fetching URL {url}; method: {method}")
        if data is not None:
            logger.debug(f"data: {data}")
        if query:
            logger.debug(f"query: {query}")
        querystr = urllib.parse.urlencode(query)
        try:
            if method == "get":
                resp = self.client.get(f"{url}?{querystr}")
            elif method == "post":
                resp = self.client.post(url, json=data)
            elif method == "put":
                resp = self.client.put(url, json=data)
            elif method == "delete":
                resp = self.client.delete(url, json=data)
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
            if method == "get":
                return self.client.get(f"{url}?{querystr}")
            elif method == "post":
                return self.client.post(url, json=data)
            elif method == "put":
                return self.client.put(url, json=data)
            elif method == "delete":
                return self.client.delete(url, json=data)
            else:
                raise Exception("Unsupported dispatch method")

    def get(self, url: str, **query) -> requests.Response:
        r = self.dispatch("get", url, **query)
        return r

    def post(self, url: str, data=None) -> requests.Response:
        return self.dispatch("post", url, data=data)

    def put(self, url: str, data=None) -> requests.Response:
        return self.dispatch("put", url, data=data)

    def delete(self, url: str) -> requests.Response:
        return self.dispatch("delete", url)

    def pathget(self, path: str, version: str = VERSION, **query) -> requests.Response:
        prefix = self.prefix(version)
        url = f"{prefix}/{path}"
        return self.get(url, **query)

    def pathpost(
        self, path: str, version: str = VERSION, data: dict = None
    ) -> requests.Response:
        prefix = self.prefix(version)
        url = f"{prefix}/{path}"
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
        content_type: str = "news",
        input_file: str = None,
        output_path: str = None,
        models: List[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        options: List[str] = None,
        version: str = VERSION,
    ) -> requests.Response:
        """Create a batch processing job."""
        if models is None:
            models = []
        if options is None:
            options = []
        if input_file is None:
            raise Exception("Input file required.")
        r = self.pathpost(
            "jobs",
            version,
            data={
                "content_type": content_type,
                "input_file": input_file,
                "output_path": output_path,
                "batch_size": batch_size,
                "options": options,
                "models": models,
            },
        )
        return r

    def update_job(
        self, job_name: str, *, version: str = VERSION, **data
    ) -> requests.Response:
        """Update a pre-defined job."""
        r = self.pathput(f"jobs/{job_name}", version, data=data)
        return r

    def delete_job(self, job_name: str, *, version: str = VERSION) -> requests.Response:
        """Delete a job."""
        r = self.pathdelete(f"jobs/{job_name}", version)
        return r

    def jobs(
        self, *, job_name: str = None, version: str = VERSION
    ) -> requests.Response:
        """List jobs or show details of a specified job."""
        if job_name:
            r = self.pathget(f"jobs/{job_name}", version)
        else:
            r = self.pathget(f"jobs", version)
        return r

    def models(self) -> requests.Response:
        """List supported inference models."""
        return self.pathget("models")
