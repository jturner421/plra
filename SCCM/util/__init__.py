import functools
import ssl
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


class AsyncHttpClient:
    session: aiohttp.ClientSession = None

    async def start(self):
        MAX_CONCURRENT = 10
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
        auth = aiohttp.BasicAuth(settings.ccam_username,
                                 password=settings.ccam_password.get_secret_value(),
                                 encoding='utf-8')

        self.session = aiohttp.ClientSession(base_url=settings.base_url, connector=connector, auth=auth)

    async def stop(self):
        await self.session.close()
        self.session = None

    async def get_CCAM_balances(self, data, ccam_case_num) -> int:
        timeout = aiohttp.ClientTimeout(total=5 * 60)
        headers = {'Content-Type': 'application/json'}
        rest = '/ccam/v1/Accounts'
        ssl_context = ssl.create_default_context(cafile=settings.cert_file)
        async with self.session.get(
                rest,
                timeout=timeout,
                headers=headers,
                params=data,
                ssl=ssl_context) as response:
            response.raise_for_status()
            res = await response.read()
            ccam_data = json.loads(res)['data']

            # API pagination set at 20. This snippet retrieves the rest of the records.  Note: API does not return next page
            # url so we need to rely on total pages embedded in the metadata
        for page in range(2, json.loads(res)['meta']['pageInfo']['totalPages'] + 1):
            data = {"caseNumberList": ccam_case_num, "page": page}
            async with self.session.get(rest, timeout=timeout, headers=headers, params=data,
                                        ssl=ssl_context) as response:
                response.raise_for_status()
                ccam_data.extend(await response["data"])
        return ccam_data

    def __call__(self) -> aiohttp.ClientSession:
        assert self.session is not None
        return self.session


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


async def get_httpx(url: str, params: Optional = None, headers: Optional = None) -> int:
    caseid = url.split('/')[-1]
    print(Fore.YELLOW + f'Getting docket entries for case {caseid}...', flush=True)
    if headers:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params, headers=headers, timeout=None)
    else:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params=params, timeout=None)
    return r.status_code


async def fetch_CCAM_balances(session, data, ccam_case_num):
    timeout = aiohttp.ClientTimeout(total=5 * 60)
    headers = {'Content-Type': 'application/json'}
    rest = '/ccam/v1/Accounts'
    ssl_context = ssl.create_default_context(cafile=PLRASettings.cert_file)
    async with session.get(
            rest,
            timeout=timeout,
            headers=headers,
            params=data,
            ssl=ssl_context) as response:
        response.raise_for_status()
        res = await response.read()
        ccam_data = json.loads(res)['data']

        # API pagination set at 20. This snippet retrieves the rest of the records.  Note: API does not return next page
        # url so we need to rely on total pages embedded in the metadata
    for page in range(2, json.loads(res)['meta']['pageInfo']['totalPages'] + 1):
        data = {"caseNumberList": ccam_case_num, "page": page}
        async with session.get(rest, timeout=timeout, headers=headers, params=data, ssl=ssl_context) as response:
            response.raise_for_status()
            ccam_data.extend(await response["data"])
    return ccam_data


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
