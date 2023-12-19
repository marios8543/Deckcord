import { Toggle } from "decky-frontend-lib";
import { useState } from "react";

const PTT_BUTTON = 33;

export function PushToTalkButton(props: { serverAPI: any }) {
  const [pttEnabled, setPtt] = useState<boolean>(false);
  let unregisterPtt: any;
  return (
    <span style={{ display: "flex" }}>
      PTT:{" "}
      <Toggle
        value={pttEnabled}
        onChange={(checked) => {
          setPtt(checked);
          if (!pttEnabled) {
            props.serverAPI.callPluginMethod("enable_ptt", { enabled: true });
            props.serverAPI.toaster.toast({
              title: "Push-To-Talk",
              body: "Hold down the R5 button to talk",
            });
            unregisterPtt =
              SteamClient.Input.RegisterForControllerInputMessages(
                (events: any) => {
                  for (const event of events)
                    if (event.nA == PTT_BUTTON)
                      props.serverAPI.callPluginMethod("set_ptt", {
                        value: event.bS,
                      });
                }
              ).unregister;
          } else {
            unregisterPtt();
            props.serverAPI.callPluginMethod("enable_ptt", { enabled: false });
          }
        }}
      ></Toggle>
    </span>
  );
}
