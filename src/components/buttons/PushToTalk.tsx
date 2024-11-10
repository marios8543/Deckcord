import { call, toaster } from "@decky/api";
import { Toggle } from "@decky/ui";
import { useState } from "react";

const PTT_BUTTON = 33;

export function PushToTalkButton() {
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
            call("enable_ptt", true);
            toaster.toast({
              title: "Push-To-Talk",
              body: "Hold down the R5 button to talk",
            });
            unregisterPtt =
              SteamClient.Input.RegisterForControllerInputMessages(
                (events: any) => {
                  for (const event of events)
                    if (event.nA == PTT_BUTTON)
                      call("set_ptt", event.bS);
                }
              ).unregister;
          } else {
            unregisterPtt();
            call("enable_ptt", false);
          }
        }}
      ></Toggle>
    </span>
  );
}
