import json
import os
from enum import Enum
from .api import SocialcontextClient


VERSION = 'v0.1a'
BATCHES_BUCKET = 'socialcontext-batches'

app_id = os.environ['SOCIALCONTEXT_APP_ID']
app_secret = os.environ['SOCIALCONTEXT_APP_SECRET']


_client = None
def client():
    global _client
    if _client is None:
        _client = SocialcontextClient(app_id, app_secret)
    return _client


class ContentTypes(str, Enum):
    news = 'news'


def complete_content_type(incomplete: str):
    for name in ContentTypes:
        if name.startswith(incomplete):
            yield (name, help_text)



def output(data, *, filename=None, indent=4):
    if filename is None:
        s = json.dumps(data, indent=indent, ensure_ascii=False).encode('utf-8')
        print(s.decode())
    if filename is not None:
        with open(filename, 'w', encoding='utf8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
     

class Models(str, Enum):
    antivax = 'antivax'
    crime_violence = 'crime_violence'
    diversity = 'diversity'
    elite = 'elite'
    emerging = 'emerging'
    fake_news = 'fake_news'
    female_sports = 'female_sports'
    fetch_error = 'fetch_error'
    gender_equality = 'gender_equality'
    injuries = 'injuries'
    latinx = 'latinx'
    lgbt = 'lgbt'
    low_cred = 'low_cred'
    male_sports = 'male_sports'
    military = 'military'
    online_partisan = 'online_partisan'
    political = 'political'
    profanity = 'profanity'
    provax = 'provax'
    renewable_energy = 'renewable_energy'
    sexually_explicit = 'sexually_explicit'
    traditional = 'traditional'
    vice = 'vice'
    wire = 'wire'
