# socialcontext

Client library for the socialcontext.ai web API

```
 $ pip install git+https://github.com/socialcontext-ai/socialcontext.git
```


## Usage


### Instantiate a client

```
>>> from socialcontext.api import SocialcontextClient
>>> client = SocialcontextClient(APPLICATION_ID, APPLICATION_SECRET)
```


### Classify the content of a web page

```
>>> url = 'https://www.cnn.com/2020/11/24/politics/biden-cabinet-nominees-event/index.html'
>>> resp = client.classify(url=url)
```

### Classify text

```
>>> text = "Pope Francis Appoints First African-American Cardinal Wilton Gregory, the archbishop of Washington, was among 13 new cardinals named on Sunday."
>>> resp = client.classify('news', models=['diversity', 'crime_violence', text=text)
```

## Development

```
 $ pip install -e '.[test]'
```

