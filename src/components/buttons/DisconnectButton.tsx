import { call } from "@decky/api";
import { DialogButton } from "@decky/ui";
import { FaPlug } from "react-icons/fa";

export function DisconnectButton() {
  return (
    <DialogButton
      onClick={() => {
        call("disconnect_vc");
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
