from websockets import client
from json import dumps, loads
from uuid import uuid4
from asyncio import get_event_loop, sleep
from sys import maxsize
from aiohttp import ClientSession
from traceback import print_exc

class User:
    def __init__(self, data) -> None:
        self.id = data["id"]
        self.name = data["username"]
        self.discriminator = data["discriminator"]
        self.avatar = data["avatar"]

        self.is_muted = False
        self.is_deafened = False

    @classmethod
    def from_vc(self, data):
        usr = User({"id": data["userId"], "username": "", "discriminator": None, "avatar": ""})
        usr.is_muted = data["mute"]
        usr.is_deafened = data["deaf"]
        return usr
    
    async def populate(self, client):
        if self.name:
            return
        r = await client.get_user(self.id)
        self.name = r.name
        self.discriminator = r.discriminator
        self.avatar = r.avatar

    def to_dict(self):
        return {
            "id": self.id,
            "username": str(self),
            "avatar": self.avatar,
            "is_muted": self.is_muted,
            "is_deafened": self.is_deafened
        }
    
    def __str__(self) -> str:
        return f"{self.name}#{self.discriminator}"

class ApiClient:
    def __init__(self, token) -> None:
        self.token = token
        self.client = ClientSession(headers={"authorization": self.token})
    
    async def get_user(self, id):
        async with self.client.get(f"https://discord.com/api/v9/users/{id}") as res:
            if res.status == 200:
                return User(await res.json())
            raise Exception(await res.text())

    async def get_channel(self, id):
        async with self.client.get(f"https://discord.com/api/v9/channels/{id}") as res:
            if res.status == 200:
                return await res.json()
            raise Exception(await res.text())
    
    async def get_guild(self, id):
        async with self.client.get(f"https://discord.com/api/v9/guilds/{id}") as res:
            if res.status == 200:
                return await res.json()
            raise Exception(await res.text())

class RpcClient:
    def __init__(self, token) -> None:
        self.token = token
        self.ws : client.WebSocketClientProtocol = None
        self.api : ApiClient = None
        self.loop = get_event_loop()
        self.event_handlers = {
            "VOICE_STATE_UPDATES": self._voice_state_update,
            "VOICE_CHANNEL_SELECT": self._voice_channel_select,
            "OVERLAY_INITIALIZE": self._overlay_initialize,
            "AUDIO_TOGGLE_SELF_MUTE": self.toggle_mute,
            "AUDIO_TOGGLE_SELF_DEAF": self.toggle_deafen
        }

        self.me = User({"id": "", "username": "", "discriminator": None, "avatar": ""})
        self.voicestates = {}

        self.vc_channel_id = ""
        self.vc_channel_name = ""
        self.vc_guild_name = ""

        self.loop.create_task(self.print_status())
    
    async def _process_event(self, data):
        callback = None
        try:
            callback = self.event_handlers[data["type"]]
        except KeyError:
            return
        try:
            await callback(data)
        except Exception:
            print_exc()
    
    async def print_status(self):
        while True:
            print(dumps(self.build_state_dict(), indent=2)+"\n\n")
            await sleep(1)

    async def _main(self):
        self.ws = await client.connect("ws://127.0.0.1:6463/?v=1", origin="https://discord.com", max_size=maxsize)
        await self.ws.ensure_open()
        await self.ws.send(dumps({
            "cmd":"SUBSCRIBE", "args":{"token":self.token}, "evt":"OVERLAY", "nonce": str(uuid4())
        }))
        await self.ws.send(dumps({
            "cmd":"OVERLAY","args":{"type":"CONNECT","pid":-1,"token":self.token}, "nonce": str(uuid4())
        }))
        while True:
            data = loads(await self.ws.recv())
            if data["cmd"] == "DISPATCH" and data["evt"] == "OVERLAY" and data["data"]["type"] == "DISPATCH":
                payloads = data["data"]["payloads"]
                for payload in payloads:
                    await self._process_event(payload)

    async def _overlay_initialize(self, data):
        self.api = ApiClient(data["token"])
        self.me = User(data["user"])
        self.me.is_muted = data["mediaEngineState"]["settingsByContext"]["default"]["mute"]
        self.me.is_deafened = data["mediaEngineState"]["settingsByContext"]["default"]["deaf"]

        for guild in data["voiceStates"].values():
            for talking_user in guild.values():
                if talking_user["channelId"] in self.voicestates:
                    self.voicestates[talking_user["channelId"]][talking_user["userId"]] = User.from_vc(talking_user)
                else:
                    self.voicestates[talking_user["channelId"]] = {talking_user["userId"]: User.from_vc(talking_user)}
        
        self.vc_channel_id = data["selectedVoiceChannelId"]
        if self.vc_channel_id:
            ch = await self.api.get_channel(self.vc_channel_id)
            self.vc_channel_name = ch["name"]
            self.vc_guild_name = (await self.api.get_guild(ch["guild_id"]))["name"]
            for user in self.voicestates[self.vc_channel_id].values():
                await user.populate(self.api)

    async def _voice_channel_select(self, data):
        if not self.api:
            return
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
            await self.ws.send(dumps({
                "cmd":"OVERLAY","args":{"type":"DISPATCH","pid":-1,"token": self.token,"payloads":[{"type": "AUDIO_TOGGLE_SELF_MUTE","context": "default","syncRemote": True}]},"nonce": str(uuid4())
            }))
        self.me.is_muted = not self.me.is_muted
    
    async def toggle_deafen(self, *args, act=False):
        if act:
            await self.ws.send(dumps({
                "cmd":"OVERLAY","args":{"type":"DISPATCH","pid":-1,"token": self.token,"payloads":[{"type": "AUDIO_TOGGLE_SELF_DEAFEN","context": "default","syncRemote": True}]},"nonce": str(uuid4())
            }))
        self.me.is_deafened = not self.me.is_deafened
    
    async def disconnect_vc(self):
        await self.ws.send(dumps({
            "cmd":"OVERLAY","args":{"type":"DISPATCH","pid":-1,"token":self.token,"payloads":[{"type":"VOICE_CHANNEL_SELECT","guildId":None,"channelId":None,"currentVoiceChannelId":self.vc_channel_id,"video":False,"stream":False}]},"nonce": str(uuid4())
        }))
    
    def run(self):
        self.loop.run_until_complete(self._main())