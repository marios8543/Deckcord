# Injector code from https://github.com/SteamDeckHomebrew/steamdeck-ui-inject. More info on how it works there.

from asyncio import sleep, run
from typing import List

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError, ClientOSError
from asyncio.exceptions import TimeoutError
from pathlib import Path

BASE_ADDRESS = "http://192.168.1.2:8081"

class Tab:
    cmd_id = 0

    def __init__(self, res) -> None:
        self.title = res["title"]
        self.id = res["id"]
        self.url = res["url"]
        self.ws_url = res["webSocketDebuggerUrl"]

        self.websocket = None
        self.client = None

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

    async def evaluate(self, js):
        return await self._send_devtools_cmd({
            "method": "Runtime.evaluate",
            "params": {
                "expression": js
            }
        })

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

async def get_tab(tab_name) -> Tab:
    tabs = await get_tabs()
    tab = next((i for i in tabs if i.title == tab_name), None)
    if not tab:
        raise ValueError(f"Tab {tab_name} not found")
    return tab

async def start_discord_tab():
    tab = await get_tab("SharedJSContext")
    await tab.open_websocket()
    await tab.evaluate("""
                if (window.DISCORD_TAB !== undefined) {
                    window.DISCORD_TAB.m_browserView.SetVisible(false);
                    window.DISCORD_TAB.Destroy();
                    window.DISCORD_TAB = undefined;
                }
                window.DISCORD_TAB = window.DFL.Router.WindowStore.GamepadUIMainWindowInstance.CreateBrowserView("discord");
                window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 530);
                window.DISCORD_TAB.m_browserView.LoadURL("data:text/plain,to_be_discord");

                setInterval(() => {
                    if (!window.DISCORD_TAB.m_refKeyboard.BIsActive()) {
                        const bounds = window.DISCORD_TAB.m_browserView.GetBounds();
                        if (bounds.height != 530) {
                            window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 530);
                        }
                    }
                }, 100);
                       """)
    await tab.close_websocket()

async def inject_vencord_open_discord():
    tab = await get_tab("data:text/plain,to_be_discord")
    await tab.open_websocket()
    await tab.enable()
    await tab._send_devtools_cmd({
        "method": "Page.addScriptToEvaluateOnNewDocument",
        "params": {
            "source": "window.unsafeWindow = window; " + open(Path(__file__).parent.parent.joinpath(Path("defaults/Vencord.user.js")), "r").read(),
            "runImmediately": True
        }
    })
    await tab._send_devtools_cmd({
        "method": "Page.navigate",
        "params": {
            "url": "https://discord.com/app",
            "transitionType": "address_bar"
        }
    })
    await tab.close_websocket()

async def set_discord_tab_visibility(visibility):
    tab = await get_tab("SharedJSContext")
    await tab.open_websocket()
    await tab.evaluate(f"window.DISCORD_TAB.m_browserView.SetVisible({'true' if visibility else 'false'})")
    await tab.close_websocket()

async def inject_client_to_discord_tab():
    tab = next(tab for tab in (await get_tabs()) if "Discord" in tab.title)
    if not tab:
        return
    await tab.open_websocket()
    await tab.evaluate(open(Path(__file__).parent.parent.joinpath(Path("defaults/deckcord_client.js")), "r").read())

async def setOSK(state):
    tab = await get_tab("SharedJSContext")
    await tab.open_websocket()
    if state:
        await tab.evaluate("window.DISCORD_TAB.m_refKeyboard.ShowVirtualKeyboard()")
        await tab.evaluate("window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 295)")
    else:
        await tab.evaluate("window.DISCORD_TAB.m_refKeyboard.HideVirtualKeyboard()")
        await tab.evaluate("window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 530)")
    await tab.close_websocket()