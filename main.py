#import decky_plugin
from aiohttp.web import Application, get, _run_app, WebSocketResponse, json_response
from asyncio import run, sleep, ensure_future
import aiohttp_cors

from py_modules.tab_utils import inject_vencord_open_discord, \
                                 start_discord_tab, \
                                 set_discord_tab_visibility, \
                                 inject_client_to_discord_tab, \
                                 setOSK
from py_modules.discord_client.event_handler import EventHandler


async def start_discord():
    await start_discord_tab()
    await sleep(0.5)
    await inject_vencord_open_discord()
    await sleep(1)
    await inject_client_to_discord_tab()

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
        ensure_future(start_discord())

        self.server.add_routes([
            get("/close", self._close),
            get("/open", self._open),
            get("/openkb", self._openkb),
            get("/socket", self._websocket_handler),
            get("/storeget", self._storeget)
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
    
    async def get_state(self):
        d = self.rpc.build_state_dict()
#        decky_plugin.logger.debug(d)
        return d
    
    async def toggle_mute(self):
#        decky_plugin.logger.debug("Toggling mute")
        return await self.rpc.toggle_mute(act=True)
    
    async def toggle_deafen(self):
#        decky_plugin.logger.debug("Toggling deafen")
        return await self.rpc.toggle_deafen(act=True)
    
    async def disconnect_vc(self):
#        decky_plugin.logger.debug("Disconnecting vc")
        return await self.rpc.disconnect_vc()

    async def _unload(self):
#        decky_plugin.logger.info("Goodbye World!")
        await self.rpc.stop()

run(Plugin()._main())