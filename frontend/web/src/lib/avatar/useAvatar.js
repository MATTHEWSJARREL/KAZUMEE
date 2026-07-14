import { useAvatarContext } from "./AvatarContext";

export function useAvatar() {
  const { avatarUrl, setAvatarUrl, avatarState, setAvatarState } = useAvatarContext();
  return { avatarUrl, setAvatarUrl, avatarState, setAvatarState };
}

