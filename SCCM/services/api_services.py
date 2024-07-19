import functools
import ssl
from functools import wraps
import json
import time
from pathlib import Path
from typing import Callable, Any, Optional
import asyncio
import aiohttp
import backoff
from aiohttp import ClientSession
from colorama import Fore
import pandas as pd

from SCCM.config.config_model import PLRASettings
from util import settings

env_file = Path.cwd() / 'config' / 'dev.env'
settings = PLRASettings(_env_file=env_file, _env_file_encoding='utf-8')


def backoff_hdlr(details):
    print(Fore.RED + "Backing off {wait:0.1f} seconds after {tries} tries "
                     "calling function {target} with args {args} and kwargs "
                     "{kwargs}".format(**details))


class AsyncHttpClient:
    session: aiohttp.ClientSession = None

    async def start(self):
        MAX_CONCURRENT = 10
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
        auth = aiohttp.BasicAuth(settings.ccam_username,
                                 password=settings.ccam_password.get_secret_value(),
                                 encoding='utf-8')

        self.session = aiohttp.ClientSession(base_url=settings.base_url, connector=connector, auth=auth,
                                             raise_for_status=True)

    async def stop(self):
        await self.session.close()
        self.session = None

    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=4, on_backoff=backoff_hdlr)
    async def get_CCAM_balances_async(self, case_list):
        timeout = aiohttp.ClientTimeout(total=5 * 60)
        headers = {'Content-Type': 'application/json'}
        rest = '/ccam/v1/Accounts'
        ssl_context = ssl.create_default_context(cafile=settings.cert_file)
        case_list["page"] = 1
        case_list["size"] = 200
        print(Fore.BLUE + f'Retrieving Page {case_list["page"]} of CCAM Balances \n')
        async with self.session.post(
                rest,
                timeout=timeout,
                headers=headers,
                json=case_list,
                ssl=ssl_context) as response:
            # response.raise_for_status()
            res = await response.read()
            ccam_data = json.loads(res)['data']

        while json.loads(res)['meta']['pageInfo']['last'] is False:
            case_list["page"] = json.loads(res)['meta']['pageInfo']['number'] + 1
            print(Fore.BLUE + f'Retrieving Page {case_list["page"]} of CCAM Balances \n')
            async with self.session.post(rest, timeout=timeout, headers=headers, json=case_list,
                                        ssl=ssl_context) as response:
                response.raise_for_status()
                res = await response.read()
                ccam_data.extend(json.loads(res)['data'])
        return ccam_data

    def __call__(self) -> aiohttp.ClientSession:
        assert self.session is not None
        return self.session
