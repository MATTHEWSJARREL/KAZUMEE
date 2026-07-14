"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { useRealtime } from "./useRealtime";

export default function RealtimeProvider({ children }: { children: ReactNode }) {
  // Mounting useRealtime ensures the connection is initialized and shared
  // through the singleton client.
  const { readyState, lastMessage } = useRealtime();

  useEffect(() => {
    void readyState;
    void lastMessage;
  }, [readyState, lastMessage]);

  return <>{children}</>;
}

