import {
  DialogButton,
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
  Router,
  Toggle,
  sleep,
  Dropdown,
  DropdownOption,
  Focusable
} from "decky-frontend-lib";
import { VFC, useEffect, useMemo, useState } from "react";
import {
  FaDiscord,
  FaMicrophoneAltSlash,
  FaMicrophoneAlt,
  FaHeadphonesAlt,
  FaSlash,
  FaPlug
} from "react-icons/fa";
import { patchMenu } from "./menuPatch";
import { DiscordTab } from "./DiscordTab";

class _EventTarget extends EventTarget { }
class DeckcordEvent extends Event {
  data: any;
  constructor(d: any) {
    super("state");
    this.data = d;
  }
}
declare global {
  interface Window {
    DISCORD_TAB: any,
    DECKCORD: {
      setState: any,
      appLifetimeUnregister: any,
      settingsChangeUnregister: any,
      pttEnabled: boolean,
      pttUpdated: any
    }
  }
}

function urlContentToDataUri(url: string) {
  return fetch(url)
    .then(response => response.blob())
    .then(blob => new Promise(callback => {
      let reader = new FileReader();
      reader.onload = function () { callback(this.result) };
      reader.readAsDataURL(blob);
    }));
}

const Content: VFC<{ serverAPI: ServerAPI, evtTarget: _EventTarget }> = ({ serverAPI, evtTarget }) => {
  const [state, setState] = useState<any | undefined>();

  const [screenshot, setScreenshot] = useState<any>();
  const [selectedChannel, setChannel] = useState<any>();
  const [uploadButtonDisabled, setUploadButtonDisabled] = useState<boolean>(false);
  const channels = useMemo(
    (): DropdownOption[] => [],
    [],
  );

  evtTarget.addEventListener("state", s => setState((s as DeckcordEvent).data));

  useEffect(() => {
    serverAPI.callPluginMethod("get_state", {}).then(s => setState(s.result));
    serverAPI.callPluginMethod("get_last_channels", {}).then(res => {
      if ("error" in (res.result as {})) return;
      const channelList: {} = res.result;
      for (const channelId in channelList) channels.push({ data: channelId, label: channelList[channelId] });
      setChannel(channels[0].data);
    });
    SteamClient.Screenshots.GetLastScreenshotTaken().then((res: any) => setScreenshot(res));
  }, []);

  function muteButton() {
    if (state?.me?.is_muted) {
      return (
        <DialogButton onClick={() => { serverAPI.callPluginMethod("toggle_mute", {}) }}
          style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px', marginRight: '10px' }}
        ><FaMicrophoneAltSlash /></DialogButton>
      );
    }
    return (
      <DialogButton onClick={() => { serverAPI.callPluginMethod("toggle_mute", {}) }}
        style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px', marginRight: '10px' }}
      ><FaMicrophoneAlt /></DialogButton>
    );
  }

  function deafenButton() {
    if (!state?.me?.is_deafened) {
      return (
        <DialogButton onClick={() => { serverAPI.callPluginMethod("toggle_deafen", {}) }}
          style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px', marginRight: '10px' }}
        ><FaHeadphonesAlt /></DialogButton>
      );
    }
    return (
      <DialogButton onClick={() => { serverAPI.callPluginMethod("toggle_deafen", {}) }}
        style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px', marginRight: '10px' }}
      ><FaHeadphonesAlt /><FaSlash style={{ position: 'absolute', left: '13px' }} /></DialogButton>
    );
  }

  function vcChannel() {
    if (state?.vc == undefined) return;
    return (
      <div style={{ marginTop: '-30px' }}>
        <h3>{state?.vc?.channel_name}</h3>
        <h4 style={{ marginTop: '-20px' }}>{state?.vc?.guild_name}</h4>
      </div>
    )
  }

  function vcMembers() {
    if (state?.vc?.users == undefined) return;
    const members = [];
    for (const user of state?.vc?.users) {
      members.push(
        <li style={{ display: "flex", justifyContent: "left" }}>
          <img src={'https://cdn.discordapp.com/avatars/' + user?.id + '/' + user?.avatar + '.webp'} width={32} height={32} />
          {user?.username}
        </li>
      );
    }
    return <ul style={{ marginTop: '-30px' }}>{members}</ul>;
  }

  function uploadScreenshot() {
    return (
      <div>
        <img width={240} height={160} src={'https://steamloopback.host/' + screenshot?.strUrl}></img>
        <Dropdown
          menuLabel="Last Channels"
          selectedOption={selectedChannel}
          rgOptions={channels}
          onChange={(e) => {
            setChannel(e.data);
            if (window.location.pathname == "/routes/discord") {
              window.DISCORD_TAB.m_browserView.SetVisible(true);
              window.DISCORD_TAB.m_browserView.SetFocus(true);
            }
          }}
          onMenuOpened={() => {
            window.DISCORD_TAB.m_browserView.SetVisible(false);
            window.DISCORD_TAB.m_browserView.SetFocus(false);
          }}
        ></Dropdown>
        <DialogButton style={{ marginTop: '5px' }} disabled={uploadButtonDisabled} onClick={async () => {
          setUploadButtonDisabled(true);
          const data = await urlContentToDataUri(`https://steamloopback.host/${screenshot.strUrl}`);
          await serverAPI.callPluginMethod("post_screenshot", { channel_id: selectedChannel, data: data });
          setUploadButtonDisabled(false);
        }}>Upload</DialogButton>
      </div>
    )
  }

  const [_pttEnabled, setPtt] = useState<boolean>(window.DECKCORD.pttEnabled);
  function pttSwitch() {
    return (
      <span style={{ display: 'flex' }}>PTT: <Toggle value={_pttEnabled} onChange={(checked) => {
        setPtt(checked)
        window.DECKCORD.pttEnabled = !_pttEnabled;
        window.DECKCORD.pttUpdated();
        console.log(checked, _pttEnabled);
      }}></Toggle></span>
    )
  }

  if (state?.loaded && state?.logged_in) {
    return (
      <PanelSection>
        <PanelSectionRow>
          <Focusable style={{ display: "flex", justifyContent: "center" }}>
            {muteButton()}
            {deafenButton()}
            <DialogButton onClick={() => { serverAPI.callPluginMethod("disconnect_vc", {}) }}
              style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px' }}
            ><FaPlug /></DialogButton>
          </Focusable>
        </PanelSectionRow>
        <PanelSectionRow>
          <div style={{ marginTop: '-8px', display: "flex", justifyContent: "center" }}>
            {pttSwitch()}
          </div>
        </PanelSectionRow>
        <hr></hr>
        <PanelSectionRow>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ marginTop: '-10px' }}>
              <img src={'https://cdn.discordapp.com/avatars/' + state?.me?.id + '/' + state?.me?.avatar + '.webp'} width={32} height={32} />
              {state?.me?.username}
            </span>
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          {vcChannel()}
          {vcMembers()}
        </PanelSectionRow>
        <hr></hr>
        <PanelSectionRow>
          {uploadScreenshot()}
        </PanelSectionRow>
      </PanelSection>
    );
  }
  else if (!state?.loaded) {
    return (
      <div style={{ display: "flex", justifyContent: "center" }}>
        <h2>Initializing...</h2>
      </div>
    )
  }
  else {
    return (
      <div style={{ display: "flex", justifyContent: "center", flexDirection: 'column', paddingLeft: '15px' }}>
        <h2>Not logged in!</h2>
        <h3>Open <b><FaDiscord />Discord</b> from the Steam Menu and login.</h3>
        <h4>If you did not logout, just wait for a few seconds.</h4>
      </div>
    )
  }
};

