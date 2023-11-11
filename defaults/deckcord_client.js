Object.hasOwn = (obj, prop) => obj.hasOwnProperty(prop);

(function () {
    function dataURLtoFile(dataurl, filename) {
        var arr = dataurl.split(','),
            mime = arr[0].match(/:(.*?);/)[1],
            bstr = atob(arr[arr.length - 1]),
            n = bstr.length,
            u8arr = new Uint8Array(n);
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new File([u8arr], filename, { type: mime });
    }

    function patchTypingField() {
        const t = setInterval(() => {
            try {
                document.getElementsByClassName("editor__66464")[0].onclick = (e) => fetch("http://127.0.0.1:65123/openkb", { mode: "no-cors" });
                clearInterval(t);
            } catch (err) { }
        }, 100)
    }

    async function getAppId(name) {
        const res = await Vencord.Webpack.Common.RestAPI.get({ url: "/applications/detectable" });
        if (res.ok) {
            const item = res.body.filter(e => e.name == name);
            if (item.length > 0) return item[0].id;
        }
        return "0";
    }

    let CloudUpload, MediaEngineStore;
    const tt = setInterval(() => {
        CloudUpload = Vencord.Webpack.findByProps("CloudUpload").CloudUpload;
        if (CloudUpload !== undefined && CloudUpload !== null) clearInterval(tt);
    });
    const ttt = setInterval(() => {
        MediaEngineStore = Vencord.Webpack.findStore("MediaEngineStore");
        if (MediaEngineStore !== undefined && MediaEngineStore !== null) clearInterval(ttt);
    })
    function sendAttachmentToChannel(channelId, attachment_b64, filename) {
        return new Promise((resolve, reject) => {
            const file = dataURLtoFile(`data:text/plain;base64,${attachment_b64}`, filename);
            const upload = new CloudUpload({
                file: file,
                isClip: false,
                isThumbnail: false,
                platform: 1,
            }, channelId, false, 0);
            upload.on("complete", () => {
                Vencord.Webpack.Common.RestAPI.post({
                    url: `/channels/${channelId}/messages`,
                    body: {
                        channel_id: channelId,
                        content: "",
                        nonce: Vencord.Webpack.Common.SnowflakeUtils.fromTimestamp(Date.now()),
                        sticker_ids: [],
                        type: 0,
                        attachments: [{
                            id: "0",
                            filename: upload.filename,
                            uploaded_filename: upload.uploadedFilename
                        }]
                    }
                });
                resolve(true);
            });
            upload.on("error", () => resolve(false))
            upload.upload();
        })
    }

    var ws;
    function connect() {
        ws = new WebSocket('ws://127.0.0.1:65123/socket');

        ws.onmessage = async function (e) {
            const data = JSON.parse(e.data);
            if (data.type.startsWith("$")) {
                let result;
                try {
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
                                mute: MediaEngineStore.isSelfMute(),
                                deaf: MediaEngineStore.isSelfDeaf()
                            }
                            break;
                        case "$get_last_channels":
                            result = {}
                            const ChannelStore = Vencord.Webpack.Common.ChannelStore;
                            const GuildStore = Vencord.Webpack.Common.GuildStore;
                            const channelIds = Object.values(JSON.parse(Vencord.Util.localStorage.SelectedChannelStore).mostRecentSelectedTextChannelIds);
                            for (const chId of channelIds) {
                                const ch = ChannelStore.getChannel(chId);
                                const guild = GuildStore.getGuild(ch.guild_id);
                                result[chId] = `${ch.name} (${guild.name})`;
                            }
                            break;
                        case "$get_screen_bounds":
                            result = { width: screen.width, height: screen.height }
                            break;
                        case "$ptt":
                            try {
                                MediaEngineStore.getMediaEngine().connections.values().next().value.setForceAudioInput(data.value);
                            } catch (error) { }
                            return;
                        case "$setptt":
                            Vencord.Webpack.Common.FluxDispatcher.dispatch({
                                "type": "AUDIO_SET_MODE",
                                "context": "default",
                                "mode": data.enabled ? "PUSH_TO_TALK" : "VOICE_ACTIVITY",
                                "options": MediaEngineStore.getSettings().modeOptions
                            });
                            return;
                        case "$rpc":
                            Vencord.Webpack.Common.FluxDispatcher.dispatch({
                                type: "LOCAL_ACTIVITY_UPDATE",
                                activity: data.game ? {
                                    application_id: await getAppId(data.game),
                                    name: data.game,
                                    type: 0,
                                    flags: 1,
                                    timestamps: { start: Date.now() }
                                } : {},
                                socketId: "CustomRPC",
                            });
                            return;
                        case "$screenshot":
                            result = await sendAttachmentToChannel(data.channel_id, data.attachment_b64, "screenshot.jpg");
                            break;
                    }
                } catch (error) {
                    result = { error: error }
                    if (data.increment == undefined) return;
                }
                const payload = {
                    type: "$deckcord_request",
                    increment: data.increment,
                    result: result || {}
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

        ws.onopen = function (ev) {
            Vencord.Webpack.waitFor("useState", () => {
                ws.send(JSON.stringify({
                    type: "LOADED",
                    result: true
                }));
            });
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
                const shouldPass = [
                    "LOADED",
                    "CONNECTION_OPEN",
                    "LOGOUT",
                    "CONNECTION_CLOSED",
                    "VOICE_STATE_UPDATES",
                    "VOICE_CHANNEL_SELECT",
                    "AUDIO_TOGGLE_SELF_MUTE",
                    "AUDIO_TOGGLE_SELF_DEAF",
                    "RPC_NOTIFICATION_CREATE"
                ].includes(e.type);
                if (shouldPass) ws.send(JSON.stringify(e));
                if (e.type == "CONNECTION_OPEN") {
                    window.WebSocket = window.OriginalWebsocket;
                }
            });
            MediaEngineStore.getMediaEngine().enabled = true;
            Vencord.Webpack.Common.FluxDispatcher.dispatch({ type: "MEDIA_ENGINE_SET_AUDIO_ENABLED", enabled: true, unmute: true })
            if (window.location.pathname == "/login") {
                for (const el of document.getElementsByTagName('input')) {
                    el.onclick = (ev) => fetch("http://127.0.0.1:65123/openkb", { mode: "no-cors" });
                }
            }
            clearInterval(t);
        }
        catch (err) { }
    }, 100);
})();