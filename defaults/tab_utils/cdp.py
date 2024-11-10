# Injector code from https://github.com/SteamDeckHomebrew/steamdeck-ui-inject. More info on how it works there.

from asyncio import sleep, run
from typing import List

from aiohttp import ClientSession # type: ignore
from aiohttp.client_exceptions import ClientConnectorError, ClientOSError # type: ignore
from asyncio.exceptions import TimeoutError

BASE_ADDRESS = "http://127.0.0.1:8080"

class Tab:
    cmd_id = 0

    def __init__(self, res) -> None:
        self.title = res["title"]
        self.id = res["id"]
        self.url = res["url"]
        self.ws_url = res["webSocketDebuggerUrl"]

        self.websocket = None
        self.client = None
    
    async def ensure_open(self):
        if self.websocket.closed:
            await self.open_websocket()

    async def open_websocket(self):
        self.client = ClientSession()
        self.websocket = await self.client.ws_connect(self.ws_url)

    async def close_websocket(self):
        await self.websocket.close()
        await self.client.close()

    async def listen_for_message(self):
        async for message in self.websocket:
            data = message.json()
            yield data

        await self.close_websocket()

    async def _send_devtools_cmd(self, dc, receive=True):
        if self.websocket:
            self.cmd_id += 1
            dc["id"] = self.cmd_id
            await self.websocket.send_json(dc)

            if receive:
                async for msg in self.listen_for_message():
                    if "id" in msg and msg["id"] == dc["id"]:
                        return msg

            return None

        raise RuntimeError("Websocket not opened")

    async def close(self, manage_socket=True):
        try:
            if manage_socket:
                await self.open_websocket()

            res = await self._send_devtools_cmd({
                "method": "Page.close",
            }, False)

        finally:
            if manage_socket:
                await self.close_websocket()

        return res

    async def enable(self):
        """
        Enables page domain notifications.
        """
        await self._send_devtools_cmd({
            "method": "Page.enable",
        }, False)

    async def evaluate(self, js, wait=False):
        return await self._send_devtools_cmd({
            "method": "Runtime.evaluate",
            "params": {
                "expression": js
            }
        }, wait)

    async def set_request_interception(self, patterns = None):
        return await self._send_devtools_cmd({
            "method": "Network.setRequestInterception",
            "params": {
                "patterns": patterns
            }
        })

    async def enable_fetch(self, patterns = None):
        return await self._send_devtools_cmd({
            "method": "Fetch.enable",
            "params": {
                "patterns": patterns
            }
        }, False)

    async def enable_net(self):
        return await self._send_devtools_cmd({
            "method": "Network.enable"
        })

    async def disable_net(self):
        return await self._send_devtools_cmd({
            "method": "Network.disable"
        })

    async def disable_fetch(self):
        return await self._send_devtools_cmd({
            "method": "Fetch.disable",
        })

    async def continue_request(self, request_id, url=None):
        return await self._send_devtools_cmd({
            "method": "Fetch.continueRequest",
            "params": {
                "requestId": request_id,
                "url": url
                # "interceptResponse": intercept_response
            }
        }, False)

    async def fulfill_request(self, request_id, response_code=None, response_headers=None, body=None):
        return await self._send_devtools_cmd({
            "method": "Fetch.fulfillRequest",
            "params": {
                "requestId": request_id,
                "responseCode": response_code,
                "responseHeaders": response_headers,
                "body": body
            }
        }, False)


async def get_tabs() -> List[Tab]:
    res = {}

    na = False

    while True:
        try:
            async with ClientSession() as web:
                res = await web.get(f"{BASE_ADDRESS}/json", timeout=3)

        except ClientConnectorError:
            if not na:
                na = True
            await sleep(5)

        except ClientOSError:
            await sleep(1)

        except TimeoutError:
            await sleep(1)

        else:
            break

    if res.status == 200:
        r = await res.json()
        return [Tab(i) for i in r]

    else:
        raise Exception(f"/json did not return 200. {await res.text()}")


async def get_tab_lambda(test) -> Tab:
    tabs = await get_tabs()
    tab = next((i for i in tabs if test(i)), None)

    if not tab:
        raise ValueError(f"Tab not found by lambda")

    return tab


async def get_tab(tab_name) -> Tab:
    tabs = await get_tabs()
    tab = next((i for i in tabs if i.title == tab_name), None)

    if not tab:
        raise ValueError(f"Tab {tab_name} not found")

    return tab
