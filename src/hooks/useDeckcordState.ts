import { ServerAPI } from "decky-frontend-lib";
import { useEffect, useState } from "react";

class _EventTarget extends EventTarget {}

export class DeckcordEvent extends Event {
  data: any;
  constructor(d: any) {
    super("state");
    this.data = d;
  }
}

export const eventTarget = new _EventTarget();

export function useDeckcordState(serverAPI: ServerAPI) {
  const [state, setState] = useState<any | undefined>();
  eventTarget.addEventListener("state", (s) =>
    setState((s as DeckcordEvent).data)
  );

  useEffect(() => {
    serverAPI.callPluginMethod("get_state", {}).then((s) => setState(s.result));
  }, []);

  return state;
}

