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

export class WebRTCEvent extends Event {
  data: any;
  constructor(d: any) {
    super("webrtc");
    this.data = d;
  }
}

export const eventTarget = new _EventTarget();
let lastState: any;

export function useDeckcordState(serverAPI: ServerAPI) {
  const [state, setState] = useState<any | undefined>();
  eventTarget.addEventListener("state", (s) => {
    setState((s as DeckcordEvent).data);
    lastState = state;
  });

  useEffect(() => {
    serverAPI.callPluginMethod("get_state", {}).then((s) => setState(s.result));
  }, []);

  return state;
}

export const isLoaded = () =>
  new Promise((resolve, reject) => {
    if (lastState?.loaded) return resolve(true);
    eventTarget.addEventListener("state", (s) => {
      if ((s as DeckcordEvent).data?.loaded) return resolve(true);
    });
  });

export const isLoggedIn = () =>
  new Promise((resolve, reject) => {
    if (lastState?.logged_in) return resolve(true);
    eventTarget.addEventListener("state", (s) => {
      if ((s as DeckcordEvent).data?.logged_in) return resolve(true);
    });
  });
