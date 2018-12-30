#!/usr/bin/env python3
import sys
import requests
import telepot, telepot.aio
import json
import asyncio, aiofiles
import regex
from telepot.aio.loop import MessageLoop
from telepot.aio.helper import InlineUserHandler, AnswererMixin
from telepot.namedtuple import InlineQueryResultPhoto, InlineQueryResultVideo, InlineQueryResultGif

with open(sys.path[0] + '/keys.json', 'r') as f:
    key = json.load(f)
users_file = sys.path[0] + '/users.json'
bot = telepot.aio.Bot(key['telegram'])

async def on_command(msg):
    content_type, chat_type, chat_id, msg_date, msg_id = telepot.glance(msg, long=True)
    from_id = str(msg['from']['id'])

    try:
       botcom = msg['entities'][0]['type']
       if not botcom == 'bot_command':
           return
    except KeyError:
       return
    if content_type != 'text':
       return

    raw_msg = msg['text'].lower()
    command = raw_msg.split(' ', 1)[0]
    try:
        command_argument = raw_msg.split(' ', 1)[1]
    except IndexError:
        command_argument = None

    with open(users_file, 'r') as u:
        users_dict = json.loads(u.read())
    user_data = users_dict['users']

    if from_id in user_data:
        user_settings = user_data[from_id]
    else:
        user_data[from_id] = { 'safety' : '' }
        async with aiofiles.open(users_file, 'w') as u:
            await u.write(json.dumps(users_dict))
        user_settings = user_data[from_id]

    if regex.search(r'\/safety(\@Coopru_bot)?\Z', command) is not None and command_argument is not None:
        safeties = ['safe', 'sketchy', 'unsafe']

        await bot.sendChatAction(chat_id, 'typing')

        if command_argument in safeties:
            user_settings['safety'] = command_argument
            async with aiofiles.open(users_file, 'w') as u:
                await u.write(json.dumps(users_dict))
            await bot.sendMessage(chat_id, 'Search safety set to ' + command_argument + '!')
        else:
            await bot.sendMessage(chat_id, 'Sorry, that\'s not a valid safety')

    elif regex.search(r'\/nosafe(\@Coopru_bot)?\Z', command) is not None:
        await bot.sendChatAction(chat_id, 'typing')

        user_settings['safety'] = ''
        async with aiofiles.open(users_file, 'w') as u:
                await u.write(json.dumps(users_dict))

        await bot.sendMessage(chat_id, 'Search safety cleared!')


async def on_inline_query(msg):
    query_id, from_id, query_string, query_offset = telepot.glance(msg, flavor='inline_query', long=True)
    from_id = str(from_id)

    if not query_offset:
        query_offset = 0
    if not query_string:
        query_string = ''

    with open(users_file, 'r') as u:
        users_dict = json.loads(u.read())['users']

    if from_id in users_dict:
        user_settings = users_dict[from_id]
        query_safety = user_settings['safety']
        query_string = query_string + ' safety:' + query_safety
    else:
        pass


    rest_headers={'content-type':'application/json', 'accept':'application/json'}
    request_uri = 'https://coopr.ru/api/posts/?limit=50&query={q}&offset={o}'.format(q=query_string, o=str(query_offset))
    get_posts = requests.get(request_uri, headers=rest_headers)

    if get_posts.status_code == 200:
        posts_json = get_posts.json()
    else:
        return

    def compute():
        listobj = []

        for p in posts_json['results']:
            post_id = str(p['id'])
            post_mime = p['mimeType']
            post_thumb = p['thumbnailUrl']
            post_cont = p['contentUrl']
            caption_text = '[coopr.ru](https://coopr.ru/post/' + post_id + ')'

            if len(p['tags']) > 0:
                caption_text += ': '
                tag_list = []
                for i in p['tags']:
                    tag_list.append('[#' + i['names'][0] + '](https://www.coopr.ru/posts/query=' + i['names'][0] + ')')
                caption_text += ', '.join(tag_list)

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

        return { 'results' : listobj, 'cache_time' : 1, 'next_offset' : str(posts_offset), 'is_personal' : 'true' }

    answerer.answer(msg, compute)

answerer = telepot.aio.helper.Answerer(bot)
loop = asyncio.get_event_loop()
loop.create_task(MessageLoop(bot,{'chat' : on_command,
                  'inline_query' : on_inline_query}).run_forever())
print('Started...')
loop.run_forever()