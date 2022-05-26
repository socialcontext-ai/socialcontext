"""
Based on the Webster client implementation:
https://github.com/scott2b/Webster/tree/main/client
"""
from enum import Enum
from typing import List
from gzip import GzipFile
import typer
from .utils import ContentTypes, complete_content_type, output, Models, cache_models
from .utils import VERSION, client
from . import jobs


app = typer.Typer()
app.add_typer(jobs.app, name="jobs")


@app.command()
def version():
    """Get the API verson."""
    typer.echo(VERSION)


@app.command()
def models():
    """Get the list of currently supported classification models."""
    output(cache_models())


@app.command()
def classify(
    content_type: ContentTypes = typer.Option(
        "news",
        help="Content type. Currently only news is supported.",
        autocompletion=complete_content_type,
    ),
    url: str = typer.Option("", help="Web URL to classify."),
    text: str = typer.Option("", help="Text to classify."),
    #models: List[Models()] = typer.Argument(..., help="classification models"),
    content_model: List[str] = typer.Option("", help="Content model(s)."),
    domain_model: List[str] = typer.Option("", help="Domain model(s).")
    #models: List[str] = typer.Argument(..., help="classification models"),
):
    """Classify provided text or text extracted from a provided URL.

    One of either --url or --text must be provided. --text will be ignored if --url is
    provided (the content will be extracted from the URL in this case).

    To specify multiple content models, pass --content_model multiple times or specify
    a comma separated list of models (E.g. `--content-model climate_action,diversity`)

    To specify multiple domain models, pass --domain_model multiple times or specify
    a comma separated list of models (E.g. `--domain-model traditional,elite`)
    """
    #models = [m.value for m in models]
    content_models = []
    for m in content_model:
        content_models += m.split(",")
    domain_models = []
    for m in domain_model:
        domain_models += m.split(",")
    if domain_models and not url:
        typer.echo(
            typer.style(
                "WARNING: Domain model(s) provided without URL. The following "
                f"--domain-model parameter(s) will be ignores: {domain_models}",
                fg=typer.colors.YELLOW, bold=True
            )
        )
        domain_models = []
    if not content_models and not domain_models: 
        typer.echo(
            typer.style(
                "Either content-model or domain-model is required.", fg=typer.colors.RED, bold=True
            )
        )
        raise typer.Exit()
    if url and text:
        typer.echo(
            typer.style(
                "WARNING: --url and --text both provided. --text will be ignored. "
                "Content will be extracted from the URL.",
                fg=typer.colors.YELLOW, bold=True
            )
        )
    if url:
        r = client().classify(content_type, content_models=content_models, domain_models=domain_models, url=url)
    elif text:
        r = client().classify(content_type, content_models=content_models, text=text)
    else:
        typer.echo(
            typer.style(
                "Either url or text is required.", fg=typer.colors.RED, bold=True
            )
        )
        raise typer.Exit()
    output(r.json())


# s3

_s3_resource = None


def s3_resource():
    import boto3

    global _s3_resource
    if _s3_resource is None:
        _s3_resource = boto3.resource("s3")
    return _s3_resource


def s3_client():
    resource = s3_resource()
    return resource.meta.client


def parse_path(path):
    assert path.startswith("s3://"), f"Invalid s3 path: {path}"
    bucket = path.split("/")[2]
    key = "/".join(path.split("/")[3:]).strip("/")
    return bucket, key


def iterate_file(bucket, key, encoding="utf-8"):
    obj = s3_resource().Object(bucket, key).get()["Body"]
    if key.endswith(".gz"):
        obj = GzipFile(None, "rb", fileobj=obj)
        for line in obj:
            yield line.decode(encoding).strip()
    else:
        for line in obj.iter_lines():
            yield line.decode(encoding).strip()


class DownloadFileTypes(str, Enum):
    data = "data"
    errors = "errors"


@app.command()
def download(
    path: str = typer.Argument(..., help="s3 output folder to download"),
    output_file: typer.FileTextWrite = typer.Option(None, help="Output file to write."),
    file_type: DownloadFileTypes = typer.Option(
        "data", help="Type of output files to download."
    ),
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
    response = s3_client.list_objects(Bucket=bucket, Prefix=path)
    files = []
    for item in response.get("Contents", []):
        key = item["Key"]
        name = key.split("/")[-1]
        if name.startswith(f"{file_type}-"):
            files.append(key)
    files = sorted(files)
    for df_i, key in enumerate(files):
        fn = f"s3://{bucket}/{key}"
        for i, line in enumerate(iterate_file(bucket, key)):
            if df_i > 0 and i == 0:  # skip headers after the first file
                continue
            if output_file:
                output_file.write(f"{line}\n")
            else:
                typer.echo(line)


def run():
    app()
