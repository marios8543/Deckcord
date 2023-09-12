import { ServerAPI } from "decky-frontend-lib"
import { VFC, useLayoutEffect } from "react"

export const DiscordTab: VFC<{serverAPI: ServerAPI}> = ({ serverAPI }) => {
    useLayoutEffect(() => {
        serverAPI.callPluginMethod("open_discord", {});
        return () => {
            serverAPI.callPluginMethod("close_discord", {});
        }
    })
    return <div></div>
}