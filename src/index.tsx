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
  DropdownOption
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
    DECKCORD: {
      setState: any,
      appLifetimeUnregister: any,
      screenshotNotifUnregister: any
    }
  }
}

function urlContentToDataUri(url: string){
  return  fetch(url)
          .then( response => response.blob() )
          .then( blob => new Promise( callback =>{
              let reader = new FileReader() ;
              reader.onload = function(){ callback(this.result) } ;
              reader.readAsDataURL(blob) ;
          }) ) ;
}

const Content: VFC<{ serverAPI: ServerAPI, evtTarget: _EventTarget }> = ({ serverAPI, evtTarget }) => {
  const [state, setState] = useState<any | undefined>();
  var unregisterPtt: any;
  const PTT_BUTTON = 33;

  const [screenshot, setScreenshot] = useState<any>();
  const [selectedChannel, setChannel] = useState<any>();
  const [uploadButtonDisabled, setUploadButtonDisabled] = useState<boolean>(false);
  const channels = useMemo(
    (): DropdownOption[] => [],
    [],
  );

  evtTarget.addEventListener("state", s => setState((s as DeckcordEvent).data));
  SteamClient.Screenshots.GetLastScreenshotTaken().then((res: any) => setScreenshot(res));
  SteamClient.GameSessions.RegisterForScreenshotNotification(async () => {
    await sleep(500);
    setScreenshot(await SteamClient.Screenshots.GetLastScreenshotTaken());
  }).unregister

  useEffect(() => {
    serverAPI.callPluginMethod("get_state", {}).then(s => setState(s.result));
    serverAPI.callPluginMethod("get_last_channels", {}).then(res => {
      const channelList: {} = res.result;
      for (const channelId in channelList) channels.push({ data: channelId, label: channelList[channelId] });
      setChannel(channels[0].data);
    });
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
          onChange={(e) => setChannel(e.data)}
        ></Dropdown>
        <DialogButton style={{marginTop: '5px'}} disabled={uploadButtonDisabled} onClick={async () => {
          setUploadButtonDisabled(true);
          const data = await urlContentToDataUri(`https://steamloopback.host/${screenshot.strUrl}`);
          await serverAPI.callPluginMethod("post_screenshot", {channel_id: selectedChannel, data: data});
          setUploadButtonDisabled(false);
        }}>Upload</DialogButton>
      </div>
    )
  }

  //Not implemented because it crashes react. Probably mis-implementing the toggle somehow, otherwise PTT support is there 100%
  function pttSwitch() {
    const [pttEnabled, setPtt] = useState<boolean>();
    setPtt(false);
    <span style={{ display: 'flex' }}>PTT: <Toggle value={!pttEnabled} onChange={(checked) => {
      setPtt(!pttEnabled)
      if (pttEnabled) {
        unregisterPtt = SteamClient.Input.RegisterForControllerInputMessages((events: any) => {
          for (const event of events) {
            if (event.nA == PTT_BUTTON) {
              serverAPI.callPluginMethod("set_ptt", { value: event.bS })
            }
          }
        }).unregister;
      }
      else unregisterPtt();
    }}></Toggle></span>
  }

  return (
    <PanelSection>
      <PanelSectionRow>
        <div style={{ display: "flex", justifyContent: "center" }}>
          {muteButton()}
          {deafenButton()}
          <DialogButton onClick={() => { serverAPI.callPluginMethod("disconnect_vc", {}) }}
            style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px' }}
          ><FaPlug /></DialogButton>
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
};

export default definePlugin((serverApi: ServerAPI) => {
  const evtTarget = new _EventTarget();

  window.DECKCORD = {
    setState: (s: any) => evtTarget.dispatchEvent(new DeckcordEvent(s)),
    appLifetimeUnregister: SteamClient.GameSessions.RegisterForAppLifetimeNotifications(async () => {
      await sleep(500);
      const app = Router.MainRunningApp;
      console.log("Setting RPC", app);
      serverApi.callPluginMethod("set_rpc", { game: app !== undefined ? app?.display_name : null });
    }).unregister,
    screenshotNotifUnregister: null
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
        window.DECKCORD.screenshotNotifUnregister();
      }
      catch (error) {}
    },
    alwaysRender: true
  };
});