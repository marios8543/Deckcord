function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

(function () {
    async function buildReadyObject() {
        while (true) {
            const user = Vencord.Webpack.Common.UserStore.getCurrentUser();
            if (user == undefined) {
                await sleep(100);
                continue
            }
            return {
                user: user,
                mute: Vencord.Webpack.findStore("MediaEngineStore").isSelfMute(),
                deaf: Vencord.Webpack.findStore("MediaEngineStore").isSelfDeaf()
            }
        }
    }
    function patchTypingField() {
        const t = setInterval(() => {
            try {
                document.getElementsByClassName("editor-H2NA06")[0].onclick = (e) => fetch("http://127.0.0.1:65123/openkb", { mode: "no-cors" });
                clearInterval(t);
            } catch (err) { }
        }, 100)
    }
    var ws;
    function connect() {
        ws = new WebSocket('ws://127.0.0.1:65123/socket');

        ws.onmessage = function (e) {
            const data = JSON.parse(e.data);
            if (data.type.startsWith("$")) {
                let result;
                switch (data.type) {
                    case "$getuser":
                        result = Vencord.Webpack.Common.UserStore.getUser(data.id);
                        break;
                    case "$getchannel":
                        result = Vencord.Webpack.Common.ChannelStore.getChannel(data.id);
                        break;
                    case "$getguild":
                        result = Vencord.Webpack.Common.GuildStore.getGuild(data.id);
                        break;
                    case "$getmedia":
                        result = {
                            mute: Vencord.Webpack.findStore("MediaEngineStore").isSelfMute(),
                            deaf: Vencord.Webpack.findStore("MediaEngineStore").isSelfDeaf()
                        }
                        break;
                    case "$ptt":
                        try {
                            Vencord.Webpack.findStore("MediaEngineStore").getMediaEngine().connections.values().next().value.setForceAudioInput(data.value);
                        } catch (error) { }
                        return;
                    case "$rpc":
                        Vencord.Webpack.Common.FluxDispatcher.dispatch({
                            type: "LOCAL_ACTIVITY_UPDATE",
                            activity: data.game ? {
                                "application_id": "0",
                                "name": data.game,
                                "type": 0,
                                "flags": 1
                            } : {},
                            socketId: "CustomRPC",
                        });
                }
                const payload = {
                    type: "$deckcord_request",
                    increment: data.increment,
                    result: result
                };
                console.debug(data, payload);
                ws.send(JSON.stringify(payload));
                return;
            }
            Vencord.Webpack.Common.FluxDispatcher.dispatch(data);
        };

        ws.onclose = function (e) {
            setTimeout(function () {
                connect();
            }, 500);
        };

        ws.onopen = async function (ev) {
            while (true) {
                try {
                    const payload = await buildReadyObject();
                    ws.send(JSON.stringify({
                        type: "READY",
                        result: payload
                    }));
                    console.log("SENT READY PAYLOAD", payload)
                    break;
                } catch (error) { }
                await sleep(100);
            }
        }

        ws.onerror = function (err) {
            console.error('Socket encountered error: ', err.message, 'Closing socket');
            ws.close();
        };
    }
    connect();
    const t = setInterval(() => {
        try {
            Vencord.Webpack.Common.FluxDispatcher.addInterceptor(e => {
                if (e.type == "CHANNEL_SELECT") patchTypingField();
                ws.send(JSON.stringify(e));
            });
            Vencord.Webpack.findStore("MediaEngineStore").getMediaEngine().enabled = true;
            Vencord.Webpack.Common.FluxDispatcher.dispatch({ type: "MEDIA_ENGINE_SET_AUDIO_ENABLED", enabled: true, unmute: true })
            console.log("MEDIA ENGINE ENABLED");
            clearInterval(t);
        }
        catch (err) { }
    }, 100);
})();