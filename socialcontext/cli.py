import typer
from .cli import SocialcontextClient

VERSION = '0.1.0'

app = typer.Typer()
client = SocialcontextClient()


@app.command()
def version(name: str):
    typer.echo(VERSION)


@app.command()
def classify(url: str):
    r = client.classify(url)
    print(r.status_code)
    print(r.json())


def run():
    app()
