from aiohttp.web import (
    Application,
    get,
    put,
    WebSocketResponse,
    StreamResponse,
    route,
    AppRunner,
    TCPSite,
)
from aiohttp import ClientResponse, ClientSession, TCPConnector, WSServerHandshakeError
from asyncio import gather, sleep, ensure_future, create_task, create_subprocess_exec
import aiohttp_cors
from ssl import create_default_context
from io import BytesIO
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
    inject_client_to_discord_tab,
)
from tab_utils.cdp import Tab, get_tab
from discord_client.event_handler import EventHandler
from proxy import process_fetch, ws_forward

from decky_plugin import logger, DECKY_PLUGIN_DIR
from logging import INFO

logger.setLevel(INFO)


async def stream_watcher(stream, is_err=False):
    async for line in stream:
        line = line.decode("utf-8")
        if not line.strip():
            continue
        if is_err:
            logger.error(line)
        else:
            logger.info(line)

async def initialize():
    await create_discord_tab()
    while True:
        try:
            tab = await setup_discord_tab()
            create_task(process_fetch(tab))
            create_task(watchdog(tab))
            break
        except Exception as e:
            await sleep(0.1)
    while True:
        try:
            await boot_discord()
            break
        except:
            await sleep(0.1)

    async def _():
        while True:
            try:
                await inject_client_to_discord_tab()
                break
            except:
                await sleep(0.1)

    ensure_future(_())

async def watchdog(tab: Tab):
    while True:
        while not tab.websocket.closed:
            await sleep(1)
        logger.info("Discord tab websocket is no longer open. Trying to reconnect...")
        try:
            await tab.open_websocket()
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
                get("/authws", Plugin._auth_websocket_handler),
                put("/deckcord_upload/{tail:.*}", lambda req: Plugin._proxy(req, True)),
                route("*", "/{tail:.*}", Plugin._proxy),
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
        create_task(Plugin._frontend_evt_dispatcher())
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

    async def _auth_websocket_handler(request: ClientResponse):
        ws = WebSocketResponse(max_msg_size=0)
        await ws.prepare(request)
        async with ClientSession(connector=TCPConnector(ssl=True)) as session:
            headers = {"Origin": "https://discord.com"}
            try:
                async with session.ws_connect(
                    "wss://remote-auth-gateway.discord.gg/?v=2",
                    headers=headers,
                    ssl=create_default_context(cafile="/etc/ssl/cert.pem"),
                ) as target_ws:
                    await gather(ws_forward(ws, target_ws), ws_forward(target_ws, ws))
            except WSServerHandshakeError as e:
                logger.error(str(e))

    async def _frontend_evt_dispatcher():
        async for state in Plugin.evt_handler.yield_new_state():

            async def _():
                await Plugin.shared_js_tab.ensure_open()
                await Plugin.shared_js_tab.evaluate(
                    f"window.DECKCORD.setState(JSON.parse('{dumps(state)}'));"
                )

            create_task(_())

    async def _notification_dispatcher():
        async for notification in Plugin.evt_handler.yield_notification():
            payload = dumps(
                {"title": notification["title"], "body": notification["body"]}
            )
            await Plugin.shared_js_tab.ensure_open()
            await Plugin.shared_js_tab.evaluate(
                f"DeckyPluginLoader.toaster.toast(JSON.parse('{payload}'));"
            )

    async def _proxy(request, is_upload=False):
        req_headers = {k: v for k, v in request.headers.items()}
        req_headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                "Origin": "https://discord.com",
                "Referer": "https://discord.com/app",
                "Host": "discord.com"
                if not is_upload
                else "discord-attachments-uploads-prd.storage.googleapis.com",
            }
        )
        async with ClientSession(auto_decompress=False) as session:
            response = await session.request(
                request.method,
                f"https://discord.com/{request.rel_url}"
                if not is_upload
                else f"https://discord-attachments-uploads-prd.storage.googleapis.com/{str(request.rel_url).replace('/deckcord_upload/', '')}".strip(),
                ssl=create_default_context(cafile="/etc/ssl/cert.pem"),
                headers=req_headers,
                data=await request.read() if request.has_body else None,
            )
            res_headers = {k: v for k, v in response.headers.items()}
            res_headers.update(
                {"Access-Control-Allow-Origin": "https://steamloopback.host"}
            )
            content = BytesIO(await response.content.read())
            status = response.status
            if not response.ok:
                logger.debug(response.request_info)
                logger.debug(response)
                logger.debug(response.status)
                logger.debug(res_headers)
            response.close()
        b = content.read()
        res = StreamResponse(status=status, headers=res_headers)
        if is_upload:
            res.headers.pop("Access-Control-Allow-Origin")
            res.headers.pop("Access-Control-Expose-Headers")
        await res.prepare(request)
        await res.write(b)
        return res

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
