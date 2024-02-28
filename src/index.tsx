import {
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
  Router,
  sleep,
  Focusable,
} from "decky-frontend-lib";
import { VFC } from "react";
import { FaDiscord } from "react-icons/fa";

import { patchMenu } from "./patches/menuPatch";
import { DiscordTab } from "./components/DiscordTab";
import {
  useDeckcordState,
  eventTarget,
  DeckcordEvent,
  isLoaded,
  isLoggedIn,
  WebRTCEvent,
} from "./hooks/useDeckcordState";

import { MuteButton } from "./components/buttons/MuteButton";
import { DeafenButton } from "./components/buttons/DeafenButton";
import { DisconnectButton } from "./components/buttons/DisconnectButton";
import { GoLiveButton } from "./components/buttons/GoLiveButton";
import { PushToTalkButton } from "./components/buttons/PushToTalk";
import {
  VoiceChatChannel,
  VoiceChatMembers,
} from "./components/VoiceChatViews";
import { UploadScreenshot } from "./components/UploadScreenshot";

declare global {
  interface Window {
    DISCORD_TAB: any;
    DECKCORD: {
      dispatchNotification: any;
      MIC_PEER_CONNECTION: any;
      startWatchdog: any;
    };
  }
}

const Content: VFC<{ serverAPI: ServerAPI }> = ({ serverAPI }) => {
  const state = useDeckcordState(serverAPI);
  if (!state?.loaded) {
    return (
      <div style={{ display: "flex", justifyContent: "center" }}>
        <h2>Initializing...</h2>
      </div>
    );
  } else if (!state?.logged_in) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          flexDirection: "column",
          paddingLeft: "15px",
        }}
      >
        <h2>Not logged in!</h2>
        <h3>
          Open{" "}
          <b>
            <FaDiscord />
            Discord
          </b>{" "}
          from the Steam Menu and login.
        </h3>
        <h4>If you did not logout, just wait for a few seconds.</h4>
      </div>
    );
  } else {
    return (
      <PanelSection>
        <PanelSectionRow>
          <Focusable style={{ display: "flex", justifyContent: "center" }}>
            <MuteButton serverAPI={serverAPI}></MuteButton>
            <DeafenButton serverAPI={serverAPI}></DeafenButton>
            <DisconnectButton serverAPI={serverAPI}></DisconnectButton>
            <GoLiveButton serverAPI={serverAPI}></GoLiveButton>
          </Focusable>
        </PanelSectionRow>
        <PanelSectionRow>
          <div
            style={{
              marginTop: "-8px",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <PushToTalkButton serverAPI={serverAPI}></PushToTalkButton>
          </div>
        </PanelSectionRow>
        <hr></hr>
        <PanelSectionRow>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ marginTop: "-10px" }}>
              <img
                src={
                  "https://cdn.discordapp.com/avatars/" +
                  state?.me?.id +
                  "/" +
                  state?.me?.avatar +
                  ".webp"
                }
                width={32}
                height={32}
              />
              {state?.me?.username}
            </span>
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <VoiceChatChannel serverAPI={serverAPI}></VoiceChatChannel>
          <VoiceChatMembers serverAPI={serverAPI}></VoiceChatMembers>
        </PanelSectionRow>
        <hr></hr>
        <PanelSectionRow>
          <UploadScreenshot serverAPI={serverAPI}></UploadScreenshot>
        </PanelSectionRow>
      </PanelSection>
    );
  }
};

export default definePlugin((serverApi: ServerAPI) => {
  window.DECKCORD = {
    dispatchNotification: (payload: { title: string; body: string }) => {
      console.log("Dispatching Deckcord notification: ", payload);
      serverApi.toaster.toast(payload);
    },
    MIC_PEER_CONNECTION: undefined,
    startWatchdog: () => tabWatchdog()
  };

  const setState = (data: any) => {
    if (data.webrtc) eventTarget.dispatchEvent(new WebRTCEvent(data.webrtc));
    else eventTarget.dispatchEvent(new DeckcordEvent(data));
  };
  serverApi.callPluginMethod("get_state", {}).then((s) => setState(s));
  let ws;
  function connect() {
    ws = new WebSocket("ws://127.0.0.1:65123/frontend_socket");
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      setState(data);
    };
    ws.onclose = () => setTimeout(() => connect(), 500);
  }
  connect();

  let peerConnection: RTCPeerConnection;
  eventTarget.addEventListener("webrtc", async (ev: any) => {
    const data = ev.data;
    console.log(data);
    if (data.offer) {
      console.log("Deckcord: Starting RTC connection");
      if (peerConnection) peerConnection.close();
      peerConnection = new RTCPeerConnection();
      window.DECKCORD.MIC_PEER_CONNECTION = peerConnection;
      const localStream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: true,
      });
      localStream.getTracks().forEach((track) => {
        peerConnection.addTrack(track, localStream);
      });
      await peerConnection.setRemoteDescription(
        new RTCSessionDescription(data.offer)
      );
      const answer = await peerConnection.createAnswer();
      await peerConnection.setLocalDescription(answer);
      console.log("Deckcord: Sending RTC Answer");
      await serverApi.callPluginMethod("mic_webrtc_answer", { answer: answer });
    } else if (data.ice) {
      try {
        while (peerConnection.remoteDescription == null) await sleep(10);
        await peerConnection.addIceCandidate(data.ice);
      } catch (e) {
        console.error("Deckcord: Error adding received ice candidate", e);
      }
    }
  });

  const tabWatchdog = async () => {
    while (true) {
      if (window.DISCORD_TAB == undefined) {
        await serverApi.callPluginMethod("initialize_tab", {});
        break;
      }
      await sleep(1000);
    }
  };

  let settingsChangeUnregister: any;
  const appLifetimeUnregister =
    SteamClient.GameSessions.RegisterForAppLifetimeNotifications(async () => {
      await sleep(500);
      setPlaying();
    }).unregister;
  const unpatchMenu = patchMenu();

  const setPlaying = () => {
    const app = Router.MainRunningApp;
    serverApi.callPluginMethod("set_rpc", {
      game: app !== undefined ? app?.display_name : null,
    });
  };

  let lastDisplayIsExternal = false;
  (async () => {
    await isLoaded();

    settingsChangeUnregister = SteamClient.Settings.RegisterForSettingsChanges(
      async (settings: any) => {
        if (settings.bDisplayIsExternal != lastDisplayIsExternal) {
          lastDisplayIsExternal = settings.bDisplayIsExternal;
          const bounds: any = (
            await serverApi.callPluginMethod("get_screen_bounds", {})
          ).result;
          window.DISCORD_TAB.HEIGHT = bounds.height;
          window.DISCORD_TAB.WIDTH = bounds.width;
          window.DISCORD_TAB.m_browserView.SetBounds(
            0,
            0,
            bounds.width,
            bounds.height
          );
        }
      }
    );
    await isLoggedIn();
    setPlaying();
  })();

  serverApi.routerHook.addRoute("/discord", () => {
    return <DiscordTab serverAPI={serverApi}></DiscordTab>;
  });

  return {
    title: <div className={staticClasses.Title}>Deckcord</div>,
    content: <Content serverAPI={serverApi} />,
    icon: <FaDiscord />,
    onDismount() {
      unpatchMenu();
      try {
        appLifetimeUnregister();
        settingsChangeUnregister();
      } catch (error) {}
    },
    alwaysRender: true,
  };
});
