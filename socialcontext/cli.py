import json
import os
import typer
from .api import SocialcontextClient

VERSION = '0.1.0'


app_id = os.environ['SOCIALCONTEXT_APP_ID']
app_secret = os.environ['SOCIALCONTEXT_APP_SECRET']

app = typer.Typer()
client = SocialcontextClient(app_id, app_secret)


@app.command()
def version():
    typer.echo(VERSION)



@app.command()
def classify(
    url: str = typer.Option("", help="Web URL to classify"),
    text: str = typer.Option("", help="Text to classify")
):
    if url:
        r = client.classify(url=url)
    elif text:
        r = client.classify(text=text)
    else:
        typer.echo(typer.style("Either url or text is required.",
            fg=typer.colors.RED, bold=True))
        raise typer.Exit()
    # If you are writing to a file, just use json.dump() and leave it to the file object to encode:
    # with open('filename', 'w', encoding='utf8') as json_file:
    #     json.dump("ברי צקלה", json_file, ensure_ascii=False)
    s = json.dumps(r.json(), indent=4, ensure_ascii=False).encode('utf-8')
    print(s.decode())




def run():
    app()
