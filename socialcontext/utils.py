import json
import os
from enum import Enum
from pathlib import Path
from .api import SocialcontextClient, VERSION


BATCHES_BUCKET = "socialcontext-batches"
MODELS_CACHE = Path(__file__).parent / ".models"

app_id = os.environ["SOCIALCONTEXT_APP_ID"]
app_secret = os.environ["SOCIALCONTEXT_APP_SECRET"]


_client = None


def client():
    global _client
    if _client is None:
        _client = SocialcontextClient(app_id, app_secret)
    return _client


class ContentTypes(str, Enum):
    news = "news"


def complete_content_type(incomplete: str):
    for name in ContentTypes:
        if name.startswith(incomplete):
            yield (name, help_text)


def output(data, *, filename=None, indent=4):
    if filename is None:
        s = json.dumps(data, indent=indent, ensure_ascii=False).encode("utf-8")
        print(s.decode())
    if filename is not None:
        with open(filename, "w", encoding="utf8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)


def cache_models():
    r = client().models().json()
    with open(MODELS_CACHE, 'w') as f:
        json.dump(r, f)
    return r


_models = None
def Models():
    """Return an enum of supported models from the models cache."""
    global _models
    if _models is None:
        try:
            with open(MODELS_CACHE) as f:
                _models = json.load(f)["content_models"]
        except:
            _models = cache_models()["content_models"]
    return Enum("Models", { m["identifier"]:m["identifier"] for m in _models })
