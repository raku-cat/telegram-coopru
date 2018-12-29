#!/usr/bin/env python3
import sys
import requests
import telepot, telepot.aio
import json
import asyncio
from time import sleep
from telepot.aio.loop import MessageLoop
from telepot.aio.helper import InlineUserHandler, AnswererMixin
from telepot.namedtuple import InlineQueryResultPhoto, InlineQueryResultVideo, InlineQueryResultGif

with open(sys.path[0] + '/keys.json', 'r') as f:
    key = json.load(f)
bot = telepot.aio.Bot(key['telegram'])

async def on_inline_query(msg):
    query_id, from_id, query_string, query_offset = telepot.glance(msg, flavor='inline_query', long=True)

    rest_headers={'content-type':'application/json', 'accept':'application/json'}

    if not query_offset:
        query_offset = 0

    if not query_string:
        query_string = ''

    request_uri = 'https://coopr.ru/api/posts/?limit=50&query={q}&offset={o}'.format(q=query_string, o=str(query_offset))
    get_posts = requests.get(request_uri, headers=rest_headers)

    if get_posts.status_code == 200:
        posts_json = get_posts.json()
    else:
        return

    def compute():
        listobj = []
        for p in posts_json['results']:
            caption_text = '[coopr.ru](https://coopr.ru/post/' + str(p['id']) + ')'
            if len(p['tags']) > 0:
                caption_text += ': '
                tag_list = []
                for i in p['tags']:
                    tag_list.append('[#' + i['names'][0] + '](https://www.coopr.ru/posts/query=' + i['names'][0] + ')')
                caption_text += ', '.join(tag_list)
            post_id = str(p['id'])
            post_mime = p['mimeType']
            post_thumb = p['thumbnailUrl']
            post_cont = p['contentUrl']
            if post_mime == 'image/jpeg':
                listobj.append(InlineQueryResultPhoto(
                    id=post_id, photo_url=post_cont,
                    thumb_url=post_thumb, caption=caption_text,
                    parse_mode='Markdown'
                    )
                )
            elif post_mime == 'image/gif':
                listobj.append(InlineQueryResultGif(
                    id=post_id, gif_url=post_cont,
                    thumb_url=post_thumb, caption=caption_text,
                    parse_mode='Markdown'
                    )
                )
            elif post_mime == 'video/mp4':
                listobj.append(InlineQueryResultVideo(
                    id=post_id, video_url=post_cont,
                    thumb_url=post_thumb, caption=caption_text,
                    mime_type='video/mp4', parse_mode='Markdown',
                    title=post_id
                    )
                )
        if query_offset == 0:
            if posts_json['total'] > 50:
                posts_offset = query_offset + 50
            else:
                posts_offset = ''
        else:
            pre_next_offset = int(query_offset) + 50
            if pre_next_offset < posts_json['total']:
                posts_offset = pre_next_offset
            else:
                posts_offset = ''
        return { 'results' : listobj, 'cache_time' : 1, 'next_offset' : str(posts_offset) }
    answerer.answer(msg, compute)

answerer = telepot.aio.helper.Answerer(bot)
loop = asyncio.get_event_loop()
loop.create_task(MessageLoop(bot,{'chat' : None,
                  'inline_query' : on_inline_query}).run_forever())
print('Started...')
loop.run_forever()