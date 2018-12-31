#!/usr/bin/env python3
import sys
import requests
import telepot, telepot.aio
import json
import base64
import asyncio, aiofiles
from telepot.aio.loop import MessageLoop
from telepot.aio.helper import InlineUserHandler, AnswererMixin
from telepot.namedtuple import InlineQueryResultPhoto, InlineQueryResultVideo, InlineQueryResultGif, InlineKeyboardMarkup, InlineKeyboardButton

with open(sys.path[0] + '/keys.json', 'r') as f:
    key = json.load(f)
users_file = sys.path[0] + '/users.json'
bot = telepot.aio.Bot(key['telegram'])
users_dict = {}

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

    cmd_list = ['start', 'safety', 'nosafe', 'authhelp', 'setuser', 'settoken', 'axe']

    raw_msg = msg['text'].lower()
    check_cmd = raw_msg.split(' ', 1)[0][1:].split('@')[0]
    cmd = [i for i in cmd_list if check_cmd in i]

    if cmd:
        cmd = cmd[0]
    else:
        return

    try:
        cmd_arg = raw_msg.split(' ', 1)[1]
    except IndexError:
        cmd_arg = None

    with open(users_file, 'r') as u:
        global users_dict
        users_dict = json.loads(u.read())
    user_data = users_dict['users']

    await bot.sendChatAction(chat_id, 'typing')
    await globals()['cmd_' + cmd](cmd_arg, from_id, user_data, chat_id)

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
        if query_safety:
            query_string = query_string + ' safety:' + query_safety
    else:
        pass


    rest_headers={ 'content-type' : 'application/json', 'accept' : 'application/json' }
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

            post_keyboard=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text='🔍', url='https://www.google.com/searchbyimage?&image_url=' + post_cont),
                        InlineKeyboardButton(text='❤️', callback_data='favorite ' + post_id)],
                        ])

            if post_mime == 'image/jpeg':
                listobj.append(InlineQueryResultPhoto(
                    id=post_id, photo_url=post_cont,
                    thumb_url=post_thumb, caption=caption_text,
                    reply_markup=post_keyboard, parse_mode='Markdown'
                    )
                )
            elif post_mime == 'image/gif':
                listobj.append(InlineQueryResultGif(
                    id=post_id, gif_url=post_cont,
                    thumb_url=post_thumb, caption=caption_text,
                    reply_markup=post_keyboard, parse_mode='Markdown'
                    )
                )
            elif post_mime == 'video/mp4':
                listobj.append(InlineQueryResultVideo(
                    id=post_id, video_url=post_cont,
                    thumb_url=post_thumb, caption=caption_text,
                    reply_markup=post_keyboard, mime_type='video/mp4', 
                    parse_mode='Markdown', title=post_id
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

async def on_callback_query(msg):
    query_id, chat_id, query_data = telepot.glance(msg, flavor='callback_query')
    from_id = str(msg['from']['id'])
    if query_data.startswith('favorite'):
        this_post = query_data.split(' ')[1]
        with open(users_file, 'r') as u:
            users_dict = json.loads(u.read())
        user_data = users_dict['users']
        if from_id in user_data.keys():
            user_settings = user_data[from_id]
            if 'token' in user_settings.keys():
                user_token = base64.b64encode(bytes(user_settings['username'] + ':' + user_settings['token'], 'utf-8')).decode('utf-8')
                rest_headers={ 'content-type' : 'application/json', 'accept' : 'application/json', 'authorization' : 'Token ' + user_token }
                request_uri = 'https://coopr.ru/api/post/' + this_post + '/favorite'
                fave_post = requests.post(request_uri, headers=rest_headers)
                if fave_post.status_code == 200:
                    await bot.answerCallbackQuery(query_id, text='Post added to favorites!')
                elif fave_post.status_code == 403:
                    await bot.answerCallbackQuery(query_id, text='Your login token is invalid!')
                else:
                    await bot.answerCallbackQuery(query_id, text='Sorry, something went wrong!')
            else:
                await bot.answerCallbackQuery(query_id, text='Please login, send /authhelp to the bot in pm!')
        else:
            await bot.answerCallbackQuery(query_id, text='Please start a conversation with the bot in pm first!')


async def cmd_start(cmd_arg, from_id, user_data, chat_id):
    if from_id in user_data:
        return
    else:
        user_data[from_id] = { 'safety' : '' }
        async with aiofiles.open(users_file, 'w') as u:
            await u.write(json.dumps(users_dict))

async def cmd_safety(cmd_arg, from_id, user_data, chat_id):
    safeties = ['safe', 'sketchy', 'unsafe']
    if cmd_arg in safeties:
        user_settings = user_data[from_id]
        user_settings['safety'] = cmd_arg
        async with aiofiles.open(users_file, 'w') as u:
            await u.write(json.dumps(users_dict))
        await bot.sendMessage(chat_id, 'Search safety set to ' + cmd_arg + '!')
    else:
        await bot.sendMessage(chat_id, 'Sorry, that\'s not a valid safety')

async def cmd_nosafe(cmd_arg, from_id, user_data, chat_id):
    user_settings = user_data[from_id]
    user_settings['safety'] = ''
    async with aiofiles.open(users_file, 'w') as u:
        await u.write(json.dumps(users_dict))
    await bot.sendMessage(chat_id, 'Search safety cleared!')

async def cmd_authhelp(cmd_arg, from_id, user_data, chat_id):
    await bot.sendMessage(chat_id, 'To authenticate, first set your coopru username with `/setuser <username>`, then it is recommended to generate a new token under your account settings, and set that with `/settoken <token>`', parse_mode='Markdown')

async def cmd_setuser(cmd_arg, from_id, user_data, chat_id):
    if cmd_arg is not None:
        user_settings = user_data[from_id]
        user_settings['username'] = cmd_arg
        async with aiofiles.open(users_file, 'w') as u:
            await u.write(json.dumps(users_dict))
        await bot.sendMessage(chat_id, 'Username set to ' + command_argument + '!')
    else:
        await bot.sendMessage(chat_id, 'Please provide a username')

async def cmd_settoken(cmd_arg, from_id, user_data, chat_id):
    if cmd_arg is not None:
        user_settings = user_data[from_id]
        if 'username' in user_settings.keys():
            user_token = base64.b64encode(bytes(user_settings['username'] + ':' + cmd_arg, 'utf-8')).decode('utf-8')
            rest_headers={ 'content-type' : 'application/json', 'accept' : 'application/json', 'authorization' : 'Token ' + user_token }
            request_uri = 'https://coopr.ru/api/posts/?limit=1'
            test_auth = requests.get(request_uri, headers=rest_headers)
            if test_auth.status_code == 200:
                user_settings['token'] = cmd_arg
                async with aiofiles.open(users_file, 'w') as u:
                    await u.write(json.dumps(users_dict))
                await bot.sendMessage(chat_id, 'Token set!')
            else:
                await bot.sendMessage(chat_id, 'Sorry, either your username or token is wrong ;<')
        else:
            await bot.sendmessage(chat_id, 'Please set your username first!')
    else:
        await bot.sendMessage(chat_id, 'Please provide a token')


answerer = telepot.aio.helper.Answerer(bot)
loop = asyncio.get_event_loop()
loop.create_task(MessageLoop(bot,{'chat' : on_command,
                  'inline_query' : on_inline_query,
                  'callback_query' : on_callback_query}).run_forever())
print('Started...')
loop.run_forever()
