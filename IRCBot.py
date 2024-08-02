#!/usr/bin/env python3.11

import twitchpy as tw
import argparse
import pyperclip
import winsound


class TwitchBot(tw.TwitchIRCBot):
    def __init__(self, server='irc.twitch.tv', port=6697, channel='', user='', password='', log=None):
        super().__init__(server=server, port=port, channel=channel, user=user, password=password, log=log)

    def on_message(self, name, tags, msg):
        print(f'{name:>16}: {msg}')

    def on_sub(self, name, months):
        pass

    def on_mode_change(self, mode, on, data):
        pass

    def on_follow(self, followers):
        pass

    def on_join(self, name, tags):
        pass

    def on_part(self, name, tags):
        pass

    @tw.TwitchIRCBot.chat_command('!lootfilter', tw.Badges.none)
    def loot_filter_command(self, name, tags, msg):
        s = 'Download the loot filter from https://easyupload.io/f496ep extract anywhere and run after starting the game. '\
            'By default it filters about 99% of the items in the game so check the filter file to make sure something '\
            'you want isn\'t hidden. This may get you banned so use at your own risk.'

        self.send_private_message(s)    \

    @tw.TwitchIRCBot.chat_command('!stop', tw.Badges.broadcaster)
    def loot_filter_command(self, name, tags, msg):
        print('stopping')
        self.stop()

    @tw.TwitchIRCBot.regex_command(r'(\d{4}-\d{3}-\d{4})', tw.Badges.none)
    def some_regex_command(self, matches, name, tags, message):
        print('!matches: ')
        for m in matches:
            print(f'\t{m}')

    @tw.TwitchIRCBot.regex_command(r'!add\s(?P<level_code>[A-Za-z0-9]{3}-[A-Za-z0-9]{3}-[A-Za-z0-9]{3})', tw.Badges.subscriber | tw.Badges.broadcaster)
    def add_level(self, matches, name, tags, msg):
        print(f'{name} - {msg}')

        print(f'\n\n{matches[0]}')

    @tw.TwitchIRCBot.regex_command(r'^(?P<code>[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4})$')
    def found_level_code(self, matches, name, tags, msg):
        print(f'FOUND CODE - {matches[0]["code"]}')
        pyperclip.copy(matches[0]["code"])
        winsound.Beep(1000, 1000)

    @tw.TwitchIRCBot.regex_command(r'^(?P<code>[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4})$')
    def found_level_code(self, matches, name, tags, msg):
        print(f'FOUND CODE - {matches[0]["code"]}')
        pyperclip.copy(matches[0]["code"])
        winsound.Beep(1000, 1000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Something something twitchbot')
    parser.add_argument('-p', '--password', help='OAuth token', required=True)
    parser.add_argument('-c', '--channel', help='Channel', required=True)
    parser.add_argument('-u', '--username', help='Username', required=True)
    parser.add_argument('-i', '--client-id', help='Client ID', required=True)
    parser.add_argument('-l', '--log', help='Set log file')
    parser.set_defaults(log=None)
    args = parser.parse_args()

    tw.set_client_id(args.client_id)
    tb_thread = TwitchBot(channel=args.channel, user=args.username, password=args.password, log=args.log)
    tb_thread.run()
