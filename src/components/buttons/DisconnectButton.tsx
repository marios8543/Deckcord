import { DialogButton, ServerAPI } from "decky-frontend-lib";
import { FaPlug } from "react-icons/fa";

export function DisconnectButton(props: { serverAPI: ServerAPI; }) {

  return (
    <DialogButton
      onClick={() => {
        props.serverAPI.callPluginMethod("disconnect_vc", {});
      }}
      style={{
        height: "40px",
        width: "40px",
        minWidth: 0,
        padding: "10px 12px",
        marginRight: "10px",
      }}
    >
      <FaPlug />
    </DialogButton>
  );
}
