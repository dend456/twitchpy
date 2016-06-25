import time
import asyncio

__cache = {}
cache_timeout = 60

__headers = {'user-agent': 'twitchpy-v.0001', 'Connection': 'close'}


def set_client_id(cid):
    __headers['Client-ID'] = cid


def __check_cache(key):
    cached = __cache.get(key)
    now = time.time()
    if cached and cached[1] + cache_timeout > now:
        return cached[0]
    elif cached:
        del __cache[key]
    return None


def wait(cos):
    """Waits for all coroutines in cos to finish."""
    single = False
    if not isinstance(cos, (list, tuple)):
        cos = [cos]
        single = True

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    tasks = [asyncio.ensure_future(co) for co in cos]
    loop.run_until_complete(asyncio.wait(tasks, loop=loop))
    return [task.result() for task in tasks] if not single else tasks[0].result()


if __name__ == '__main__':
    pass