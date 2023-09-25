from pathlib import Path

from aiohttp import ClientSession
from .cdp import Tab, get_tab, get_tab_lambda, get_tabs
from asyncio import sleep
from ssl import create_default_context

async def create_discord_tab():
    while True:
        try:
            tab = await get_tab("SharedJSContext")
            break
        except:
            await sleep(0.1)
    await tab.open_websocket()
    while True:
        await tab.evaluate("""
                    if (window.DISCORD_TAB !== undefined) {
                        window.DISCORD_TAB.m_browserView.SetVisible(false);
                        window.DISCORD_TAB.Destroy();
                        //window.DISCORD_TAB.unregisterCloseKeybind();
                        window.DISCORD_TAB = undefined;
                    }
                    window.DISCORD_TAB = window.DFL.Router.WindowStore.GamepadUIMainWindowInstance.CreateBrowserView("discord");
                    window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 495);
                    window.DISCORD_TAB.m_browserView.LoadURL("https://steamloopback.host/discord/init");
                        
                    DFL.Router.WindowStore.GamepadUIMainWindowInstance.m_VirtualKeyboardManager.IsShowingVirtualKeyboard.m_callbacks.m_vecCallbacks.push((e) => {
                        if (!e) {
                            const bounds = window.DISCORD_TAB.m_browserView.GetBounds();
                            if (bounds.height != 495) {
                                window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 495);
                            }
                        }
                    });
                    /*window.DISCORD_TAB.unregisterCloseKeybind = SteamClient.Input.RegisterForControllerInputMessages(e => {
                        const ev = e[0];
                        if (ev.nA == 1 && !ev.bS && window.DISCORD_TAB.m_refKeyboard.BIsActive()) {
                        console.log("closing...")
                        fetch("http://127.0.0.1:65123/close", { mode: "no-cors" });
                        }
                    }).unregister;*/
        """)
        await sleep(3)
        try:
            await get_tab_lambda(lambda tab: tab.url == "https://steamloopback.host/discord/init")
            break
        except:
            pass
    await tab.close_websocket()

async def fetch_vencord():
    async with ClientSession() as session:
        res = await session.get("https://raw.githubusercontent.com/Vencord/builds/main/Vencord.user.js",
                                ssl=create_default_context(cafile="/etc/ssl/cert.pem"))
        if res.ok:
            return await res.text()

async def setup_discord_tab():
    tab = await get_tab_lambda(lambda tab: tab.url == "https://steamloopback.host/discord/init")
    await tab.open_websocket()
    await tab.enable()
    await tab._send_devtools_cmd({
        "method": "Page.addScriptToEvaluateOnNewDocument",
        "params": {
            "source": "window.unsafeWindow = window; " + (await fetch_vencord()),
            "runImmediately": True
        }
    })
    await tab.enable_fetch([
        {
            "urlPattern": "https://discord.com/assets/*",
            "requestStage": "Request"
        },
        {
            "urlPattern":"https://discord.com/api/*/auth/*",
            "requestStage": "Request" 
        }
    ])
    return tab

async def boot_discord():
    tab = await get_tab_lambda(lambda tab: tab.url == "https://steamloopback.host/discord/init")
    await tab.open_websocket()
    await tab._send_devtools_cmd({
        "method": "Page.navigate",
        "params": {
            "url": "https://steamloopback.host/index.html",
            "transitionType": "address_bar"
        }
    })
    await tab.close_websocket()

async def inject_client_to_discord_tab():
    tab = next(tab for tab in (await get_tabs()) if "Discord" in tab.title)
    if not tab:
        return
    await tab.open_websocket()
    await tab.evaluate(open(Path(__file__).parent.parent.joinpath("deckcord_client.js"), "r").read())
    await tab.close_websocket()

async def setOSK(tab: Tab, state):
    await tab.open_websocket()
    if state:
        await tab.evaluate("DISCORD_TAB.m_virtualKeyboardHost.m_showKeyboard()")
        await tab.evaluate("window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 295)")
    else:
        await tab.evaluate("DISCORD_TAB.m_virtualKeyboardHost.m_hideKeyboard()")
        await tab.evaluate("window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 495)")
    await tab.close_websocket()

async def set_discord_tab_visibility(tab: Tab, visibility):
    await tab.open_websocket()
    await tab.evaluate(f"""
        window.DISCORD_TAB.m_browserView.SetVisible({'true' if visibility else 'false'});
        window.DISCORD_TAB.m_browserView.SetFocus({'true' if visibility else 'false'})
    """)
    await tab.close_websocket()