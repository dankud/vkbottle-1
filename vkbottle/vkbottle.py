from .jsontype import json_type_utils
from .utils import Utils
from .keyboard import _keyboard
from .methods import Method
from random import randint
import re
import requests
from multiprocessing import Process


# Bot Universal Class
class RunBot:
    def __init__(self, bot, token, asyncio=True):
        self._token = token
        self.bot = bot
        self.url = 'https://api.vk.com/method/'
        self.utils = Utils(self.bot.debug)
        self.utils('Bot was authorised successfully')
        self.utils('Async module completed')
        self.method = Method(token, self.url, self.bot.api_version)
        self.asyncio = asyncio

    def run(self, wait):
        self.utils('Found {} message decorators'.format(len(self.bot.processor_message.keys())))
        self.utils(json_type_utils())
        longpoll = self.method(
            'groups',
            'getLongPollServer',
            {"group_id": self.bot.group_id}
        )
        ts = longpoll['ts']
        self.utils('Started listening longpoll...')

        self.__run(wait, longpoll, ts)

    def __run(self, wait, longpoll, ts):
        while True:
            try:
                url = f"{longpoll['server']}?act=a_check&key={longpoll['key']}&ts={ts}&wait={wait}&rps_delay=0"
                event = requests.post(url).json()
                if self.asyncio:
                    proc = Process(target=self.event_processor, args=(event,))
                    proc.start()
                else:
                    self.event_processor(event)
                # await self.event_processor(event)
            except requests.ConnectTimeout:
                self.utils.warn('Request Connect Timeout! Reloading longpoll..')
            except Exception as e:
                self.utils.warn('ERROR! ' + str(e))
            try:
                longpoll = self.method(
                    'groups',
                    'getLongPollServer',
                    {"group_id": self.bot.group_id}
                )
                ts = longpoll['ts']
            except Exception as E:
                self.utils.warn('LONGPOLL CONNECTION ERROR! ' + str(E))

    def event_processor(self, event):
        if event['updates']:
            for update in event['updates']:
                obj = update['object']
                if update['type'] == 'message_new':
                    if obj['peer_id'] < 2e9:
                        self.process_message(obj['text'], obj)
                    else:
                        self.process_message_chat(obj['text'], obj)
                elif update['type'] in self.bot.events:
                    self.process_event(event)

    def process_message_chat(self, text: str, obj):
        answer = AnswerObjectChat(self.method, obj, self.bot.group_id)
        if text in self.bot.processor_message_chat:
            self.utils('\x1b[31;1m-> MESSAGE FROM CHAT {} TEXT "{}" TIME #'.format(obj['peer_id'], obj['text']))
            self.bot.processor_message_chat[text](answer)
            self.utils(
                'New message compiled with decorator <\x1b[35m{}\x1b[0m> (from: {})'.format(
                    self.bot.processor_message_chat[text].__name__, obj['from_id']
                ))

        answer = AnswerObjectChat(self.method, obj, self.bot.group_id)
        regex_text = False
        if self.bot.processor_message_chat_regex != {}:
            for key in self.bot.processor_message_chat_regex:
                if key.match(text) is not None:
                    self.utils('\x1b[31;1m-> MESSAGE FROM CHAT {} TEXT "{}" TIME #'.format(obj['peer_id'], obj['text']))
                    try:
                        self.bot.processor_message_chat_regex[key]['call'](answer, **key.match(text).groupdict())
                    except TypeError:
                        Utils(True).warn(
                            f'ADD TO {self.bot.processor_message_chat_regex[key]["call"].__name__} FUNCTION REQUIRED ARGS'
                        )
                    else:
                        regex_text = True
        if not regex_text:
            if text in self.bot.processor_message:
                self.utils('\x1b[31;1m-> MESSAGE FROM CHAT {} TEXT "{}" TIME #'.format(obj['peer_id'], obj['text']))
                self.bot.processor_message_chat[text](answer)
                self.utils(
                    'New message compiled with decorator <\x1b[35m{}\x1b[0m> (from: {})'.format(
                        self.bot.processor_message[text].__name__, obj['peer_id']
                    ))

    def process_message(self, text: str, obj):
        answer = AnswerObject(self.method, obj, self.bot.group_id)
        self.utils('\x1b[31;1m-> MESSAGE FROM {} TEXT "{}" TIME #'.format(obj['peer_id'], obj['text']))
        regex_text = False
        if self.bot.processor_message_regex != {}:
            for key in self.bot.processor_message_regex:
                if key.match(text) is not None:
                    try:
                        self.bot.processor_message_regex[key]['call'](answer, **key.match(text).groupdict())
                    except TypeError:
                        Utils(True).warn(
                            f'ADD TO {self.bot.processor_message_regex[key]["call"].__name__} FUNCTION REQUIRED ARGS'
                        )
                    else:
                        regex_text = True
        if not regex_text:
            if text in self.bot.processor_message:
                self.bot.processor_message[text](answer)
                self.utils(
                    'New message compiled with decorator <\x1b[35m{}\x1b[0m> (from: {})'.format(
                        self.bot.processor_message[text].__name__, obj['peer_id']
                    ))
            else:
                self.utils(
                    'New message compile decorator was not found. ' +
                    'Compiled with decorator \x1b[35m[on-message-undefined]\x1b[0m (from: {})'.format(
                        obj['peer_id']
                    ))
                self.bot.undefined_message_func(answer)

    def process_event(self, event):
        self.utils(
            '\x1b[31;1m-> NEW EVENT FROM {} TYPE "{}" TIME #'.format(
                event['updates'][0]['object']['user_id'],
                event['updates'][0]['type']
            ))
        event_type = event['updates'][0]['type']
        rule = self.bot.events[event_type]['rule']
        if rule != '=':
            event_compile = True \
                if rule in event['updates'][0]['object'] \
                and event['updates'][0]['object'][rule] in self.bot.events[event_type]['equal'] \
                else False
            if event_compile:
                answer = AnswerObject(self.method, event['updates'][0]['object'], self.bot.group_id)
                self.utils('* EVENT RULES => TRUE. COMPILING EVENT')
                self.bot.events[event_type]['equal'][event['updates'][0]['object'][rule]](answer)
            else:
                self.utils('* EVENT RULES => FALSE. IGNORE EVENT')
        else:
            answer = AnswerObject(self.method, event['updates'][0]['object'], self.bot.group_id)
            self.utils('* EVENT RULES => TRUE. COMPILING EVENT')
            self.bot.events[event_type]['equal']['='](answer)


