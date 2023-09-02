import {
  DialogButton,
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
} from "decky-frontend-lib";
import { VFC, useState } from "react";
import {
  FaDiscord,
  FaMicrophoneAltSlash,
  FaMicrophoneAlt,
  FaHeadphonesAlt,
  FaVolumeMute,
  FaPhoneSlash,
} from "react-icons/fa";


const Content: VFC<{ serverAPI: ServerAPI }> = ({ serverAPI }) => {
  const [state, setState] = useState<any | undefined>();

  function sleep(ms: number) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  (async function () {
    while (true) {
      setState((await serverAPI.callPluginMethod("get_state", {})).result);
      await sleep(1000);
    }
  })();

  return (
    <PanelSection>
      <PanelSectionRow>
        <div style={{ display: "flex", justifyContent: "left" }}>
          <img src={'https://cdn.discordapp.com/avatars/' + state?.me?.id + '/' + state?.me?.avatar + '.webp'} />
          {state?.me?.username}
        </div>
      </PanelSectionRow>
      <hr></hr>
      <PanelSectionRow>
        <div style={{ display: "flex", justifyContent: "center" }}>
          if (state?.me?.is_muted) {
            <DialogButton
              style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px', marginRight: '10px' }}
            ><FaMicrophoneAltSlash /></DialogButton>
          }
          else {
            <DialogButton
              style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px', marginRight: '10px' }}
            ><FaMicrophoneAlt /></DialogButton>
          }
          <DialogButton
            style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px', marginRight: '10px' }}
          ><FaHeadphonesAlt /></DialogButton>
          <DialogButton
            style={{ height: '40px', width: '40px', minWidth: 0, padding: '10px 12px' }}
          ><FaPhoneSlash /></DialogButton>
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
};


export default definePlugin((serverApi: ServerAPI) => {
  return {
    title: <div className={staticClasses.Title}>Deckcord</div>,
    content: <Content serverAPI={serverApi} />,
    icon: <FaDiscord />,
    onDismount() {
    },
  };
});
