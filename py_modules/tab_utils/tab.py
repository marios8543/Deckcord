from .cdp import get_tab, get_tab_lambda, get_tabs
from pathlib import Path

async def create_discord_tab():
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
                window.DISCORD_TAB.m_browserView.LoadURL("https://steamloopback.host/discord/init");
                       
                DFL.Router.WindowStore.GamepadUIMainWindowInstance.m_VirtualKeyboardManager.IsShowingVirtualKeyboard.m_callbacks.m_vecCallbacks.push((e) => {
                    if (!e) {
                        const bounds = window.DISCORD_TAB.m_browserView.GetBounds();
                        if (bounds.height != 530) {
                            window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 530);
                        }
                    }
                })
    """)
    await tab.close_websocket()

async def setup_discord_tab():
    tab = await get_tab_lambda(lambda tab: tab.url == "https://steamloopback.host/discord/init")
    await tab.open_websocket()
    await tab.enable()
    await tab._send_devtools_cmd({
        "method": "Page.addScriptToEvaluateOnNewDocument",
        "params": {
            "source": "window.unsafeWindow = window; " + open(Path(__file__).parent.parent.parent.joinpath(Path("defaults/Vencord.user.js")), "r").read(),
            "runImmediately": True
        }
    })
    #await tab._send_devtools_cmd({
    #    "method": "Emulation.setUserAgentOverride",
    #    "params": {
    #        "userAgent": "Mozilla/5.0 (X11; Linux x86_64; Valve Steam Client/default/1691097434) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
    #    }
    #})
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
    await tab.evaluate(open(Path(__file__).parent.parent.parent.joinpath(Path("defaults/deckcord_client.js")), "r").read())
    await tab.close_websocket()

async def setOSK(state):
    tab = await get_tab("SharedJSContext")
    await tab.open_websocket()
    if state:
        await tab.evaluate("DFL.Router.WindowStore.GamepadUIMainWindowInstance.m_VirtualKeyboardManager.m_lastActiveVirtualKeyboardRef.ShowVirtualKeyboard()")
        await tab.evaluate("window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 295)")
    else:
        await tab.evaluate("DFL.Router.WindowStore.GamepadUIMainWindowInstance.m_VirtualKeyboardManager.m_lastActiveVirtualKeyboardRef.ShowVirtualKeyboard()")
        await tab.evaluate("window.DISCORD_TAB.m_browserView.SetBounds(0,0, 860, 530)")
    await tab.close_websocket()