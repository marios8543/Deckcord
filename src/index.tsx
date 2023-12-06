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
import { useDeckcordState, eventTarget, DeckcordEvent } from "./hooks/useDeckcordState";

import { MuteButton } from "./components/buttons/MuteButton";
import { DeafenButton } from "./components/buttons/DeafenButton";
import { DisconnectButton } from "./components/buttons/DisconnectButton";
import { GoLiveButton } from "./components/buttons/GoLiveButton";
import { PushToTalkButton } from "./components/buttons/PushToTalk";
import { VoiceChatChannel, VoiceChatMembers } from "./components/VoiceChatViews";
import { UploadScreenshot } from "./components/UploadScreenshot";

declare global {
  interface Window {
    DISCORD_TAB: any;
    DECKCORD: {
      setState: any,
      dispatchNotification: any
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
  let lastState: any;
  window.DECKCORD = {
    dispatchNotification: (payload: {title:string, body:string}) => {
      console.log("Dispatching Deckcord notification: ", payload)
      serverApi.toaster.toast(payload);
    },
    setState: (state: any) => {
      eventTarget.dispatchEvent(new DeckcordEvent(state));
      lastState = state;
    }
  }
  serverApi.callPluginMethod("get_state", {}).then((s) => window.DECKCORD.setState(s.result));

  const isLoaded = () => new Promise((resolve, reject) => {
    if (lastState?.loaded) return resolve(true);
    eventTarget.addEventListener("state", (s) => {
      if ((s as DeckcordEvent).data?.loaded) return resolve(true);
    })
  });
  const isLoggedIn = () => new Promise((resolve, reject) => {
    if (lastState?.logged_in) return resolve(true);
    eventTarget.addEventListener("state", (s) => {
      if ((s as DeckcordEvent).data?.logged_in) return resolve(true);
    })
  });

  let settingsChangeUnregister: any;
  const appLifetimeUnregister = SteamClient.GameSessions.RegisterForAppLifetimeNotifications(async () => {
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
    await isLoaded()
    settingsChangeUnregister =
    SteamClient.Settings.RegisterForSettingsChanges(
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
