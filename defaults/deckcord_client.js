(function () {
    function buildReadyObject() {
        return {
            user: Vencord.Webpack.Common.UserStore.getCurrentUser(),
            mute: Vencord.Webpack.findStore("MediaEngineStore").isSelfMute(),
            deaf: Vencord.Webpack.findStore("MediaEngineStore").isSelfDeaf()
        }
    }
    function patchTypingField() {
        const t = setInterval(() => {
            try {
                document.getElementsByClassName("editor-H2NA06")[0].onclick = (e) => fetch("http://127.0.0.1:65123/openkb", {mode: "no-cors"});
                clearInterval(t);
            } catch (err) {}
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

        ws.onopen = function(ev) {
            const t = setInterval(() => {
                try {
                    ws.send(JSON.stringify({
                        type: "READY",
                        result: buildReadyObject()
                    }));
                    clearInterval(t);
                } catch (error) {}
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
                ws.send(JSON.stringify(e));
            });
            Vencord.Webpack.findStore("MediaEngineStore").getMediaEngine().enabled = true;
            clearInterval(t);
        }
        catch (err) { }
    }, 100);
    /* const tt = setInterval(() => {
        try {
            document.querySelector("#app-mount > div.appAsidePanelWrapper-ev4hlp > div.notAppAsidePanel-3yzkgB > div.app-3xd6d0 > div > div.layers-OrUESM.layers-1YQhyW > div > div > div > div > main > section > div > div.toolbar-3_r2xA > a").onclick = e => {
                e.preventDefault();
                fetch("http://127.0.0.1:65123/close", {mode: "no-cors"});
            }
            clearInterval(tt);
        }
        catch (err) {}
    }, 100); */
})();