from json import dumps, loads
from asyncio import sleep, get_event_loop, Task, Event, Queue
from aiohttp import WSMsgType # type: ignore
from aiohttp.web import WebSocketResponse # type: ignore
from traceback import print_exception

from .store_access import StoreAccess, User
from decky import logger # type: ignore

class EventHandler:
    def __init__(self) -> None:
        self.ws: WebSocketResponse
        self.api = StoreAccess()
        self.state_changed_event = Event()
        self.notification_queue = Queue()
        self.event_handlers = {
            "LOADED": self._loaded,
            "CONNECTION_OPEN": self._logged_in,
            "LOGOUT": self._logout,
            "CONNECTION_CLOSED": self._logout,
            "VOICE_STATE_UPDATES": self._voice_state_update,
            "VOICE_CHANNEL_SELECT": self._voice_channel_select,
            "AUDIO_TOGGLE_SELF_MUTE": self.toggle_mute,
            "AUDIO_TOGGLE_SELF_DEAF": self.toggle_deafen,
            "RPC_NOTIFICATION_CREATE": self._notification_create,
            "STREAM_STOP": self.toggle_mute,
            "STREAM_START": self.toggle_mute,
            "$MIC_WEBRTC": self._webrtc_mic_forward,
        }

        self.loaded = False
        self.logged_in = False
        self.me = User({"id": "", "username": "", "discriminator": None, "avatar": ""})
        self.voicestates = {}

        self.vc_channel_id = ""
        self.vc_channel_name = ""
        self.vc_guild_name = ""

        self.webrtc = None
    
    async def yield_new_state(self):
        while True:
            await self.state_changed_event.wait()
            dc = self.build_state_dict()
            yield dc
            self.state_changed_event.clear()
    
    async def yield_notification(self):
        while True:
            yield await self.notification_queue.get()

    def build_state_dict(self):

        r = {
            "loaded": self.loaded,
            "logged_in": self.logged_in,
            "me": self.me.to_dict(),
            "vc": {},
            "webrtc": self.webrtc.copy() if self.webrtc else None
        }
        if self.vc_channel_id:
            r["vc"]["channel_name"] = self.vc_channel_name
            r["vc"]["guild_name"] = self.vc_guild_name
            r["vc"]["users"] = []
            if self.vc_channel_id in self.voicestates:
                for user in self.voicestates[self.vc_channel_id].values():
                    r["vc"]["users"].append(user.to_dict())
        
        if self.webrtc:
            self.webrtc = None
        return r

    async def toggle_mute(self, *args, act=False):
        if act:
            await self.ws.send_json({"type": 'AUDIO_TOGGLE_SELF_MUTE', "context": 'default', "syncRemote": True})
        r = await self.api.get_media()
        self.me.is_muted = r["mute"]
        self.me.is_deafened = r["deaf"]
        self.me.is_live = r["live"]
    
    async def toggle_deafen(self, *args, act=False):
        if act:
            await self.ws.send_json({"type": 'AUDIO_TOGGLE_SELF_DEAF', "context": 'default', "syncRemote": True})
        r = await self.api.get_media()
        self.me.is_muted = r["mute"]
        self.me.is_deafened = r["deaf"]
        self.me.is_live = r["live"]
    
    async def disconnect_vc(self):
        await self.ws.send_json({"type":"VOICE_CHANNEL_SELECT","guildId":None,"channelId":None,"currentVoiceChannelId":self.vc_channel_id,"video":False,"stream":False})

    async def main(self, ws):
        logger.info("Received WS Connection. Starting event processing loop")
        self.ws = ws
        self.api.ws = ws
        async for msg in self.ws:
            if msg.type == WSMsgType.TEXT:
                self._process_event(loads(msg.data))
            elif msg.type == WSMsgType.ERROR:
                print('ws connection closed with exception %s' % self.ws.exception())

    def _process_event(self, data):
        if data["type"] == "$ping":
            return
        if data["type"] == "$deckcord_request" and "increment" in data:
            self.api._set_result(data["increment"], data["result"])
            return
        if data["type"] in self.event_handlers:
            callback = self.event_handlers[data["type"]]
            logger.info(f"Handling event: {data['type']}")
            #print(dumps(data, indent=2)+"\n\n")
        else:
            return
        def _(future: Task):
            self.state_changed_event.set()
            e = future.exception()
            if e:
                print(f"Exception during handling of {data['type']} event.   {e}")
                print_exception(e)
        get_event_loop().create_task(callback(data)).add_done_callback(_)

    async def _loaded(self, data):
        self.loaded = True

    async def _logged_in(self, data):
        self.logged_in = True
        self.me = User(data["user"])
        
        s = await self.api.get_media()
        self.me.is_muted = s["mute"]
        self.me.is_deafened = s["deaf"]
        self.me.is_live = s["live"]
    
    async def _logout(self, data):
        self.logged_in = False

    async def _voice_channel_select(self, data):
        self.vc_channel_id = data["channelId"]
        if not self.vc_channel_id:
            self.vc_channel_name = ""
            self.vc_guild_name = ""
            return 
        self.vc_channel_name = (await self.api.get_channel(self.vc_channel_id))["name"]
        if "guildId" in data and data["guildId"]:
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
                if state["channelId"] == self.vc_channel_id:
                    await user_to_add.populate(self.api)
            if state["channelId"] in self.voicestates:
                self.voicestates[state["channelId"]][state["userId"]] = user_to_add
            else:
                self.voicestates[state["channelId"]] = {state["userId"]: user_to_add}
    
    async def _notification_create(self, data):
        await self.notification_queue.put(data)

    async def _webrtc_mic_forward(self, data):
        self.webrtc = data