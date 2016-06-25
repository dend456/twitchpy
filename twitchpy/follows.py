from .twitch import __check_cache, __cache, __headers
import aiohttp
import time
from dateutil.parser import parse

CHANNEL_FOLLOWERS_URL = 'https://api.twitch.tv/kraken/channels/{}/follows?direction=DESC&limit=100'
USER_FOLLOWERS_URL = 'https://api.twitch.tv/kraken/users/{}/follows/channels?direction=DESC&limit=100'
USER_FOLLOWS_CHANNEL_URL = 'https://api.twitch.tv/kraken/users/{}/follows/channels/{}'

DATE_FORMAT_STRING = '%Y-%m-%dT%H:%M:%S%z'


class ChannelFollower:
    """Represents a user who follows a channel."""

    def __init__(self, follow_time, follows_link, notifs, type, bio, logo, display_name, created_time, updated_time, _id, name):
        self.follow_time = follow_time
        self.follows_link = follows_link
        self.notifications = notifs,
        self.type = type
        self.bio = bio
        self.logo = logo
        self.display_name = display_name
        self.created_time = created_time
        self.updated_time = updated_time
        self._id = _id
        self.name = name

    def __eq__(self, other):
        return self._id == other._id

    def __hash__(self):
        return self._id

    @classmethod
    def from_json(cls, js):
        user = js['user']
        return cls(parse(js['created_at']), js['_links']['self'],js['notifications'], user['type'], user['bio'], user['logo'], user['display_name'],
                   parse(user['created_at']), parse(user['updated_at']), user['_id'], user['name'])


class FollowedChannel:
    """Represents a channel followed by a user."""
    def __init__(self, follow_time, mature, status, broadcaster_language, display_name, game, delay, language, _id, name, created_time, updated_time,
                 logo, banner, video_banner, background, profile_banner, profile_banner_background, partner, url, views, followers, links):
        self.follow_time = follow_time,
        self.mature = mature
        self.status = status,
        self.broadcaster_language = broadcaster_language
        self.display_name = display_name
        self.game = game
        self.delay = delay
        self.language = language
        self._id = _id
        self.name = name
        self.created_time = created_time
        self.updated_time = updated_time
        self.logo = logo
        self.banner = banner
        self.video_banner = video_banner
        self.background = background
        self.profile_banner = profile_banner
        self.profile_banner_background = profile_banner_background
        self.partner = partner
        self.url = url
        self.views = views
        self.followers = followers
        self.links = links

    @classmethod
    def from_json(cls, js):
        chan = js['channel']
        return cls(parse(js['created_at']), chan['mature'], chan['status'], chan['broadcaster_language'], chan['display_name'], chan['game'],
                   chan['delay'], chan['language'], chan['_id'], chan['name'], parse(chan['created_at']), parse(chan['updated_at']), chan['logo'],
                   chan['banner'], chan['video_banner'], chan['background'], chan['profile_banner'], chan['profile_banner_background_color'],
                   chan['partner'], chan['url'], chan['views'], chan['followers'], chan['_links'])

async def get_followers_for_channel(channel, force_refresh=False):
    if channel[0] == '#':
        channel = channel[1:]

    cache_key = ('get_followers_for_channel', channel)
    if not force_refresh:
        cached = __check_cache(cache_key)
        if cached:
            return cached

    followers = []
    try:
        res = await aiohttp.request('get', CHANNEL_FOLLOWERS_URL.format(channel), headers=__headers)
        js = await res.json()

        _total = js['_total']
        followers += [ChannelFollower.from_json(x) for x in js['follows']]

        while len(followers) < _total:
            res = await aiohttp.request('get', js['_links']['next'], headers=__headers)
            js = await res.json()
            followers += [ChannelFollower.from_json(x) for x in js['follows']]

        __cache[cache_key] = followers, time.time()
    except Exception:
        pass
    return followers

async def get_followed_channels(user, force_refresh=False):
    cache_key = ('get_followed_channels', user)
    if not force_refresh:
        cached = __check_cache(cache_key)
        if cached:
            return cached

    channels = []
    try:
        res = await aiohttp.request('get', USER_FOLLOWERS_URL.format(user), headers=__headers)
        js = await res.json()

        _total = js['_total']
        channels += [FollowedChannel.from_json(x) for x in js['follows']]

        while len(channels) < _total:
            res = await aiohttp.request('get', js['_links']['next'], headers=__headers)
            js = await res.json()
            channels += [FollowedChannel.from_json(x) for x in js['follows']]

        __cache[cache_key] = channels, time.time()
    except Exception:
        pass
    return channels

async def does_user_follow_channel(user, channel):
    """Gets a FollowedChannel given a user and channel. Returns None if user doesn't exist or does not follow channel."""

    try:
        res = await aiohttp.request('get', USER_FOLLOWS_CHANNEL_URL.format(user, channel), headers=__headers)
        if res.status == 404:
            res.close()
            return None
        js = await res.json()
        return FollowedChannel.from_json(js)

    except Exception:
        pass
    return None

