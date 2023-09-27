import { Router, ServerAPI } from "decky-frontend-lib"
import { VFC, useLayoutEffect } from "react"

export const DiscordTab: VFC<{serverAPI: ServerAPI}> = ({ serverAPI }) => {
    useLayoutEffect(() => {
        serverAPI.callPluginMethod("get_state", {}).then(res => {
            const state = (res.result as any);
            if (state?.ready) serverAPI.callPluginMethod("open_discord", {});
            else {
                serverAPI.toaster.toast({
                    title: "Deckcord",
                    body: "Deckcord has not loaded yet!"
                });
                Router.Navigate("/library/home");
            }
        })
        return () => {
            serverAPI.callPluginMethod("close_discord", {});
        }
    })
    return <div></div>
}