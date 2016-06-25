#! /usr/bin/env python3.5

import twitchpy as tw
import argparse


class TwitchBot(tw.TwitchIRCBot):
    def __init__(self, server='irc.twitch.tv', port=6697, channel='', user='', password='', log=None):
        super().__init__(server=server, port=port, channel=channel, user=user, password=password, log=log)

    def on_message(self, name, tags, message):
        print('{:>32}: {}'.format(name, message))

    def on_sub(self, name, months):
        pass

    def on_mode_change(self, mode, on, data):
        pass

    def on_follow(self, followers):
        pass

    def on_join(self, name, tags):
        print('{} join'.format(name))

    def on_part(self, name, tags):
        print('{} part'.format(name))

    @tw.TwitchIRCBot.chat_command('!zz', tw.ChatUserLevel.mod)
    def some_chat_command(self, name, tags, msg):
        pass

    @tw.TwitchIRCBot.regex_command(r'(\d{4}-\d{3}-\d{4})', tw.ChatUserLevel.any)
    def some_regex_command(self, matches, name, tags, message):
        pass

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
    TwitchBot(channel=args.channel, user=args.username, password=args.password, log=args.log).run()
