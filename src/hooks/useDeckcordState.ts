import { call } from "@decky/api";
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

export function useDeckcordState() {
  const [state, setState] = useState<any | undefined>();
  eventTarget.addEventListener("state", (s) => {
    setState((s as DeckcordEvent).data);
    lastState = state;
  });

  useEffect(() => {
    call("get_state").then((s) => setState(s));
  }, []);

  return state;
}

export const isLoaded = () =>
  new Promise((resolve) => {
    if (lastState?.loaded) return resolve(true);
    eventTarget.addEventListener("state", (s) => {
      if ((s as DeckcordEvent).data?.loaded) return resolve(true);
    });
  });

export const isLoggedIn = () =>
  new Promise((resolve) => {
    if (lastState?.logged_in) return resolve(true);
    eventTarget.addEventListener("state", (s) => {
      if ((s as DeckcordEvent).data?.logged_in) return resolve(true);
    });
  });
