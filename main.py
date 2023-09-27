from aiohttp.web import Application, get, WebSocketResponse, StreamResponse, route, AppRunner, TCPSite
from aiohttp import ClientSession
from asyncio import sleep, ensure_future, create_task
import aiohttp_cors
from ssl import create_default_context
from io import BytesIO
from json import dumps

import os, sys
sys.path.append(os.path.dirname(__file__))

from tab_utils.tab import create_discord_tab,  \
                          setup_discord_tab,              \
                          boot_discord,                   \
                          setOSK,                         \
                          set_discord_tab_visibility,      \
                          inject_client_to_discord_tab
from tab_utils.cdp import get_tab
from discord_client.event_handler import EventHandler
from proxy import process_fetch

from decky_plugin import logger
from logging import INFO
logger.setLevel(INFO)

class Plugin:
    server = Application()
    cors = aiohttp_cors.setup(server, defaults={
        "*": aiohttp_cors.ResourceOptions(
            expose_headers="*",
            allow_headers="*",
            allow_credentials=True
        )
    })
    evt_handler = EventHandler()

    async def initialize():
        await create_discord_tab()
        while True:
            try:
                tab = await setup_discord_tab()
                create_task(process_fetch(tab))
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

    async def _main(self):
        logger.info("Starting Deckcord backend")
        await Plugin.initialize()
        logger.info("Discord initialized")

        Plugin.server.add_routes([
            get("/openkb", Plugin._openkb),
            get("/socket", Plugin._websocket_handler),
            route("PUT", '/deckcord_upload/{tail:.*}', lambda req: Plugin._proxy(req, True)),
            route("*", '/{tail:.*}', Plugin._proxy),
        ])
        for r in list(Plugin.server.router.routes())[:-1]:
            Plugin.cors.add(r)
        Plugin.runner = AppRunner(Plugin.server, access_log=None)
        await Plugin.runner.setup()
        logger.info("Starting server.")
        await TCPSite(Plugin.runner, '0.0.0.0', 65123).start()

        Plugin.shared_js_tab = await get_tab("SharedJSContext")
        await Plugin.shared_js_tab.open_websocket()
        create_task(Plugin._frontend_evt_dispatcher())
        create_task(Plugin._notification_dispatcher())

        while True:
            await sleep(3600)
    
    async def _openkb(request):
        await Plugin.shared_js_tab.ensure_open()
        await setOSK(Plugin.shared_js_tab, True)
        logger.info("Setting discord visibility to true")
        return "OK"

    WD_SECONDS = 6
    counter = 0
    wd_task = None
    async def increment_counter():
        while True:
            if Plugin.counter == Plugin.WD_SECONDS:
                logger.fatal(f"Did not hear back from the discord tab in {Plugin.WD_SECONDS}. Re-initializing...")
                return
            Plugin.counter += 1
            await sleep(1)
    async def _websocket_handler(request):
        logger.info("Received websocket connection!")
        ws = WebSocketResponse()
        await ws.prepare(request)
        Plugin.wd_task = create_task(Plugin.increment_counter())
        Plugin.wd_task.add_done_callback(lambda: create_task(Plugin.initialize()))
        async for ping in Plugin.evt_handler.main(ws):
            if ping:
                Plugin.counter = 0
    
    async def _frontend_evt_dispatcher():
        async for state in Plugin.evt_handler.yield_new_state():
            async def _():
                await Plugin.shared_js_tab.ensure_open()
                await Plugin.shared_js_tab.evaluate(f"window.DECKCORD.setState(JSON.parse('{dumps(state)}'));")
            create_task(_())
    
    async def _notification_dispatcher():
        async for notification in Plugin.evt_handler.yield_notification():
            payload = dumps({
                'title': notification['title'],
                'body': notification['body']
            })
            await Plugin.shared_js_tab.ensure_open()
            await Plugin.shared_js_tab.evaluate(f"DeckyPluginLoader.toaster.toast(JSON.parse('{payload}'));")
        
    async def _proxy(request, is_upload=False):
        req_headers = { k: v for k, v in request.headers.items()}
        req_headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/app",
            "Host": "discord.com" if not is_upload else "discord-attachments-uploads-prd.storage.googleapis.com"
        })
        async with ClientSession(auto_decompress=False) as session:
            response = await session.request(request.method,
                f"https://discord.com/{request.rel_url}" if not is_upload else
                f"https://discord-attachments-uploads-prd.storage.googleapis.com/{str(request.rel_url).replace('/deckcord_upload/', '')}".strip(),
                ssl=create_default_context(cafile="/etc/ssl/cert.pem"),
                headers=req_headers,
                data=await request.read() if request.has_body else None
            )
            res_headers = { k: v for k, v in response.headers.items()}
            res_headers.update({
                "Access-Control-Allow-Origin": "https://steamloopback.host"
            })
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
    
    async def open_discord(*args):
        logger.info("Setting discord visibility to true")
        await Plugin.shared_js_tab.ensure_open()
        await set_discord_tab_visibility(Plugin.shared_js_tab, True)
    
    async def close_discord(*args):
        logger.info("Setting discord visibility to false")
        await Plugin.shared_js_tab.ensure_open()
        await set_discord_tab_visibility(Plugin.shared_js_tab, False)

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
        return await Plugin.evt_handler.api.post_screenshot(channel_id, data)

    async def _unload(*args):
        if hasattr(Plugin, "runner"):
            await Plugin.runner.cleanup()
        if hasattr(Plugin, "shared_js_tab"):
            await Plugin.shared_js_tab.ensure_open()
            await Plugin.shared_js_tab.evaluate("""
                window.DISCORD_TAB.m_browserView.SetVisible(false);
                window.DISCORD_TAB.Destroy();
                window.DISCORD_TAB = undefined;
            """)
            await Plugin.shared_js_tab.close_websocket()