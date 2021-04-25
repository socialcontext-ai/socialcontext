"""
Batch job management commands.
"""
import re
import sys
from typing import List, Optional
from .utils import ContentTypes, complete_content_type, output, Models
from .utils import VERSION, BATCHES_BUCKET, client
import typer

app = typer.Typer(help="Batch job managment commands.")



@app.command()
def list():
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
    """
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
