from aiohttp.web import (
    Application,
    get,
    WebSocketResponse,
    AppRunner,
    TCPSite,
)
from asyncio import sleep, create_task, create_subprocess_exec
import aiohttp_cors
from json import dumps
from pathlib import Path
from subprocess import PIPE

import os, sys

sys.path.append(os.path.dirname(__file__))

from tab_utils.tab import (
    create_discord_tab,
    setup_discord_tab,
    boot_discord,
    setOSK,
)
from tab_utils.cdp import Tab, get_tab
from discord_client.event_handler import EventHandler

from decky_plugin import logger, DECKY_PLUGIN_DIR
from logging import INFO

logger.setLevel(INFO)


async def stream_watcher(stream, is_err=False):
    async for line in stream:
        line = line.decode("utf-8")
        if not line.strip():
            continue
        if is_err:
            logger.debug("ERROR: " + line)
        else:
            logger.debug(line)

async def initialize():
    tab = await create_discord_tab()
    await setup_discord_tab(tab)
    await boot_discord(tab)
    
    create_task(watchdog(tab))

async def watchdog(tab: Tab):
    while True:
        while not tab.websocket.closed:
            await sleep(1)
        logger.info("Discord tab websocket is no longer open. Trying to reconnect...")
        try:
            await tab.open_websocket()
            logger.info("Reconnected")
        except:
            break
    logger.info("Discord has died. Re-initializing...")
    while True:
        try:
            await initialize()
            break
        except:
            await sleep(1)

