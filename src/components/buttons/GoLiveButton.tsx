import { DialogButton, ServerAPI } from "decky-frontend-lib";
import { useDeckcordState } from "../../hooks/useDeckcordState";
import { FaVideo } from "react-icons/fa";

export function GoLiveButton(props: { serverAPI: ServerAPI; }) {
  const state = useDeckcordState(props.serverAPI);
  if (state?.vc == null || state?.vc == undefined) return (<div></div>);
  if (Object.keys(state?.vc).length > 0) {
    if (!state?.me?.is_live) {
      return (
        <DialogButton
          onClick={() => {
            props.serverAPI.callPluginMethod("go_live", {});
          }}
          style={{
            height: "40px",
            width: "40px",
            minWidth: 0,
            padding: "10px 12px",
          }}
        >
          <FaVideo />
        </DialogButton>
      );
    } else {
      return (
        <DialogButton
          onClick={() => {
            props.serverAPI.callPluginMethod("stop_go_live", {});
          }}
          style={{
            height: "40px",
            width: "40px",
            minWidth: 0,
            padding: "10px 12px",
            backgroundColor: "red",
          }}
        >
          <FaVideo />
        </DialogButton>
      );
    }
  } else return <div></div>;
}
