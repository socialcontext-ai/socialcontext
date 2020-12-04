# -*- coding: utf-8 -*-
"""Example package/API queries
"""
import os
from socialcontext.api import SocialcontextClient


client = SocialcontextClient(
    os.environ['SOCIALCONTEXT_APP_ID'],
    os.environ['SOCIALCONTEXT_APP_SECRET']) 

bad_articles = []
MODELS = [
    'crime_violence',
    'profanity']

count = 0
with open('example_urls.txt') as f:
    for url in f:
        url = url.strip()
        if not url:
            continue
        print(f'Fetching: {url}')
        resp = client.news.classify(url=url, models=MODELS)
        print(resp.status_code)
        data = resp.json()
        print('Classifications:', data['classifications'])
        if any([cls > 0.5 for cls in
                data['classifications'].values() ]):
            bad_articles.append(data['source']['url'])
        count += 1

rate = len(bad_articles) / count
print(f'{len(bad_articles)} of {count} articles blocked for brand safety. Blockage rate: {rate:.2}')
