#import decky_plugin
from aiohttp.web import Application, get, _run_app, WebSocketResponse, json_response, StreamResponse, route
from aiohttp import ClientSession
from asyncio import run, sleep, ensure_future, create_task
import aiohttp_cors
from ssl import create_default_context
from certifi import where
from io import BytesIO
from traceback import format_exc

from py_modules.tab_utils.tab import create_discord_tab,  \
                          setup_discord_tab,              \
                          boot_discord,                   \
                          setOSK,                         \
                          set_discord_tab_visibility,      \
                          inject_client_to_discord_tab
from py_modules.discord_client.event_handler import EventHandler
from py_modules.proxy import process_fetch

SSL_CTX = create_default_context(cafile=where())

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

    async def _main(self):
        await create_discord_tab()
        await sleep(1)
        tab = await setup_discord_tab()
        create_task(process_fetch(tab))
        async def _():
            await sleep(5)
            await boot_discord()
            await sleep(3)
            await inject_client_to_discord_tab()
        ensure_future(_())

        self.server.add_routes([
            get("/close", self._close),
            get("/open", self._open),
            get("/openkb", self._openkb),
            get("/socket", self._websocket_handler),
            get("/storeget", self._storeget),
            route("*", '/{tail:.*}', self._proxy)
        ])
        self.cors.add(list(self.server.router.routes())[0])
        ensure_future(self.evt_handler.print_status())
        await _run_app(self.server, host="127.0.0.1", port=65123)
    
    async def _close(self, request):
        await set_discord_tab_visibility(False)
        return "OK"
    
    async def _open(self, request):
        await set_discord_tab_visibility(True)
        return "OK"
    
    async def _openkb(self, request):
        await setOSK(True)
        return "OK"

    async def _websocket_handler(self, request):
        ws = WebSocketResponse()
        await ws.prepare(request)
        await self.evt_handler.main(ws)
        return ws
    
    async def _storeget(self, request):
        req = request.query.get("type")
        id = request.query.get("id")
        if req == "user":
            return json_response(await self.evt_handler.api.get_user(id))
        elif req == "channel":
            return json_response(await self.evt_handler.api.get_channel(id))
        elif req == "guild":
            return json_response(await self.evt_handler.api.get_guild(id))
        
    async def _proxy(self, request):
        try:
            #print("got request %s", request.rel_url)
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
    
    async def get_state(self):
        d = self.rpc.build_state_dict()
        return d
    
    async def toggle_mute(self):
        return await self.rpc.toggle_mute(act=True)
    
    async def toggle_deafen(self):
        return await self.rpc.toggle_deafen(act=True)
    
    async def disconnect_vc(self):
        return await self.rpc.disconnect_vc()

    async def _unload(self):
        await self.rpc.stop()

if __name__ == "__main__":
    run(Plugin()._main())