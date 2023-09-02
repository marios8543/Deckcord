from json import dumps, loads
from asyncio import sleep, get_event_loop, Task
from aiohttp import WSMsgType
from aiohttp.web import WebSocketResponse
from traceback import print_exception

from .store_access import StoreAccess, User

class EventHandler:
    def __init__(self) -> None:
        self.ws: WebSocketResponse
        self.api = StoreAccess()
        self.event_handlers = {
            "READY": self._ready,
            "VOICE_STATE_UPDATES": self._voice_state_update,
            "VOICE_CHANNEL_SELECT": self._voice_channel_select,
            "AUDIO_TOGGLE_SELF_MUTE": self.toggle_mute,
            "AUDIO_TOGGLE_SELF_DEAF": self.toggle_deafen
        }

        self.me = User({"id": "", "username": "", "discriminator": None, "avatar": ""})
        self.voicestates = {}

        self.vc_channel_id = ""
        self.vc_channel_name = ""
        self.vc_guild_name = ""
    
    async def _process_event(self, data):
        if data["type"] == "$deckcord_request":
            self.api._set_result(data["increment"], data["result"])
            return
        if data["type"] in self.event_handlers:
            callback = self.event_handlers[data["type"]]
            #print(dumps(data, indent=2)+"\n\n")
        else:
            return
        def _(future: Task):
            e = future.exception()
            if e:
                print(f"Exception during handling of {data['type']} event.   {e}")
                print_exception(e)
        get_event_loop().create_task(callback(data)).add_done_callback(_)
    
    async def print_status(self):
        old_dict = {}
        while True:
            dc = self.build_state_dict()
            if old_dict != dc:
                print(dumps(dc, indent=2)+"\n\n")
                old_dict = dc
            await sleep(0.1)

    async def main(self, ws):
        self.ws = ws
        self.api.ws = ws
        async for msg in self.ws:
            if msg.type == WSMsgType.TEXT:
                await self._process_event(loads(msg.data))
            elif msg.type == WSMsgType.ERROR:
                print('ws connection closed with exception %s' % self.ws.exception())

    async def _ready(self, data):
        self.me = User(data["result"]["user"])
        self.me.is_muted = data["result"]["mute"]
        self.me.is_deafened = data["result"]["deaf"]

    async def _voice_channel_select(self, data):
        self.vc_channel_id = data["channelId"]
        if not self.vc_channel_id:
            self.vc_channel_name = ""
            self.vc_guild_name = ""
            return 
        self.vc_channel_name = (await self.api.get_channel(self.vc_channel_id))["name"]
        self.vc_guild_name = (await self.api.get_guild(data["guildId"]))["name"]
        for user in self.voicestates[self.vc_channel_id].values():
            await user.populate(self.api)
    
    async def _voice_state_update(self, data):
        states = data["voiceStates"]
        for state in states:
            if "oldChannelId" in state and state["oldChannelId"] in self.voicestates:
                self.voicestates[state["oldChannelId"]].pop(state["userId"], None)
                if not self.voicestates[state["oldChannelId"]]:
                    self.voicestates.pop(state["oldChannelId"], None)
            if state["userId"] == self.me.id:
                user_to_add = self.me
            else:
                user_to_add = User.from_vc(state)
            if state["channelId"] in self.voicestates:
                self.voicestates[state["channelId"]][state["userId"]] = user_to_add
            else:
                self.voicestates[state["channelId"]] = {state["userId"]: user_to_add}

    def build_state_dict(self):
        r = {
            "me": self.me.to_dict(),
            "vc": {}
        }
        if self.vc_channel_id:
            r["vc"]["channel_name"] = self.vc_channel_name
            r["vc"]["guild_name"] = self.vc_guild_name
            r["vc"]["users"] = []
            if self.vc_channel_id in self.voicestates:
                for user in self.voicestates[self.vc_channel_id].values():
                    r["vc"]["users"].append(user.to_dict())
        return r

    async def toggle_mute(self, *args, act=False):
        if act:
            await self.ws.send_json({"type": 'AUDIO_TOGGLE_SELF_MUTE', "context": 'default', "syncRemote": True})
        self.me.is_muted = not self.me.is_muted
    
    async def toggle_deafen(self, *args, act=False):
        if act:
            await self.ws.send_json({"type": 'AUDIO_TOGGLE_SELF_DEAF', "context": 'default', "syncRemote": True})
        self.me.is_deafened = not self.me.is_deafened
    
    async def disconnect_vc(self):
        await self.ws.send_json({"type":"VOICE_CHANNEL_SELECT","guildId":None,"channelId":None,"currentVoiceChannelId":self.vc_channel_id,"video":False,"stream":False})