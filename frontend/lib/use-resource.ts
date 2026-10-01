"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

export function useResource<T>(path: string, interval = 0) {
  const requestId = useRef(0);
  const inFlight = useRef<string | null>(null);
  const [state, setState] = useState({
    path,
    data: null as T | null,
    error: "",
    loading: true,
  });
  const reload = useCallback(async () => {
    if (inFlight.current === path) return;
    inFlight.current = path;
    const current = ++requestId.current;
    try {
      const data = await api<T>(path);
      if (current === requestId.current) {
        setState({ path, data, error: "", loading: false });
      }
    } catch (e) {
      if (current === requestId.current) {
        setState((previous) => ({
          path,
          data: previous.path === path ? previous.data : null,
          error: e instanceof Error ? e.message : "Something went wrong.",
          loading: false,
        }));
      }
    } finally {
      if (current === requestId.current) inFlight.current = null;
    }
  }, [path]);
  useEffect(() => {
    void reload();
    const timer = interval ? setInterval(reload, interval) : null;
    return () => {
      if (timer) clearInterval(timer);
      requestId.current++;
      inFlight.current = null;
    };
  }, [reload, interval]);
  // Never show another patient's response while the selected path is loading.
  const matches = state.path === path;
  return {
    data: matches ? state.data : null,
    error: matches ? state.error : "",
    loading: !matches || state.loading,
    reload,
  };
}
