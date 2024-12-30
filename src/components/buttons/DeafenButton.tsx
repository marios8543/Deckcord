import { DialogButton } from "@decky/ui";
import { useDeckcordState } from "../../hooks/useDeckcordState";
import { FaHeadphonesAlt, FaSlash } from "react-icons/fa";
import { call } from "@decky/api";

export function DeafenButton() {
  const state = useDeckcordState();
  if (!state?.me?.is_deafened) {
    return (
      <DialogButton
        onClick={() => {
          call("toggle_deafen");
        }}
        style={{
          height: "40px",
          width: "40px",
          minWidth: 0,
          padding: "10px 12px",
          marginRight: "10px",
        }}
      >
        <FaHeadphonesAlt />
      </DialogButton>
    );
  }
  return (
    <DialogButton
      onClick={() => {
        call("toggle_deafen");
      }}
      style={{
        height: "40px",
        width: "40px",
        minWidth: 0,
        padding: "10px 12px",
        marginRight: "10px",
      }}
    >
      <FaHeadphonesAlt />
      <FaSlash style={{ position: "absolute", left: "13px" }} />
    </DialogButton>
  );
}
