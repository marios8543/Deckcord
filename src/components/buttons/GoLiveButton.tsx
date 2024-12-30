import { DialogButton } from "@decky/ui";
import { useDeckcordState } from "../../hooks/useDeckcordState";
import { FaVideo } from "react-icons/fa";
import { call } from "@decky/api";

export function GoLiveButton() {
  const state = useDeckcordState();

  if (state?.vc == null || state?.vc == undefined)
    return (<div></div>);

  if (Object.keys(state?.vc).length > 0) {
    if (!state?.me?.is_live) {
      return (
        <DialogButton
          onClick={() => {
            call("go_live");
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
            call("stop_go_live");
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
