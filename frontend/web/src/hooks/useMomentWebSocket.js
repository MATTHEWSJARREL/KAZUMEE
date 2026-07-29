import { useEffect, useRef, useState } from 'react';

/**
 * Custom hook for real-time moment detection via WebSocket
 * Connects to backend WebSocket and triggers callback on moment updates
 */
export function useMomentWebSocket(onMomentDetected, onStatusUpdate) {
  const wsRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttemptsRef = useRef(10);

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Connect directly to backend, not through proxy
        const wsUrl = `${protocol}//localhost:8000/api/moments/ws/updates`;

        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          console.log('✅ Connected to moment detection WebSocket');
          setIsConnected(true);
          reconnectAttemptsRef.current = 0;

          // Start heartbeat to keep connection alive
          if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = setInterval(() => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send('ping');
            }
          }, 25000); // Ping every 25 seconds (server sends heartbeat every 30s)
        };

        wsRef.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            if (message.type === 'connection_established') {
              console.log('🔗 WebSocket connection established');
            } else if (message.type === 'moment_update' && onMomentDetected) {
              console.log('🎬 Moment detected via WebSocket:', message.data);
              onMomentDetected(message.data);
            } else if (message.type === 'status_update' && onStatusUpdate) {
              console.log('📊 Status update:', message.data);
              onStatusUpdate(message.data);
            } else if (message.type === 'heartbeat') {
              console.log('💓 Heartbeat received');
            } else if (message.type === 'pong') {
              console.log('🏓 Pong received');
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        wsRef.current.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          setIsConnected(false);
        };

        wsRef.current.onclose = () => {
          console.log('⏸️ Disconnected from WebSocket');
          setIsConnected(false);

          // Clear heartbeat
          if (heartbeatIntervalRef.current) {
            clearInterval(heartbeatIntervalRef.current);
          }

          // Attempt reconnect with exponential backoff
          if (reconnectAttemptsRef.current < maxReconnectAttemptsRef.current) {
            const backoffDelay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
            reconnectAttemptsRef.current += 1;
            console.log(`🔄 Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttemptsRef.current})`);

            reconnectTimeoutRef.current = setTimeout(() => {
              connectWebSocket();
            }, backoffDelay);
          } else {
            console.error('❌ Max reconnection attempts reached');
          }
        };
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
      }
    };
  }, [onMomentDetected, onStatusUpdate]);

  return { isConnected, ws: wsRef.current };
}
