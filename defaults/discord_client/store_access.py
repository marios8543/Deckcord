from asyncio import Event

class User:
    def __init__(self, data) -> None:
        self.id = data["id"]
        self.name = data["username"]
        self.discriminator = data["discriminator"]
        self.avatar = data["avatar"]

        self.is_muted = False
        self.is_deafened = False
        self.is_live = False

    @classmethod
    def from_vc(self, data):
        usr = User({"id": data["userId"], "username": "", "discriminator": None, "avatar": ""})
        usr.is_muted = data["mute"]
        usr.is_deafened = data["deaf"]
        return usr

    async def populate(self, api):
        if self.name:
            return

        r = await api.get_user(self.id)
        self.name = r["username"]
        self.discriminator = r["discriminator"]
        self.avatar = r["avatar"]

    def to_dict(self):
        return {
            "id": self.id,
            "username": str(self),
            "avatar": self.avatar,
            "is_muted": self.is_muted,
            "is_deafened": self.is_deafened,
            "is_live": self.is_live
        }

    def __str__(self) -> str:
        return f"{self.name}{'#'+self.discriminator if self.discriminator and self.discriminator != '0' else ''}"


class Response:
    def __init__(self) -> None:
        self.lock = Event()
        self.response = None


class StoreAccess:
    def __init__(self) -> None:
        self.request_increment = 0
        self.requests = {}

    def _set_result(self, increment, result):
        response = self.requests[increment]
        response.result = result
        response.lock.set()

    async def _store_access_request(self, command, id="", **kwargs):
        self.request_increment += 1
        response = Response()
        self.requests[self.request_increment] = response
        await self.ws.send_json({"type": command, "id": id, "increment": self.request_increment, **kwargs})
        await response.lock.wait()
        return response.result

    async def get_user(self, id):
        return await self._store_access_request("$getuser", id)

    async def get_channel(self, id):
        return await self._store_access_request("$getchannel", id)

    async def get_guild(self, id):
        return await self._store_access_request("$getguild", id)

    async def get_media(self):
        return await self._store_access_request("$getmedia")

    async def get_last_channels(self):
        return await self._store_access_request("$get_last_channels")

    async def post_screenshot(self, channel_id, data):
        return await self._store_access_request("$screenshot", channel_id=channel_id, attachment_b64=data)

    async def get_screen_bounds(self):
        return await self._store_access_request("$get_screen_bounds")
