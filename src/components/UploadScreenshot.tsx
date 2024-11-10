import { call } from "@decky/api";
import { DialogButton, Dropdown, DropdownOption } from "@decky/ui";
import { useEffect, useMemo, useState } from "react";

function urlContentToDataUri(url: string) {
  return fetch(url)
    .then((response) => response.blob())
    .then(
      (blob) =>
        new Promise((callback) => {
          let reader = new FileReader();
          reader.onload = function () {
            callback(this.result);
          };
          reader.readAsDataURL(blob);
        })
    );
}

export function UploadScreenshot() {
  const [screenshot, setScreenshot] = useState<any>();
  const [selectedChannel, setChannel] = useState<any>();
  const [uploadButtonDisabled, setUploadButtonDisabled] =
    useState<boolean>(false);
  const channels = useMemo((): DropdownOption[] => [], []);

  useEffect(() => {
    call<[], Record<string, any>>("get_last_channels")
      .then(res => {
        if ("error" in res)
          return;

        const channelList = res;

        for (const channelId in channelList)
          channels.push({ data: channelId, label: channelList[channelId] });

        setChannel(channels[0].data);
      });

    SteamClient.Screenshots.GetLastScreenshotTaken().then((res: any) => setScreenshot(res));
  }, []);

  return (
    <div>
      <img
        width={240}
        height={160}
        src={"https://steamloopback.host/" + screenshot?.strUrl}
      ></img>
      <Dropdown
        menuLabel="Last Channels"
        selectedOption={selectedChannel}
        rgOptions={channels}
        onChange={(e: { data: any; }) => {
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
      <DialogButton
        style={{ marginTop: "5px" }}
        disabled={uploadButtonDisabled}
        onClick={async () => {
          setUploadButtonDisabled(true);
          const data = await urlContentToDataUri(`https://steamloopback.host/${screenshot.strUrl}`);
          await call("post_screenshot", selectedChannel, data);
          setUploadButtonDisabled(false);
        }}
      >
        Upload
      </DialogButton>
    </div>
  );
}
