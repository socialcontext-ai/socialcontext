"""
Batch job management commands.
"""
import json
import os
import re
import sys
from os.path import expanduser
from typing import List, Optional
from .utils import ContentTypes, complete_content_type, output, Models
from .utils import VERSION, BATCHES_BUCKET, client
import typer

from .api import DEFAULT_BATCH_SIZE, MIN_BATCH_SIZE, MAX_BATCH_SIZE

app = typer.Typer(help="Batch job managment commands.")


@app.command('list')
def list_():
    """List batch jobs for account."""
    r = client().jobs()
    output(r.json())


@app.command()
def info(
    job_name: str = typer.Argument(..., help="Job name.")
):
    """Show details for a job specified by name."""
    r = client().jobs(job_name=job_name)
    output(r.json())


@app.command()
def create(
    job_name: str = typer.Option(None, help="Job name. Must be unique to account."),
    content_type: ContentTypes=typer.Option("news", help="Content type. Currently only news is supported.", autocompletion=complete_content_type),
    input_file: str = typer.Argument(..., help="File containing URLs. Must be readable by the socialcontext batch system."),
    output_path: str = typer.Option(None, help="Location to write output files.  Must be writeable by the socialcontext batch system."),
    batch_size: int = typer.Option(DEFAULT_BATCH_SIZE, help=f"Size of written data batches between {MIN_BATCH_SIZE} and {MAX_BATCH_SIZE}. " \
        "Numbers out of range will be coerced to the valid minimum or maximum value without error"),
    profile: str = typer.Option(None, help="Read optons from a ~/.socialcontext.json profile"),
    options: Optional[List[str]] = typer.Option(None, help="Options reserved for administrative use."),
    models: List[Models] = typer.Argument(None, help="Classification models")
):
    """Submit a job for batch processing.

    The job name is optional. If not provided, it will be created according to
    the following pattern, based on the input file path:

    s3://{Bucket}/{OrganizationName}/{JobName}/{InputFile}

    If a job name is explicitly provided, it must meet the following criteria:
      * May include forward slashes (/) in order to create a path-like
        hierarchy of job organization.
      * Must be a valid S3 key subpath name
      * Spaces are not allowed and will be replaced with underscores (_)

    If an output path is not specified, the location of the input file will be used.
    The output path must be a writeable location by the socialcontext batch system.

    A profile may be specified which is a named key at profiles.[profile_name]
    in the ~/.socialcontext.json file. Profiles currently supports a model key
    which contains a list of models that will be merged with any models
    specified on the command line.
    """
    models = list(models) or []
    options = list(options) or []
    if profile:
        home = expanduser("~")
        cfg = json.load(open(os.path.join(home, '.socialcontext.json')))
        profile_info = cfg.get('profiles', {})[profile]
        models += profile_info.get('models', []) 
        models = list(set(models))
        options += profile_info.get('options', [])
        options = list(set(options))
    if job_name is None:
        account_info = client().account_info().json()
        organization = account_info['data'].get('orgName')
        if organization is None:
            message = 'Implicit job naming requires account to be configured ' \
                'with an organization name. Please contact support.'
            typer.echo(typer.style(message, fg=typer.colors.RED, bold=True))
            typer.echo(message)
            sys.exit()
        pattern = re.compile(f's3://{BATCHES_BUCKET}/{organization}/(.+)/(?:.+)')
        match = pattern.match(input_file)
        if match is None:
            message = f"""
Implicit job naming is currently only supported for input files of the format:

    s3://{BATCHES_BUCKET}/{organization}/JOB_NAME/INPUT_FILE

If your input file does not match this scheme, please specify the job name with
the --job-name parameter.
"""
            typer.echo(typer.style("\nInvalid implicit job name.",
                fg=typer.colors.RED, bold=True))
            typer.echo(message)
            sys.exit()
        job_name = match.group(1)
    if output_path is None:
        output_path = '/'.join(input_file.split('/')[:-1])
    info = {
        'input_file': input_file,
        'content_type': content_type,
        'output_path': output_path,
        'batch_size': batch_size,
        'models': models,
        'options': options
    }
    r = client().create_job(job_name, **info)
    output(r.json())


@app.command()
def run(
    job_name: str = typer.Argument(..., help="The unique name of the job.""")
):
    """Execute a pre-defined batch job by name."""
    r = client().run_job(job_name)
    output(r.json())


@app.command()
def cancel(
    job_name: str = typer.Argument(..., help="The unique name of the job.""")
):
    """Cancel a running job."""
    info = { 'action': 'cancel' }
    r = client().update_job(job_name, **info)
    output(r.json())


@app.command()
def delete(
    job_name: str = typer.Argument(..., help="The unique name of the job.""")
):
    """Delete a job."""
    r = client().delete_job(job_name)
    output(r.json())
