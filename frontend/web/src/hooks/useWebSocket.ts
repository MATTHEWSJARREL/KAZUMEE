import { useRealtime } from '@/lib/realtime/useRealtime';
import { wsBase } from '@/lib/apiClient';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export function useWebSocket(url = `${wsBase}/ws`) {
  const { lastMessage, readyState, sendMessage } = useRealtime();
  void url;
  return { lastMessage: lastMessage as WebSocketMessage | null, readyState, sendMessage };
}
