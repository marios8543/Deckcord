import { call, addEventListener, removeEventListener } from "@decky/api";
import { useEffect, useState } from "react";

export function useDeckcordState() {
  const [state, setState] = useState<any | undefined>();

  useEffect(() => {
    call("get_state").then((s) => setState(s));

    addEventListener("state", (data: any) => {
      setState(data);
    });

    return () => {
      removeEventListener("state", (data: any) => {
        setState(data);
      });
    };
  }, []);

  return state;
}

export const isLoaded = () =>
  new Promise((resolve) => {
    call("get_state").then((s: any) => {
      if (s.loaded) resolve(true);
    });

    const listener = (s: any) => {
      if (s.loaded) {
        removeEventListener("state", listener);
        return resolve(true);
      }
    };
    addEventListener("state", listener);
  });

export const isLoggedIn = () =>
  new Promise((resolve) => {
    call("get_state").then((s: any) => {
      if (s.logged_in) resolve(true);
    });

    const listener = (s: any) => {
      if (s.logged_in) {
        removeEventListener("state", listener);
        return resolve(true);
      }
    };
    addEventListener("state", listener);
  });
