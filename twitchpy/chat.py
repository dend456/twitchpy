import socket
import time
import threading
import functools
import re
import queue
import ssl
import sys
import traceback
from datetime import datetime


class Badges:
    none = 0
    moderator = 1 << 1
    subscriber = 1 << 2
    broadcaster = 1 << 3
    staff = 1 << 4
    admin = 1 << 5
    global_mod = 1 << 6
    turbo = 1 << 7
    premium = 1 << 8


class ChatMode:
    normal = 0
    sub = 1 << 0
    slow = 1 << 1
    r9k = 1 << 2
    host = 1 << 3


class TwitchIRCBot:
    CHAT_SERVER_HOSTNAME = 'irc-ws.chat.twitch.tv'
    MESSAGE_LIMIT = (20, 31)  # 20 messages per 31 seconds
    MODE_MESSAGES = {'This room is now in subscribers-only mode.': (ChatMode.sub, True),
                     'This room is no longer in subscribers-only mode.': (ChatMode.sub, False),
                     'This room is now in slow mode.': (ChatMode.slow, True),
                     'This room is no longer in slow mode.': (ChatMode.slow, False),
                     'This room is now in r9k mode.': (ChatMode.r9k, True),
                     'This room is no longer in r9k mode.': (ChatMode.r9k, False),
                     'Now hosting': (ChatMode.host, True),
                     'Exited host mode.': (ChatMode.host, False)}

    RE_SUB_REGEX = re.compile(r'^(?P<name>[A-Za-z0-9_]{4,32}) subscribed for (?P<months>[0-9]{1,10}) months in a row!$')
    NEW_SUB_REGEX = re.compile(r'^(?P<name>[A-Za-z0-9_]{4,32}) just subscribed!$')

    commands = {}
    regex_commands = []

    def __init__(self, server='', port=6697, channel='', user='', password='', log=None):
        if channel and channel[0] != '#':
            channel = '#' + channel
        self.server = server.lower()
        self.port = port
        self.channel = channel.lower()
        self.user = user.lower()
        self.password = password
        self.ssl_context = ssl.create_default_context()
        self.irc_socket = None
        self.irc = None
        self.log = log
        self.message_time_history = []
        self.message_queue = queue.Queue()
        self.message_queue_thread = threading.Thread(target=self._start_message_queue)
        self.running = False
        self.chat_mode = ChatMode.normal
        self.slow_time = 0
        self.hosting = None

        if log:
            self.log = open(log, 'ab')

    @staticmethod
    def chat_command(command, badges=Badges.broadcaster):
        """Decorator for subclass chat commands.
            Call function if chat message starts with 'command' and user has appropriate user level"""
        def decorator(func):
            @functools.wraps(func)
            def wrap(*args):
                func(*args)
            TwitchIRCBot.commands[command] = (wrap, badges)
            return wrap
        return decorator

    @staticmethod
    def regex_command(command, badges=Badges.broadcaster):
        """Decorator for subclass regex commands.
            Call function if chat message contains match for 'command' regex and user has appropriate user level
        """
        def decorator(func):
            @functools.wraps(func)
            def wrap(*args):
                func(*args)
            TwitchIRCBot.regex_commands.append((re.compile(command), wrap, badges))
            return wrap
        return decorator

    def _start_message_queue(self):
        """Message queue to send to IRC. Used to manage message rate to avoid bans and logging."""
        while self.running:
            message = self.message_queue.get()
            if message:
                while len(self.message_time_history) > TwitchIRCBot.MESSAGE_LIMIT[0]:
                    current_time = time.time()
                    now_minus_timeout = current_time - TwitchIRCBot.MESSAGE_LIMIT[1]
                    self.message_time_history = [x for x in self.message_time_history if x > now_minus_timeout]
                    if len(self.message_time_history) < TwitchIRCBot.MESSAGE_LIMIT[0]:
                        break
                    min_time = min(self.message_time_history)
                    time.sleep((min_time + TwitchIRCBot.MESSAGE_LIMIT[1] - current_time) + .1)

            while self.running:
                try:
                    self.irc.send(message)
                    if self.log:
                        current_time = datetime.utcnow().strftime('> %Y:%m:%d %H:%M:%S ')
                        self.log.write(current_time.encode())
                        if message.startswith(b'pass'):
                            message = b'pass ' + b'*'*(len(message)-5) + b'\r\n'
                        self.log.write(message)
                        self.log.flush()
                        self.message_time_history.append(time.time())
                    break
                except Exception as e:
                    print(e, file=sys.stderr)
                    self._reconnect()
            self.message_queue.task_done()

    def _reconnect(self):
        attempt = 0
        self.irc = None
        self.irc_socket = None
        while not self.irc:
            if attempt > 0:
                time.sleep(5)
                print('{}: Connection failed...trying again in 5 seconds.'.format(attempt))
            self._connect()
            attempt += 1

    def _connect(self):
        self.irc = None
        self.irc_socket = None
        irc = None

        try:
            irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            irc.connect((self.server, self.port))
            print('Connected to {}'.format(self.server))
        except Exception:
            irc = None

        self.irc_socket = irc
        self.irc = self.ssl_context.wrap_socket(self.irc_socket, server_hostname=TwitchIRCBot.CHAT_SERVER_HOSTNAME)
        if self.irc:
            self.irc.send(b'CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership\r\n')
            self.irc.send(f'pass {self.password}\r\n'.encode('utf-8'))
            self.irc.send(f'nick {self.user}\r\n'.encode('utf-8'))
            self.irc.send(f'user {self.user} 8 * :{self.user}\r\n'.encode('utf-8'))
            self.irc.send(f'join {self.channel}\r\n'.encode('utf-8'))

            print('Joined channel {}'.format(self.channel))

    def run(self):
        self.running = True
        self._reconnect()
        self.message_queue_thread.start()
        while self.running:
            try:
                data = self.irc.recv(2048).decode('UTF-8')
            except Exception:
                self._reconnect()
            else:
                current_time = datetime.utcnow().strftime('%Y:%m:%d %H:%M:%S')

                if self.log:
                    self.log.write(('< {} {}'.format(current_time, data.replace('\r\n', '\r\n\t\t\t')[:-3])).encode())
                    self.log.flush()

                messages = data.split('\n')

                for message in messages[:-1]:
                    self._parse_message(message)

    def stop(self):
        self.running = False
        self.message_queue_thread.join()

    def _on_command(self, command, data):
        command = command.lower()
        if command == "ping":
            server = data[5:-1]
            self.send_message('PONG {}'.format(server))

    def _parse_message(self, data):
        """Parse IRC message and dispatch to appropriate functions"""
        if data.startswith('PING'):
            self._on_command('PING', data)
            return

        tags = {}
        if data.startswith('@'):
            data = data[1:]
            ind = data.find(' :')
            tag = data[:ind].split(';')
            data = data[ind+1:]
            for t in tag:
                k, v = t.split('=')
                tags[k] = v

        data = data.strip()
        if data.startswith(":"):
            if data.startswith(':jtv'):
                pass
            elif data.startswith(':tmi.twitch.tv'):
                strings = data.split(' ')
                if strings[1] == 'NOTICE':
                    msg = data[data.find(' :')+2:]
                    mode_data = None
                    for mode_msg, mode in TwitchIRCBot.MODE_MESSAGES.items():
                        if msg.startswith(mode_msg):
                            if mode[0] == ChatMode.host and mode[1]:
                                strings = msg.split(' ')
                                mode_data = strings[2]
                                self.hosting = mode_data

                            if mode[1]:
                                self.chat_mode |= mode[0]
                            else:
                                self.chat_mode &= ~mode[0]

                            self.on_mode_change(mode[0], mode[1], mode_data)
                            break

                elif strings[1] == 'ROOMSTATE':
                    for k, v in tags.items():
                        mode_data = None
                        on = False if v == '0' else True
                        if k == 'slow':
                            mode = ChatMode.slow
                            self.slow_time = int(v)
                            mode_data = self.slow_time
                        elif k == 'r9k':
                            mode = ChatMode.r9k
                        elif k == 'subs-only':
                            mode = ChatMode.sub
                        else:
                            continue

                        if on:
                            self.chat_mode |= mode
                        else:
                            self.chat_mode &= ~mode

                        self.on_mode_change(mode, on, mode_data)
            else:
                try:
                    strings = data.split(':')
                    msg = ":".join(strings[2:])
                    ex_ind = strings[1].find('!')
                    if ex_ind == -1:
                        return
                    name = strings[1][0:ex_ind]
                    strings = data.split(' ')
                    command = strings[1].lower()

                    if command == "privmsg" and msg:
                        if name == 'twitchnotify':
                            matches = TwitchIRCBot.NEW_SUB_REGEX.match(msg)
                            found_sub = False
                            if matches:
                                groups = matches.groupdict()
                                name = groups['name']
                                months = 1
                                found_sub = True
                            else:
                                matches = TwitchIRCBot.RE_SUB_REGEX.match(msg)
                                if matches:
                                    groups = matches.groupdict()
                                    name = groups['name']
                                    months = int(groups['months'])
                                    found_sub = True

                            if found_sub:
                                self.on_sub(name, months)

                        self._on_message(name, tags, msg)
                    elif command == "join":
                        self.on_join(name, tags)
                    elif command == "part":
                        self.on_part(name, tags)
                except Exception as e:
                    traceback.print_exc(file=sys.stderr)

    @staticmethod
    def get_badges(badges):
        level = Badges.none

        badges = [badge.split('/')[0] for badge in badges.split(',')]
        badge_vars = vars(Badges)
        for badge in badges:
            level |= badge_vars.get(badge, 0)

        return level

    def _on_message(self, name, tags, message):
        #lower_message = message.lower()
        parts = message.split()
        event = TwitchIRCBot.commands.get(parts[0])
        badges = self.get_badges(tags['badges'])
        if event and (badges & event[1] or event[1] == Badges.none):
            try:
                ind = message.index(' ')
            except ValueError:
                ind = -1
            if ind == -1:
                event[0](self, name, tags, '')
            else:
                event[0](self, name, tags, message[ind+1:])

        for event in TwitchIRCBot.regex_commands:
            if badges & event[2] or event[2] == Badges.none:
                matches = [m.groupdict() for m in event[0].finditer(message)]
                if matches:
                    event[1](self, matches, name, tags, message)

        self.on_message(name, tags, message)

    def send_message(self, message):
        if type(message) == str:
            message = message.encode('UTF-8')
        self.message_queue.put(message + b'\r\n')

    def send_private_message(self, msg):
        self.send_message('PRIVMSG {} :{}'.format(self.channel, msg))

    def on_sub(self, name, months):
        pass

    def on_follow(self, followers):
        pass

    def on_join(self, name, tags):
        pass

    def on_part(self, name, tags):
        pass

    def on_mode_change(self, mode, on, mode_data):
        pass

    def on_message(self, name, tags, messgae):
        pass
