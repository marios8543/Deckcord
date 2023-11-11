(() => {
    let waitingForMedia = false;
    const getRTCStream = (_) => new Promise((resolve, reject) => {
        if (window.DECKCORD_RTC_STREAM) return resolve(window.DECKCORD_RTC_STREAM);
        
        if (waitingForMedia) return reject();
        waitingForMedia = true;

        const peerConnection = new RTCPeerConnection(null);
        const ws = new WebSocket("ws://127.0.0.1:65124/webrtc");

        window.DECKCORD_PEER_CONNECTION = peerConnection;

        ws.onopen = async (_) => {
            const offer = await peerConnection.createOffer({ offerToReceiveVideo: true, offerToReceiveAudio: true });
            await peerConnection.setLocalDescription(offer);
            ws.send(JSON.stringify({ "offer": offer }));

            peerConnection.addEventListener("icecandidate", event => {
                if (event.candidate) {
                    ws.send(JSON.stringify({ "ice": event.candidate }));
                }
            });
        }
        ws.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            if (data.sdp) {
                const remoteDescription = new RTCSessionDescription(data.sdp);
                console.log(remoteDescription);
                await peerConnection.setRemoteDescription(remoteDescription);
            }
            else if (data.ice) {
                console.log(data.ice);
                await peerConnection.addIceCandidate(data.ice);
            }
        }

        peerConnection.onconnectionstatechange = (ev) => {
            if (peerConnection.connectionState == "failed") {
                waitingForMedia = false;
                reject("rtc peer connection failed");
            }
        }

        peerConnection.onaddstream = (ev) => {
            const stream = ev.stream;
            if (stream.getVideoTracks().length == 0) return;

            window.DECKCORD_RTC_STREAM = stream;
            for (const track of stream.getTracks()) {
                track.stop = () => {
                    ws.send(JSON.stringify({"stop": ""}));
                    peerConnection.close();
                    window.DECKCORD_RTC_STREAM = undefined;
                }
            }
            waitingForMedia = false;
            resolve(stream);
        }
    });

    window.navigator.mediaDevices.getDisplayMedia = getRTCStream;
})();