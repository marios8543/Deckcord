import {
  DialogButton,
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
  Router,
  Toggle
} from "decky-frontend-lib";
import { VFC, useState } from "react";
import {
  FaDiscord,
  FaMicrophoneAltSlash,
  FaMicrophoneAlt,
  FaHeadphonesAlt,
  FaSlash,
  FaPlug
} from "react-icons/fa";

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
      setState: any
    }
  }
}

const Content: VFC<{ serverAPI: ServerAPI, evtTarget: _EventTarget }> = ({ serverAPI, evtTarget }) => {
  const [state, setState] = useState<any | undefined>();
  var unregisterPtt: any;
  const PTT_BUTTON = 33;

  serverAPI.callPluginMethod("get_state", {}).then(s => setState(s.result));
  evtTarget.addEventListener("state", s => setState((s as DeckcordEvent).data));

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
      <div style={{marginTop: '-30px'}}>
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
    return <ul style={{marginTop: '-30px'}}>{members}</ul>;
  }

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
      <PanelSectionRow>
        <div style={{ display: "flex", justifyContent: "center" }}>
          <DialogButton onClick={() => {
            serverAPI.callPluginMethod("open_discord", {});
            Router.CloseSideMenus();
          }
          }>Open</DialogButton>
          <DialogButton onClick={() => {
            serverAPI.callPluginMethod("close_discord", {});
          }
          }>Close</DialogButton>
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
    </PanelSection>
  );
};

export default definePlugin((serverApi: ServerAPI) => {
  const evtTarget = new _EventTarget();
  window.DECKCORD = {
    setState: (s: any) => evtTarget.dispatchEvent(new DeckcordEvent(s))
  };
  return {
    title: <div className={staticClasses.Title}>Deckcord</div>,
    content: <Content serverAPI={serverApi} evtTarget={evtTarget} />,
    icon: <FaDiscord />,
    onDismount() {
    },
  };
});
//{pttSwitch()}
//        