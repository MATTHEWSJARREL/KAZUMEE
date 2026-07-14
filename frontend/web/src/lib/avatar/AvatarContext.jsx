import { createContext, useContext, useState } from "react";

const AvatarContext = createContext({
  avatarUrl: "/zumi.png",
  setAvatarUrl: () => {},
  avatarState: "idle",
  setAvatarState: () => {},
});

export function AvatarProvider({ children }) {
  const [avatarUrl, setAvatarUrl] = useState("/zumi.png");
  const [avatarState, setAvatarState] = useState("idle");

  return (
    <AvatarContext.Provider value={{ avatarUrl, setAvatarUrl, avatarState, setAvatarState }}>
      {children}
    </AvatarContext.Provider>
  );
}

export function useAvatarContext() {
  return useContext(AvatarContext);
}