export default definePlugin((serverApi: ServerAPI) => {
  const evtTarget = new _EventTarget();
  const PTT_BUTTON = 33;
  let unregisterPtt = () => { };
  let lastDisplayIsExternal = false;

  const setPlaying = () => {
    const app = Router.MainRunningApp;
    serverApi.callPluginMethod("set_rpc", { game: app !== undefined ? app?.display_name : null });
  }

  (async () => {
    while (true) {
      const state: any = (await serverApi.callPluginMethod("get_state", {})).result;
      if (state?.loaded) {
        window.DECKCORD.settingsChangeUnregister = SteamClient.Settings.RegisterForSettingsChanges(async (settings: any) => {
          if (settings.bDisplayIsExternal != lastDisplayIsExternal) {
            lastDisplayIsExternal = settings.bDisplayIsExternal;
            const bounds: any = (await serverApi.callPluginMethod("get_screen_bounds", {})).result;
            window.DISCORD_TAB.HEIGHT = bounds.height;
            window.DISCORD_TAB.WIDTH = bounds.width;
            window.DISCORD_TAB.m_browserView.SetBounds(0, 0, bounds.width, bounds.height);
          }
        });
        break;
      }
      await sleep(100);
    }
    while (true) {
      const state: any = (await serverApi.callPluginMethod("get_state", {})).result;
      if (state?.logged_in) {
        setPlaying();
        break;
      }
      await sleep(100);
    }
  })();

  window.DECKCORD = {
    setState: (s: any) => evtTarget.dispatchEvent(new DeckcordEvent(s)),
    appLifetimeUnregister: SteamClient.GameSessions.RegisterForAppLifetimeNotifications(async () => {
      await sleep(500);
      setPlaying();
    }).unregister,
    settingsChangeUnregister: null,
    pttEnabled: false,
    pttUpdated: () => {
      if (window.DECKCORD.pttEnabled) {
        serverApi.callPluginMethod("enable_ptt", { enabled: true });
        serverApi.toaster.toast({
          title: "Push-To-Talk",
          body: "Hold down the R5 button to talk"
        });
        unregisterPtt = SteamClient.Input.RegisterForControllerInputMessages((events: any) => {
          for (const event of events) {
            if (event.nA == PTT_BUTTON) {
              serverApi.callPluginMethod("set_ptt", { value: event.bS })
            }
          }
        }).unregister;
      }
      else {
        unregisterPtt();
        serverApi.callPluginMethod("enable_ptt", { enabled: false });
      }
    }
  };

  const unpatchMenu = patchMenu();
  serverApi.routerHook.addRoute("/discord", () => {
    return <DiscordTab serverAPI={serverApi}></DiscordTab>
  });

  return {
    title: <div className={staticClasses.Title}>Deckcord</div>,
    content: <Content serverAPI={serverApi} evtTarget={evtTarget} />,
    icon: <FaDiscord />,
    onDismount() {
      unpatchMenu();
      try {
        window.DECKCORD.appLifetimeUnregister();
        window.DECKCORD.settingsChangeUnregister();
      }
      catch (error) { }
    },
    alwaysRender: true
  };
});