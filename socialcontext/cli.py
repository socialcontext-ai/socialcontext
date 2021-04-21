"""
Based on the Webster client implementation:
https://github.com/scott2b/Webster/tree/main/client
"""
from enum import Enum
from typing import List, Optional
import asyncio
import json
import os
from gzip import GzipFile
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


@app.command()
def batch(
    content_type: ContentTypes=typer.Argument(..., help="Content type", autocompletion=complete_content_type),
    location: str = typer.Argument(..., help="Location of the batch content to classify"),
    models: List[Models] = typer.Argument(..., help="classification models")):
    """Create a batch classification job."""
    r = client().batch(content_type, location=location, models=models)
    output(r.json())


@app.command()
def job(
    content_type: ContentTypes=typer.Argument(..., help="Content type", autocompletion=complete_content_type),
    job_id: int = typer.Argument(..., help="The numeric ID of the job")):
    """Get the current status of a news batch job."""
    r = client().batch_job(content_type, job_id)
    output(r.json())


# s3

_s3_resource = None

def s3_resource():
    import boto3
    global _s3_resource
    if _s3_resource is None:
        _s3_resource = boto3.resource('s3')
    return _s3_resource


def s3_client():
    resource = s3_resource()
    return resource.meta.client


def parse_path(path):
    assert path.startswith('s3://'), f'Invalid s3 path: {path}'
    bucket = path.split('/')[2]
    key = '/'.join(path.split('/')[3:]).strip('/')
    return bucket, key


def iterate_file(bucket, key, encoding='utf-8'):
    obj = s3_resource().Object(bucket, key).get()['Body']
    if key.endswith('.gz'):
        obj = GzipFile(None, 'rb', fileobj=obj)
        for line in obj:
            yield line.decode(encoding).strip()
    else:
        for line in obj.iter_lines():
            yield line.decode(encoding).strip()


@app.command()
def download(
    path: str = typer.Argument(..., help="s3 output folder to download"),
    file_: str = typer.Argument(..., metavar='FILE', help="file to write to"),
):
    """Download the data and errors from an output location."""
    bucket, key = parse_path(path)
    response = s3_client().list_objects(
        Bucket=bucket,
        Prefix=key
    )
    data_files = []
    error_files = []
    for item in response.get('Contents', []):
        key = item['Key']
        name = key.split('/')[-1]
        if name.startswith('data-'):
            data_files.append(key)
        elif name.startswith('errors-'):
            error_files.append(key)
    data_files = sorted(data_files)
    error_files = sorted(error_files)
    with open(file_, 'w') as outfile:
        for df_i, key in enumerate(data_files):
            fn = f's3://{bucket}/{key}'
            for i, line in enumerate(iterate_file(bucket, key)):
                if df_i > 0 and i == 0: # skip headers after the first file
                    continue
                outfile.write(f'{line}\n')


@app.command()
def upload(
    file_: str = typer.Argument(..., metavar='FILE', help="File to be upload as urls.txt"),
    path: str = typer.Argument(..., help="S3 job path"),
):
    """Upload a file of URLs as a new job file."""
    bucket, key = parse_path(path)
    key = key.strip('/') + '/urls.txt'
    s3_client().upload_file(file_, bucket, key)
    print(f'Uploaded: s3://{bucket}/{key}')


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
