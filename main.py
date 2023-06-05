#import decky_plugin
from aiohttp.web import Application, post, _run_app, Response
from asyncio import get_event_loop, run
from json import dumps
from py_modules import discord
import aiohttp_cors

class Plugin:
    server = Application()
    cors = aiohttp_cors.setup(server, defaults={
        "https://discord.com": aiohttp_cors.ResourceOptions(
            expose_headers="*",
            allow_headers="*",
            allow_credentials=True
        )
    })
    rpc: discord.RpcClient = None
    overlay_url = ""
    rpc_token = ""

    async def _submit_auth(self, request):
        data = await request.post()
        if self.rpc_token != data["rpc_token"]:
            self.overlay_url = data["overlay_url"]
            self.rpc_token = data["rpc_token"]
#            decky_plugin.logger.info("Received auth keys. Starting RPC Client")

            if self.rpc:
#                decky_plugin.logger.info("Stopping old RPC Client")
                await self.rpc.stop()
            self.rpc = discord.RpcClient(self.rpc_token)
            get_event_loop().create_task(self.rpc._main())
        return Response(status=200, body="OK")

    async def _main(self):
        self.server.add_routes([post("/submit_auth", self._submit_auth)])
        self.cors.add(list(self.server.router.routes())[0])
        await _run_app(self.server, host="127.0.0.1", port=65123)
    
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