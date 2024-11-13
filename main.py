from aiohttp.web import ( # type: ignore
    Application,
    get,
    WebSocketResponse,
    AppRunner,
    TCPSite,
)
from asyncio import sleep, create_task, create_subprocess_exec
import aiohttp_cors # type: ignore
from json import dumps
from pathlib import Path
from subprocess import PIPE

import sys

from decky import logger, DECKY_PLUGIN_DIR # type: ignore
from logging import INFO

sys.path.append(DECKY_PLUGIN_DIR)

from tab_utils.tab import (
    create_discord_tab,
    setup_discord_tab,
    boot_discord,
    setOSK,
)
from tab_utils.cdp import Tab, get_tab
from discord_client.event_handler import EventHandler

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
    last_ws: WebSocketResponse = None

    @classmethod
    async def _main(cls):
        logger.info("Starting Deckcord backend")
        await initialize()
        logger.info("Discord initialized")

        cls.server.add_routes(
            [
                get("/openkb", cls._openkb),
                get("/socket", cls._websocket_handler),
                get("/frontend_socket", cls._frontend_socket_handler)
            ]
        )
        for r in list(cls.server.router.routes())[:-1]:
            cls.cors.add(r)

        cls.runner = AppRunner(cls.server, access_log=None)
        await cls.runner.setup()
        logger.info("Starting server.")
        await TCPSite(cls.runner, "0.0.0.0", 65123).start()

        cls.shared_js_tab = await get_tab("SharedJSContext")
        await cls.shared_js_tab.open_websocket()
        create_task(cls._notification_dispatcher())

        cls.webrtc_server = await create_subprocess_exec(
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
        create_task(stream_watcher(cls.webrtc_server.stdout))
        create_task(stream_watcher(cls.webrtc_server.stderr, True))

        while True:
            await sleep(3600)

    @classmethod
    async def _openkb(cls, request):
        await cls.shared_js_tab.ensure_open()
        await setOSK(cls.shared_js_tab, True)
        logger.info("Setting discord visibility to true")
        return "OK"

    @classmethod
    async def _websocket_handler(cls, request):
        logger.info("Received websocket connection!")
        ws = WebSocketResponse(max_msg_size=0)
        await ws.prepare(request)
        await cls.evt_handler.main(ws)
        return ws

    @classmethod
    async def _frontend_socket_handler(cls, request):
        if cls.last_ws:
            await cls.last_ws.close()

        logger.info("Received frontend websocket connection!")
        ws = WebSocketResponse(max_msg_size=0)
        cls.last_ws = ws
        await ws.prepare(request)

        async for state in cls.evt_handler.yield_new_state():
            await ws.send_json(state)

        return ws

    @classmethod
    async def _notification_dispatcher(cls):
        async for notification in cls.evt_handler.yield_notification():
            logger.info("Dispatching notification")
            payload = dumps(
                {"title": notification["title"], "body": notification["body"]}
            )
            await cls.shared_js_tab.ensure_open()
            await cls.shared_js_tab.evaluate(f"window.DECKCORD.dispatchNotification(JSON.parse('{payload}'));")

    @classmethod
    async def connect_ws(cls):
        await cls.shared_js_tab.ensure_open()
        await cls.shared_js_tab.evaluate(f"window.DECKCORD.connectWs()")

    @classmethod
    async def get_state(cls):
        return cls.evt_handler.build_state_dict()

    @classmethod
    async def toggle_mute(cls):
        logger.info("Toggling mute")
        return await cls.evt_handler.toggle_mute(act=True)

    @classmethod
    async def toggle_deafen(cls):
        logger.info("Toggling deafen")
        return await cls.evt_handler.toggle_deafen(act=True)

    @classmethod
    async def disconnect_vc(cls):
        logger.info("Disconnecting vc")
        return await cls.evt_handler.disconnect_vc()

    @classmethod
    async def set_ptt(cls, value):
        await cls.evt_handler.ws.send_json({"type": "$ptt", "value": value})

    @classmethod
    async def enable_ptt(cls, enabled):
        await cls.evt_handler.ws.send_json({"type": "$setptt", "enabled": enabled})

    @classmethod
    async def set_rpc(cls, game):
        logger.info("Setting RPC")
        await cls.evt_handler.ws.send_json({"type": "$rpc", "game": game})

    @classmethod
    async def get_last_channels(cls):
        return await cls.evt_handler.api.get_last_channels()

    @classmethod
    async def post_screenshot(cls, channel_id, data):
        logger.info("Posting screenshot to " + channel_id)
        r = await cls.evt_handler.api.post_screenshot(channel_id, data)

        if r:
            return True

        payload = dumps({"title": "Deckcord", "body": "Error while posting screenshot"})
        await cls.shared_js_tab.ensure_open()
        await cls.shared_js_tab.evaluate(
            f"DeckyPluginLoader.toaster.toast(JSON.parse('{payload}'));"
        )

    @classmethod
    async def get_screen_bounds(cls):
        return await cls.evt_handler.api.get_screen_bounds()

    @classmethod
    async def go_live(cls):
        await cls.evt_handler.ws.send_json({"type": "$golive", "stop": False})

    @classmethod
    async def stop_go_live(cls):
        await cls.evt_handler.ws.send_json({"type": "$golive", "stop": True})

    @classmethod
    async def mic_webrtc_answer(cls, answer):
        await cls.evt_handler.ws.send_json({"type": "$webrtc", "payload": answer})

    @classmethod
    async def _unload(cls):
        if hasattr(cls, "webrtc_server"):
            cls.webrtc_server.kill()
            await cls.webrtc_server.wait()

        if hasattr(cls, "runner"):
            await cls.runner.shutdown()
            await cls.runner.cleanup()

        if hasattr(cls, "shared_js_tab"):
            await cls.shared_js_tab.ensure_open()
            await cls.shared_js_tab.evaluate(
                """
                window.DISCORD_TAB.m_browserView.SetVisible(false);
                window.DISCORD_TAB.Destroy();
                window.DISCORD_TAB = undefined;
            """
            )
            await cls.shared_js_tab.close_websocket()
