"""
Based on the Webster client implementation:
https://github.com/scott2b/Webster/tree/main/client
"""
from enum import Enum
from typing import List, Optional
import asyncio
import json
import sys
from gzip import GzipFile
import typer
from .utils import ContentTypes, complete_content_type, output, Models
from .utils import VERSION, BATCHES_BUCKET, client
from . import jobs


app = typer.Typer()
app.add_typer(jobs.app, name='jobs')


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
def models():
    """List supported classification inference models."""
    r = client().openapi()
    for model in r.json()['definitions']['ClassificationModelEnum']['enum']:
        typer.echo(model)


@app.command()
def classify(
    content_type: ContentTypes=typer.Option("news", help="Content type. Currently only news is supported.", autocompletion=complete_content_type),
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


#@app.command()
#def batch(
#    content_type: ContentTypes=typer.Argument(..., help="Content type", autocompletion=complete_content_type),
#    name: str = typer.Argument(..., help="Unique name for the news batch job"),
#    location: str = typer.Argument(..., help="Location of the batch content to classify"),
#    models: List[Models] = typer.Argument(..., help="classification models")):
#    """Create a batch classification job."""
#    org_name = 'ExampleOrg'
#    outpath = f's3://socialcontext-batches/{org_name}/News-{name}/output'
#    r = client().batch(content_type, location=location, name=name, output=outpath, models=models)
#    output(r.json())


#@app.command()
#def jobs(job_name: str = typer.Argument(None, help="A batch job name.")):
#    """Lists, information, and controls for batch jobs."""
#    if job_name:
#        r = client().jobs(job_name=job_name)
#        output(r.json())
#    else:
#        r = client().jobs()
#        output(r.json())
    


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


class DownloadFileTypes(str, Enum):
    data = 'data'
    errors = 'errors'


@app.command()
def download(
    path: str = typer.Argument(..., help="s3 output folder to download"),
    output_file: typer.FileTextWrite = typer.Option(None, help="Output file to write."),
    file_type: DownloadFileTypes = typer.Option(None, help="Type of output files to download.")
):
    """Download the output data from a batch job output location.  Downloads
    job output as a single stream and does the work of stripping CSV headers
    from all but the first file.

    Provided as a convenience for simplifying management of batch output CSV
    downloads to be consolidated. For general batch file management, the AWS
    CLI is recommended.
    """
    s3 = s3_resource()
    s3_client = s3.meta.client
    bucket, path = parse_path(path)
    path = path.rstrip('/') + '/'
    response = s3_client.list_objects(Bucket=bucket, Prefix=path)
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
    for df_i, key in enumerate(data_files):
        fn = f's3://{bucket}/{key}'
        for i, line in enumerate(iterate_file(bucket, key)):
            if df_i > 0 and i == 0: # skip headers after the first file
                continue
            if output_file:
                output_file.write(f'{line}\n')
            else:
                typer.echo(line)


#@app.command()
#def upload(
#    file_: str = typer.Argument(..., metavar='FILE', help="File to be upload as urls.txt"),
#    name: str = typer.Argument(..., help="Job name. Must be unique to account."),
#):
#    """Upload a file of URLs as a new job file."""
#    s3 = s3_resource()
#    client = s3.meta.client
#    org_name = 'ExampleOrg'
#    name = name.strip('/ .')
#    bucket = 'socialcontext-batches'
#    key = f'{org_name}/{name}/urls.txt'
#    try:
#        s3.Object(bucket, key).load()
#        typer.echo(typer.style(
#            f'News batch job file already exists: s3://{bucket}/{key}',
#            fg=typer.colors.RED, bold=True))
#        sys.exit()
#    except client.exceptions.ClientError as e:
#        if 'operation: Not Found' in str(e):
#            client.upload_file(file_, bucket, key)
#            typer.echo(f'Uploaded: s3://{bucket}/{key}')
#        else: 
#            raise


#@app.command()
#def files(
#    job_name: str = typer.Argument(None, help="Job name."),
#    organization: str = typer.Option(..., help="Organization name for socialcontext account", envvar="SOCIALCONTEXT_ORGANIZATION"),
#    content_type: ContentTypes=typer.Option("news", help="Content type. Currently only news is supported.", autocompletion=complete_content_type),
#):
#    """List batch job files. List the data files for a named job. If a job
#    name is not provided, the job paths containing urls.txt files will
#    be listed. The corresponding job name for listed job paths can be
#    determined from the URL format:
#
#        s3://{Bucket}/{OrganizationName}/{ContentType}/{JobName}
#
#    Job names may contain forward slashes (/).
#    """
#    s3 = s3_client()
#    if job_name:
#        prefix = f'{organization}/{content_type}/{job_name}'
#    else:
#        prefix = f'{organization}/{content_type}'
#    r = s3.list_objects_v2(Bucket=BATCHES_BUCKET, Prefix=prefix)
#    for f in r['Contents']:
#        key = f['Key']
#        if not job_name:
#            if key.endswith('/urls.txt'):
#                key = '/'.join(key.split('/')[:-1])
#            else:
#                continue
#        path = f's3://{BATCHES_BUCKET}/{key}'
#        typer.echo(path)
    

#def submit(
#    job_name: str = typer.Argument(..., help="Job name. Must be unique to account."),
#    organization: str = typer.Option(..., help="Organization name for socialcontext account", envvar="SOCIALCONTEXT_ORGANIZATION"),
#    content_type: ContentTypes=typer.Option("news", help="Content type. Currently only news is supported.", autocompletion=complete_content_type),
#    urls: str = typer.Option(..., help="File to be upload as urls.txt"),
#    execute: bool = typer.Option(False, help="Execute the job after completing the upload."),
#    models: List[Models] = typer.Argument(None, help="Classification models")
#):
#    """Upload a file of URLs as a new job file and submit the job for batch processing.
#    The file is written as urls.txt to the Job location, which is defined as:
#
#    s3://socialcontext-batches/{OrganizationName}/{ContentType}/{JobName}/
#
#    Job names may include forward slashes (/) in order to create a path-like
#    hierarchy of job organization. Job names must be valid S3 key names. Spaces
#    are not allowed and will be replaced with underscores (_).
#
#    After uploading the URLs file, the job is submitted to the socialcontext
#    API to initiate a new batch processing job. 
#
#    This command is the equivalent of both:
#      * uploading a urls.txt to a job-name specific s3 location, and
#      * initiating the job execution via `socialcontext exec`
#
#    Only one of `submit` or `exec` should be called for a given job.
#    """
#    s3 = s3_resource()
#    s3_client = s3.meta.client
#    job_name = job_name.strip('/ .').replace(' ', '_')
#    output_path = f'{organization}/{content_type}/{job_name}'
#    output_url = f's3://{BATCHES_BUCKET}/{output_path}'
#    input_key = f'{output_path}/urls.txt'
#    input_file = f's3://{BATCHES_BUCKET}/{input_key}'
#    try:
#        s3.Object(BATCHES_BUCKET, input_key).load()
#        typer.echo(typer.style(
#            f'News batch job file already exists: {input_file}',
#            fg=typer.colors.RED, bold=True))
#        sys.exit()
#    except s3_client.exceptions.ClientError as e:
#        if 'operation: Not Found' in str(e):
#            s3_client.upload_file(urls, BATCHES_BUCKET, input_key)
#            typer.echo(f'Uploaded: {input_file}')
#        else: 
#            raise
#    submit_kwargs = {
#        'input_file': input_file,
#        'content_type': content_type,
#        'output_path': output_url,
#        'models': models
#    }
#    if execute:
#        submit_kwargs['execute'] = True
#    r = client().submit(job_name, **submit_kwargs)
#    output(r.json())
#    if not execute:
#        typer.echo(f"""To execute job, run command:
#
#socialcontext exec {job_name}
#""")


def run():
    app()
