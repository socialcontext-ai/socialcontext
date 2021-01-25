"""
Based on the Webster client implementation:
https://github.com/scott2b/Webster/tree/main/client
"""
from enum import Enum
from typing import List, Optional
import asyncio
import json
import os
import typer
from .api import SocialcontextClient

VERSION = 'v0.1a'


app_id = os.environ['SOCIALCONTEXT_APP_ID']
app_secret = os.environ['SOCIALCONTEXT_APP_SECRET']

app = typer.Typer()

_client = None
def client():
    global _client
    if _client is None:
        print('instantiating new client')
        _client = SocialcontextClient(app_id, app_secret)
    return _client


class ContentTypes(str, Enum):
    news = 'news'


class Models(str, Enum):
    antivax = 'antivax'
    crime_violence = 'crime_violence'
    diversity = 'diversity'
    injuries = 'injuries'
    military = 'military'
    political = 'political'
    profanity = 'profanity'
    provax = 'provax'
    sexually_explicit = 'sexually_explicit'
    vice = 'vice'


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
     

@app.command()
def version():
    """Get the API verson."""
    typer.echo(VERSION)


@app.command()
def openapi():
    """Get the openapi specification."""
    r = client().openapi()
    output(r.json())


@app.command()
def classify(
    content_type: ContentTypes=typer.Argument(..., help="Content type", autocompletion=complete_content_type),
    url: str = typer.Option("", help="Web URL to classify"),
    text: str = typer.Option("", help="Text to classify"),
    models: List[Models] = typer.Argument(..., help="classification models")
):
    """Classify provided text or text extracted from a provided URL.

    One of either --url or --text must be provided.
    """
    if url:
        r = client().classify(content_type, models=models, url=url)
    elif text:
        r = client().classify(content_type, models=models, text=text)
    else:
        typer.echo(typer.style("Either url or text is required.",
            fg=typer.colors.RED, bold=True))
        raise typer.Exit()
    output(r.json())


### Stress test. Internal use only

from concurrent.futures import ThreadPoolExecutor

def do_classify(text):
    import time
    start = time.time() 
    from .api import models
    r = client().news.classify(models=models, text=text)
    output(r.json())
    duration = round(time.time() - start, 2)
    print(f'Fetched 1 in {duration} seconds')


@app.command()
def stress(filename:str):
    """Stress test the API."""
    import time
    start = time.time()
    with open(filename) as f:
        texts = f.read().split('\n\n')
        texts = [t.strip() for t in texts if t.strip()]
    with ThreadPoolExecutor() as executor:
        fn = do_classify
        executor.map(do_classify, texts)
    #for text in texts:
    #    do_classify(text)
    #    time.sleep(5)
    duration = round(time.time() - start, 2)
    print(f'Completed classifying all paragraphs of War and Peace in {duration} seconds.')


def run():
    app()
