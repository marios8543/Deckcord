from logging import getLogger, DEBUG
from aiohttp import ClientSession
from base64 import b64encode
from traceback import format_exc
from ssl import create_default_context
from asyncio import create_task

logger = getLogger("proxy_utils")
logger.setLevel(DEBUG)
SSL_CTX = create_default_context(cafile="/home/deck/.local/lib/python3.10/site-packages/certifi/cacert.pem")

async def fetch_discord():
    async with ClientSession() as session:
        res = await session.get("https://discord.com/app", ssl=SSL_CTX)
        if res.ok:
            t = (await res.text()).replace("/assets/", "https://discord.com/assets/") \
        .replace("integrity=", "disabled_integrity=").replace("/^\/billing/.test(location.pathname)", "false")
            return t
        
async def handle_paused_request(msg, tab, session: ClientSession):
    params = msg.get("params")
    request_id = params.get("requestId")
    headers = params.get("request").get("headers")
    method = params.get("request").get("method")
    url = params.get("request").get("url")
    #print("paused request: ", url)
    headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Referer": "https://discord.com/app",
        "Host": "discord.com"
    })
    response = await session.request(method, url, ssl=SSL_CTX, headers=headers)
    response_text = (await response.content.read())
    try:
        response_utf = response_text.decode("utf-8")
        response_utf = response_utf.replace("=\"/assets/\"", "=\"https://discord.com/assets/\"")
        response_text = response_utf.encode("utf-8")
    except Exception as e:
        #print("ignoring ", str(e))
        pass
    res_headers = [{ "name": k, "value": v } for k, v in response.headers.items()]
    b64 = b64encode(response_text).decode()
    await tab.fulfill_request(request_id, response.status, res_headers, b64)


async def process_fetch(tab):
    try:
        async with ClientSession() as session:
            async for msg in tab.listen_for_message():
                # this gets spammed a lot
                #print("Deckscord Page event: ", dumps(msg))
                if msg.get("method", None) != "Page.navigatedWithinDocument":
                    if msg.get("method", None) == "Fetch.requestPaused":
                        create_task(handle_paused_request(msg, tab, session))
                    if msg.get("method", None) == "Page.domContentEventFired":
                        print("Initializing")
                        # https://stackoverflow.com/a/47614491
                        await tab.evaluate("""
                        console.log("Loading...");
                        const origOpen = window.XMLHttpRequest.prototype.open;
                        window.XMLHttpRequest.prototype.open = function(...args) {
                            console.log("running override xhr");
                            if (args[1].startsWith("https://discord.com/api")) {
                                args[1] = args[1].replace("https://discord.com", "http://127.0.0.1:65123");
                                console.log("XHR PATCH", args[1]);
                            }
                            return origOpen.call(this, ...args);
                        };

                        document.documentElement.innerHTML = `""" + (await fetch_discord()) + """`;
                        Array.from(document.querySelectorAll("script")).forEach( oldScriptEl => {
                            const newScriptEl = document.createElement("script");
                            
                            Array.from(oldScriptEl.attributes).forEach( attr => {
                                newScriptEl.setAttribute(attr.name, attr.value) 
                            });
                            
                            const scriptText = document.createTextNode(oldScriptEl.innerHTML);
                            newScriptEl.appendChild(scriptText);
                            
                            oldScriptEl.parentNode.replaceChild(newScriptEl, oldScriptEl);
                            console.log('loading script ' + scriptText);
                        });
                        """)
                    if msg.get("method", None) == "Inspector.detached":
                        print("CEF has requested that we detach.")
                        await tab.close_websocket()
                        break
        print("Deckscord CEF has disconnected...")
    except Exception as e:
        print("Exception while reading page events " + format_exc())
        await tab.close_websocket()
        pass