import functools
from functools import wraps
import json
import time
from pathlib import Path
from typing import Callable, Any, Optional
import asyncio
import aiohttp
from aiohttp import ClientSession
from colorama import Fore
import pandas as pd

from SCCM.config.config_model import PLRASettings

env_file = Path.cwd() / 'config' / 'dev.env'
settings = PLRASettings(_env_file=env_file, _env_file_encoding='utf-8')


# logging.getLogger('backoff').addHandler(logging.StreamHandler())


def async_timed():
    """Decorator to time async functions"""

    def wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs) -> Any:
            print(f'starting {func} with args {args} {kwargs}')
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                end = time.time()
                total = end - start
                print(f'finished {func} in {total:.4f} second(s)')

        return wrapped

    return wrapper


async def delay(delay_seconds: int) -> int:
    """Delay for a number of seconds for an async function"""
    print(f'sleeping for {delay_seconds} second(s)')
    await asyncio.sleep(delay_seconds)
    print(f'finished sleeping for {delay_seconds} second(s)')
    return delay_seconds


async def get(session: ClientSession, url: str, params: Optional = None, headers: Optional = None) -> int:
    """Retrieve data asynchronously from an endpoint with aiohttp"""
    to = aiohttp.ClientTimeout(total=5 * 60)
    caseid = url.split('/')[-1]
    print(Fore.YELLOW + f'Getting docket entries for case {caseid}...', flush=True)
    if headers:
        async with session.get(url, timeout=to, params=params, headers=headers, ssl=False) as result:
            res = await result.read()
            df = pd.DataFrame(json.loads(res)['data'])
            df.head()
            return df
    else:
        async with session.get(url, timeout=to, params=params, ssl=False) as result:
            return result.status


def timeit(func):
    """Decorator to time synchronous functions"""

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds')
        return result

    return timeit_wrapper