class Plugin:
    server = Application()
    cors = aiohttp_cors.setup(
        server,
        defaults={
            "*": aiohttp_cors.ResourceOptions(
                expose_headers="*", allow_headers="*", allow_credentials=True
            )
        },
    )
    evt_handler = EventHandler()

    async def _main(self):
        logger.info("Starting Deckcord backend")
        await initialize()
        logger.info("Discord initialized")

        Plugin.server.add_routes(
            [
                get("/openkb", Plugin._openkb),
                get("/socket", Plugin._websocket_handler),
                get("/frontend_socket", Plugin._frontend_socket_handler)
            ]
        )
        for r in list(Plugin.server.router.routes())[:-1]:
            Plugin.cors.add(r)
        Plugin.runner = AppRunner(Plugin.server, access_log=None)
        await Plugin.runner.setup()
        logger.info("Starting server.")
        await TCPSite(Plugin.runner, "0.0.0.0", 65123).start()

        Plugin.shared_js_tab = await get_tab("SharedJSContext")
        await Plugin.shared_js_tab.open_websocket()
        create_task(Plugin._notification_dispatcher())

        Plugin.webrtc_server = await create_subprocess_exec(
            "/usr/bin/python",
            str(Path(DECKY_PLUGIN_DIR) / "gst_webrtc.py"),
            env={
                "LD_LIBRARY_PATH": str(Path(DECKY_PLUGIN_DIR) / "bin"),
                "GI_TYPELIB_PATH": str(Path(DECKY_PLUGIN_DIR) / "bin/girepository-1.0"),
                "GST_PLUGIN_PATH": str(Path(DECKY_PLUGIN_DIR) / "bin/gstreamer-1.0"),
                "GST_VAAPI_ALL_DRIVERS": "1",
                "OPENSSL_CONF": "/etc/ssl/openssl.cnf",
                "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
                "XDG_RUNTIME_DIR": "/run/user/1000",
                "XDG_DATA_DIRS": "/home/deck/.local/share/flatpak/exports/share:/var/lib/flatpak/exports/share:/usr/local/share:/usr/share",
                "LIBVA_DRIVER_NAME": "radeonsi",
            },
            stdout=PIPE,
            stderr=PIPE,
        )
        create_task(stream_watcher(Plugin.webrtc_server.stdout))
        create_task(stream_watcher(Plugin.webrtc_server.stderr, True))

        while True:
            await sleep(3600)

    async def _openkb(request):
        await Plugin.shared_js_tab.ensure_open()
        await setOSK(Plugin.shared_js_tab, True)
        logger.info("Setting discord visibility to true")
        return "OK"

    async def _websocket_handler(request):
        logger.info("Received websocket connection!")
        ws = WebSocketResponse(max_msg_size=0)
        await ws.prepare(request)
        await Plugin.evt_handler.main(ws)
    

    last_ws: WebSocketResponse = None
    async def _frontend_socket_handler(request):
        if Plugin.last_ws:
            await Plugin.last_ws.close()
        logger.info("Received frontend websocket connection!")
        ws = WebSocketResponse(max_msg_size=0)
        Plugin.last_ws = ws
        await ws.prepare(request)
        async for state in Plugin.evt_handler.yield_new_state():
            await ws.send_json(state)

    async def _notification_dispatcher():
        async for notification in Plugin.evt_handler.yield_notification():
            logger.info("Dispatching notification")
            payload = dumps(
                {"title": notification["title"], "body": notification["body"]}
            )
            await Plugin.shared_js_tab.ensure_open()
            await Plugin.shared_js_tab.evaluate(f"window.DECKCORD.dispatchNotification(JSON.parse('{payload}'));")
    
    async def connect_ws(*args):
        await Plugin.shared_js_tab.ensure_open()
        await Plugin.shared_js_tab.evaluate(f"window.DECKCORD.connectWs()")

    async def get_state(*args):
        return Plugin.evt_handler.build_state_dict()

    async def toggle_mute(*args):
        logger.info("Toggling mute")
        return await Plugin.evt_handler.toggle_mute(act=True)

    async def toggle_deafen(*args):
        logger.info("Toggling deafen")
        return await Plugin.evt_handler.toggle_deafen(act=True)

    async def disconnect_vc(*args):
        logger.info("Disconnecting vc")
        return await Plugin.evt_handler.disconnect_vc()

    async def set_ptt(plugin, value):
        await Plugin.evt_handler.ws.send_json({"type": "$ptt", "value": value})

    async def enable_ptt(plugin, enabled):
        await Plugin.evt_handler.ws.send_json({"type": "$setptt", "enabled": enabled})

    async def set_rpc(plugin, game):
        logger.info("Setting RPC")
        await Plugin.evt_handler.ws.send_json({"type": "$rpc", "game": game})

    async def get_last_channels(plugin):
        return await plugin.evt_handler.api.get_last_channels()

    async def post_screenshot(plugin, channel_id, data):
        logger.info("Posting screenshot to " + channel_id)
        r = await Plugin.evt_handler.api.post_screenshot(channel_id, data)
        if r:
            return True
        payload = dumps({"title": "Deckcord", "body": "Error while posting screenshot"})
        await Plugin.shared_js_tab.ensure_open()
        await Plugin.shared_js_tab.evaluate(
            f"DeckyPluginLoader.toaster.toast(JSON.parse('{payload}'));"
        )

    async def get_screen_bounds(plugin):
        return await plugin.evt_handler.api.get_screen_bounds()
    
    async def go_live(plugin):
        await plugin.evt_handler.ws.send_json({"type": "$golive", "stop": False})

    async def stop_go_live(plugin):
        await plugin.evt_handler.ws.send_json({"type": "$golive", "stop": True})

    async def mic_webrtc_answer(plugin, answer):
        await plugin.evt_handler.ws.send_json({"type": "$webrtc", "payload": answer})

    async def _unload(*args):
        if hasattr(Plugin, "webrtc_server"):
            Plugin.webrtc_server.kill()
            await Plugin.webrtc_server.wait()
        if hasattr(Plugin, "runner"):
            await Plugin.runner.shutdown()
            await Plugin.runner.cleanup()
        if hasattr(Plugin, "shared_js_tab"):
            await Plugin.shared_js_tab.ensure_open()
            await Plugin.shared_js_tab.evaluate(
                """
                window.DISCORD_TAB.m_browserView.SetVisible(false);
                window.DISCORD_TAB.Destroy();
                window.DISCORD_TAB = undefined;
            """
            )
            await Plugin.shared_js_tab.close_websocket()
