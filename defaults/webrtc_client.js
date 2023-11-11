(() => {
    let waitingForMedia = false;
    const getRTCStream = (_) => new Promise((resolve, reject) => {
        if (window.DECKCORD_RTC_STREAM) return resolve(window.DECKCORD_RTC_STREAM);
        
        if (waitingForMedia) return reject();
        waitingForMedia = true;

        const peerConnection = new RTCPeerConnection(null);
        const ws = new WebSocket("ws://127.0.0.1:65124/webrtc");

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

        peerConnection.addEventListener("connectionstatechange", event => {
            if (peerConnection.connectionState === "connected") {
                const stream = peerConnection.getRemoteStreams()[0];
                window.DECKCORD_RTC_STREAM = stream;
                stream.getTracks()[0].stop = () => {
                    ws.send(JSON.stringify({"stop": ""}));
                    peerConnection.close();
                    window.DECKCORD_RTC_STREAM = undefined;
                }
                waitingForMedia = false;
                resolve(stream);
            }
        });
    });

    window.navigator.mediaDevices.getDisplayMedia = getRTCStream;
})();