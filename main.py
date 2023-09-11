from aiohttp.web import Application, get, WebSocketResponse, json_response, StreamResponse, route, AppRunner, TCPSite
from aiohttp import ClientSession
from asyncio import sleep, ensure_future, create_task
import aiohttp_cors
from ssl import create_default_context
from io import BytesIO
from traceback import format_exc
from json import dumps

import os, sys
sys.path.append(os.path.dirname(__file__))

from tab_utils.tab import create_discord_tab,  \
                          setup_discord_tab,              \
                          boot_discord,                   \
                          setOSK,                         \
                          set_discord_tab_visibility,      \
                          inject_client_to_discord_tab
from tab_utils.cdp import get_tab, get_tab_lambda
from discord_client.event_handler import EventHandler
from proxy import process_fetch

from decky_plugin import logger
logger.setLevel(10)

SSL_CTX = create_default_context(cafile="/home/deck/.local/lib/python3.10/site-packages/certifi/cacert.pem")

class Plugin:
    server = Application()
    cors = aiohttp_cors.setup(server, defaults={
        "https://discord.com": aiohttp_cors.ResourceOptions(
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
            except:
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
        await Plugin.initialize()
        Plugin.server.add_routes([
            get("/close", Plugin._close),
            get("/open", Plugin._open),
            get("/openkb", Plugin._openkb),
            get("/socket", Plugin._websocket_handler),
            get("/storeget", Plugin._storeget),
            route("*", '/{tail:.*}', Plugin._proxy)
        ])
        Plugin.cors.add(list(Plugin.server.router.routes())[0])
        Plugin.runner = AppRunner(Plugin.server, access_log=None)
        await Plugin.runner.setup()
        logger.info("Starting server!!!")
        await TCPSite(Plugin.runner, '127.0.0.1', 65123).start()
        Plugin.shared_js_tab = await get_tab("SharedJSContext")
        await Plugin.shared_js_tab.open_websocket()
        create_task(Plugin._frontend_evt_dispatcher())
        create_task(Plugin._notification_dispatcher())
        while True:
            await sleep(3600)
    
    async def _close(request):
        await Plugin.shared_js_tab.ensure_open()
        await set_discord_tab_visibility(Plugin.shared_js_tab, False)
        logger.info("Setting discord visibility to false")
        return "OK"
    
    async def _open(request):
        await Plugin.shared_js_tab.ensure_open()
        await set_discord_tab_visibility(Plugin.shared_js_tab, True)
        return "OK"
    
    async def _openkb(request):
        await Plugin.shared_js_tab.ensure_open()
        await setOSK(Plugin.shared_js_tab, True)
        logger.info("Setting discord visibility to true")
        return "OK"

    async def _websocket_handler(request):
        logger.info("Received websocket connection!")
        ws = WebSocketResponse()
        await ws.prepare(request)
        await Plugin.evt_handler.main(ws)
        return ws
    
    async def _frontend_evt_dispatcher():
        async for state in Plugin.evt_handler.yield_new_state():
            async def _():
                await Plugin.shared_js_tab.ensure_open()
                Plugin.shared_js_tab.evaluate(f"window.DECKCORD.setState(JSON.parse('{dumps(state)}'));")
            create_task(_())
    
    async def _notification_dispatcher():
        async for notification in Plugin.evt_handler.yield_notification():
            payload = dumps({
                'title': notification['title'],
                'body': notification['body']
            })
            await Plugin.shared_js_tab.ensure_open()
            await Plugin.shared_js_tab.evaluate(f"DeckyPluginLoader.toaster.toast(JSON.parse('{payload}'));")
    
    async def _storeget(request):
        req = request.query.get("type")
        id = request.query.get("id")
        if req == "user":
            return json_response(await Plugin.evt_handler.api.get_user(id))
        elif req == "channel":
            return json_response(await Plugin.evt_handler.api.get_channel(id))
        elif req == "guild":
            return json_response(await Plugin.evt_handler.api.get_guild(id))
        
    async def _proxy(request):
        try:
            req_headers = { k: v for k, v in request.headers.items()}
            req_headers.update({
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                "Origin": "https://discord.com",
                "Referer": "https://discord.com/app",
                "Host": "discord.com"
            })
            async with ClientSession(auto_decompress=False) as session:
                response = await session.request(request.method,
                    f"https://discord.com/{request.rel_url}",
                    ssl=SSL_CTX,
                    headers=req_headers,
                    data=await request.read() if request.has_body else None
                )

                res_headers = { k: v for k, v in response.headers.items()}
                res_headers.update({
                    "Access-Control-Allow-Origin": "https://steamloopback.host"
                })
                content = BytesIO(await response.content.read())
                status = response.status
                response.close()
        except Exception as e:
            print("Error in request %s", format_exc())
        b = content.read()
        res = StreamResponse(status=status, headers=res_headers)
        await res.prepare(request)
        await res.write(b)
        return res
    
    async def get_state(*args):
        s = Plugin.evt_handler.build_state_dict()
        #logger.info("STATE", s)
        return s
    
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
        await set_discord_tab_visibility(Plugin.shared_js_tab, True)
    
    async def close_discord(*args):
        logger.info("Setting discord visibility to false")
        await set_discord_tab_visibility(Plugin.shared_js_tab, False)

    async def set_ptt(plugin, value):
        await Plugin.evt_handler.ws.send_json({"type": "$ptt", "value": value})

    async def _unload(*args):
        if hasattr(Plugin, "runner"):
            await Plugin.runner.cleanup()