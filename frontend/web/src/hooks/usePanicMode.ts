import { useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

export function usePanicMode() {
  const [isPanicMode, setIsPanicMode] = useState(false);
  const { lastMessage } = useWebSocket();

  useEffect(() => {
    // Listen for panic mode events from WebSocket
    if (lastMessage !== null && lastMessage.type === 'PANIC_MODE') {
      setIsPanicMode(true);
      // Auto-hide after 10 seconds
      setTimeout(() => setIsPanicMode(false), 10000);
    }
  }, [lastMessage]);

  // Keep the custom event listener for backward compatibility
  useEffect(() => {
    const handlePanicMode = (event: CustomEvent) => {
      if (event.detail?.action === 'panic_mode') {
        setIsPanicMode(true);
        // Auto-hide after 10 seconds
        setTimeout(() => setIsPanicMode(false), 10000);
      }
    };

    window.addEventListener('panicMode', handlePanicMode as EventListener);

    return () => {
      window.removeEventListener('panicMode', handlePanicMode as EventListener);
    };
  }, []);

  const deactivatePanicMode = () => {
    setIsPanicMode(false);
  };

  return { isPanicMode, deactivatePanicMode };
}
