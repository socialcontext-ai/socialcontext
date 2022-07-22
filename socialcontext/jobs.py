"""
Batch job management commands.
"""
import json
import os
import re
import sys
from os.path import expanduser
from typing import List, Optional
from .utils import ContentTypes, output, Models
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
    job_id: str = typer.Argument(..., help="Job ID.")
):
    """Show details for a job specified by ID."""
    r = client().jobs(job_id=job_id)
    output(r.json())


@app.command()
def create(
    name: str = "",
    input_file: str = typer.Argument(..., help="File containing URLs."),
    profile: str = typer.Option(None, help="Read optons from a ~/.socialcontext.json profile"),
    options: Optional[List[str]] = typer.Option(None, help="Options reserved for administrative use."),
    content_model: List[str] = typer.Option("", help="Content model(s)."),
    domain_model: List[str] = typer.Option("", help="Domain model(s).")
):
    """Submit a job for batch processing.

    If an output path is not specified, the location of the input file will be used.
    The output path must be a writeable location by the socialcontext batch system.

    A profile may be specified which is a named key at profiles.[profile_name]
    in the ~/.socialcontext.json file. Profiles currently supports a model key
    which contains a list of models that will be merged with any models
    specified on the command line.
    """
    if content_model:
        content_models = [m.value for m in content_model]
    else:
        content_models = []
    if domain_model:
        domain_models = [m.value for m in domain_model]
    else:
        domain_models = []
    options = list(options) or []
    if profile:
        home = expanduser("~")
        cfg = json.load(open(os.path.join(home, '.socialcontext.json')))
        profile_info = cfg.get('profiles', {})[profile]
        content_models += profile_info.get('content_models', []) 
        content_models = list(set(content_models))
        domain_models += profile_info.get('domain_models', []) 
        domain_models = list(set(domain_models))
        options += profile_info.get('options', [])
        options = list(set(options))
    if input_file is None:
        raise Exception("Input file required.")
    with open(input_file) as infile:
        urls = [f.strip() for f in infile.read().split("\n") if f.strip()]
    info = {
        'job_name': name,
        'content_models': content_models,
        'domain_models': domain_models,
        'options': options,
        'urls': urls
    }
    r = client().create_job(**info)
    output(r.json())


@app.command()
def run(
    job_id: str = typer.Argument(..., help="The unique ID of the job.""")
):
    """Schedule a previously cancelled or failed batch job for execution."""
    info = { 'action': 'schedule' }
    r = client().update_job(job_id, **info)
    output(r.json())


@app.command()
def cancel(
    job_id: str = typer.Argument(..., help="The unique ID of the job.""")
):
    """Cancel a running job."""
    info = { 'action': 'cancel' }
    r = client().update_job(job_id, **info)
    output(r.json())


@app.command()
def delete(
    job_id: str = typer.Argument(..., help="The unique ID of the job.""")
):
    """Delete a job."""
    r = client().delete_job(job_id)
    output(r.json())