class AnswerObject:
    def __init__(self, method, obj, group_id):
        self.method = method
        self.obj = obj
        self.group_id = group_id
        self.peer_id = obj['peer_id']
        self.self_parse = dict(
            group_id=group_id,
            peer_id=self.peer_id
        )

    def __call__(self, message: str, attachment=None, keyboard=None, sticker_id=None,
                 chat_id=None, user_ids=None, lat=None, long=None, reply_to=None, forward_messages=None, payload=None,
                 dont_parse_links=False, disable_mentions=False):
        message = self.parser(message)
        request = dict(
            message=message,
            keyboard=_keyboard(keyboard) if keyboard is not None else None,
            attachment=attachment,
            peer_id=self.peer_id,
            random_id=randint(1, 2e5),
            sticker_id=sticker_id,
            chat_id=chat_id,
            user_ids=user_ids,
            lat=lat,
            long=long,
            reply_to=reply_to,
            forward_messages=forward_messages,
            payload=payload,
            dont_parse_links=dont_parse_links,
            disable_mentions=disable_mentions
        )
        request = {k: v for k, v in request.items() if v is not None}
        return self.method('messages', 'send', request)

    def parser(self, message):
        user_parse = list(set(re.findall(r'{user:\w+}', message)))
        group_parse = list(set(re.findall(r'{group:\w+}', message)))
        self_parse = list(set(re.findall(r'{self:\w+}', message)))
        if user_parse:
            user = self.method('users', 'get', {'user_ids': self.peer_id})[0]
            for parser in user_parse:
                message = message.replace(
                    parser, str(user.get(parser[parser.find(':') + 1: parser.find('}')], 'undefined')))
        if group_parse:
            group = self.method('groups', 'getById', {'group_id': self.group_id})[0]
            for parser in group_parse:
                message = message.replace(
                    parser, str(group.get(parser[parser.find(':') + 1: parser.find('}')], 'undefined')))
        if self_parse:
            selfs = self.self_parse
            for parser in self_parse:
                message = message.replace(
                    parser, str(selfs.get(parser[parser.find(':') + 1: parser.find('}')], 'undefined')))
        return message


class AnswerObjectChat:
    def __init__(self, method, obj, group_id):
        self.method = method
        self.obj = obj
        self.group_id = group_id
        self.peer_id = obj['peer_id']
        self.user_id = obj['from_id']
        self.self_parse = dict(
            group_id=group_id,
            user_id=self.user_id,
            peer_id=self.peer_id
        )

    def __call__(self, message: str, attachment=None, keyboard=None, sticker_id=None,
                 chat_id=None, user_ids=None, lat=None, long=None, reply_to=None, forward_messages=None, payload=None,
                 dont_parse_links=False, disable_mentions=False):
        message = self.parser(message)
        request = dict(
            message=message,
            keyboard=_keyboard(keyboard) if keyboard is not None else None,
            attachment=attachment,
            peer_id=self.peer_id,
            random_id=randint(1, 2e5),
            sticker_id=sticker_id,
            chat_id=chat_id,
            user_ids=user_ids,
            lat=lat,
            long=long,
            reply_to=reply_to,
            forward_messages=forward_messages,
            payload=payload,
            dont_parse_links=dont_parse_links,
            disable_mentions=disable_mentions
        )
        request = {k: v for k, v in request.items() if v is not None}
        return self.method('messages', 'send', request)

    def parser(self, message):
        user_parse = list(set(re.findall(r'{user:\w+}', message)))
        group_parse = list(set(re.findall(r'{group:\w+}', message)))
        self_parse = list(set(re.findall(r'{self:\w+}', message)))
        if user_parse:
            user = self.method('users', 'get', {'user_ids': self.user_id})[0]
            for parser in user_parse:
                message = message.replace(
                    parser, str(user.get(parser[parser.find(':') + 1: parser.find('}')], 'undefined')))
        if group_parse:
            group = self.method('groups', 'getById', {'group_id': self.group_id})[0]
            for parser in group_parse:
                message = message.replace(
                    parser, str(group.get(parser[parser.find(':') + 1: parser.find('}')], 'undefined')))
        if self_parse:
            selfs = self.self_parse
            for parser in self_parse:
                message = message.replace(
                    parser, str(selfs.get(parser[parser.find(':') + 1: parser.find('}')], 'undefined')))
        return message