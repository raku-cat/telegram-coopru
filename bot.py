#!/usr/bin/env python3
import sys
import requests
import telepot, telepot.aio
import json
import asyncio
from time import sleep
from telepot.aio.loop import MessageLoop
from telepot.aio.helper import InlineUserHandler, AnswererMixin
from telepot.namedtuple import InlineQueryResultPhoto

with open(sys.path[0] + '/keys.json', 'r') as f:
    key = json.load(f)
bot = telepot.aio.Bot(key['telegram'])

async def on_inline_query(msg):
    query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')

    rest_headers={'content-type':'application/json', 'accept':'application/json'}
    if not query_string.isspace():
        get_posts = requests.get('https://coopr.ru/api/posts/?limit=50&query=' + query_string, headers=rest_headers)
    else:
        get_posts = requests.get('https://coopr.ru/api/posts/?limit=50', headers=rest_headers)

    if get_posts.status_code == 200:
        post_list = get_posts.json()

    def compute():
        listobj = []
        for p in get_posts.json()['results']:
            caption_text = '[coopr.ru](https://coopr.ru/post/' + str(p['id']) + ')'
            if len(p['tags']) > 0:
                caption_text += ': '
                tag_list = []
                for i in p['tags']:
                    tag_list.append('[#' + i['names'][0] + '](https://www.coopr.ru/posts/query=' + i['names'][0] + ')')
                caption_text += ', '.join(tag_list)
            listobj.append(InlineQueryResultPhoto(
                id=str(p['id']), photo_url=p['contentUrl'],
                thumb_url=p['thumbnailUrl'], caption=caption_text,
                parse_mode='Markdown'
                )
            )
        return { 'results' : listobj, 'cache_time' : 1 }
    answerer.answer(msg, compute)

answerer = telepot.aio.helper.Answerer(bot)
loop = asyncio.get_event_loop()
loop.create_task(MessageLoop(bot,{'chat' : None,
                  'inline_query' : on_inline_query}).run_forever())
print('Started...')
loop.run_forever()