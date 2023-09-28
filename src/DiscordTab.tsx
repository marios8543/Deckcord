import { Router, ServerAPI } from "decky-frontend-lib"
import { VFC, useLayoutEffect } from "react"

export const DiscordTab: VFC<{serverAPI: ServerAPI}> = ({ serverAPI }) => {
    useLayoutEffect(() => {
        serverAPI.callPluginMethod("get_state", {}).then(res => {
            const state = (res.result as any);
            if (state?.loaded) {
                window.DISCORD_TAB.m_browserView.SetVisible(true);
                window.DISCORD_TAB.m_browserView.SetFocus(true);
            }
            else {
                serverAPI.toaster.toast({
                    title: "Deckcord",
                    body: "Deckcord has not loaded yet!"
                });
                Router.Navigate("/library/home");
            }
        })
        return () => {
            window.DISCORD_TAB.m_browserView.SetVisible(false);
            window.DISCORD_TAB.m_browserView.SetFocus(false);
        }
    })
    return <div></div>
}