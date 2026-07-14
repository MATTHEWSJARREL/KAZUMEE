type JsonValue = any;

export type RealtimeMessage = {
  type: string;
  [key: string]: any;
};

type Subscriber = (message: RealtimeMessage) => void;

// Lazily-created, singleton-per-session realtime transport.
// Connect logic must stay identical to existing websocket behavior.
export class RealtimeClient {
  private ws: WebSocket | null = null;
  private readyState: number = 0;
  private lastMessage: RealtimeMessage | null = null;

  private subscribers = new Set<Subscriber>();
  private typeSubscribers = new Map<string, Set<Subscriber>>();

  private subscribersByPriority = 0; // reserved (no-op)

  // Promise to dedupe concurrent connect attempts
  private connectPromise: Promise<void> | null = null;

  constructor(
    private readonly opts: {
      url: string;
      connectToken: () => Promise<string | null>;
      shouldConnect: () => boolean;
      buildFinalUrl: (url: string, token: string | null) => string;
    },
  ) {}

  getReadyState() {
    return this.readyState;
  }

  hasActiveSubscribers() {
    return this.subscribers.size > 0 || this.typeSubscribers.size > 0 || this.ws !== null;
  }

  getLastMessage() {
    return this.lastMessage;
  }

  subscribe(sub: Subscriber) {
    this.subscribers.add(sub);
    return () => this.subscribers.delete(sub);
  }

  subscribeToType(type: string, sub: Subscriber) {
    if (!this.typeSubscribers.has(type)) this.typeSubscribers.set(type, new Set());
    this.typeSubscribers.get(type)!.add(sub);
    return () => {
      this.typeSubscribers.get(type)?.delete(sub);
      if (this.typeSubscribers.get(type)?.size === 0) this.typeSubscribers.delete(type);
    };
  }

  async ensureConnected() {
    if (this.connectPromise) return this.connectPromise;
    if (!this.opts.shouldConnect()) {
      this.readyState = WebSocket.CLOSED;
      return;
    }

    this.connectPromise = (async () => {
      const token = await this.opts.connectToken();
      // Rebuild URL just like the old hook (token query param when available)
      const finalUrl = this.opts.buildFinalUrl(this.opts.url, token);

      const ws = new WebSocket(finalUrl);
      this.ws = ws;

      ws.onopen = () => {
        this.readyState = WebSocket.OPEN;
      };

      ws.onmessage = (event) => {
        try {
          const message: RealtimeMessage = JSON.parse(event.data);
          this.lastMessage = message;

          // Notify type-specific first
          const setForType = this.typeSubscribers.get(message.type);
          if (setForType) {
            for (const sub of setForType) sub(message);
          }

          for (const sub of this.subscribers) sub(message);
        } catch (error) {
          // Match old behavior: console.error parse failure.
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        this.readyState = WebSocket.CLOSED;
        this.ws = null;
        this.connectPromise = null;
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.readyState = WebSocket.CLOSED;
        this.ws = null;
        this.connectPromise = null;
      };
    })();

    return this.connectPromise;
  }

  sendMessage(message: JsonValue) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not open. Cannot send message.');
    }
  }
}

let singleton: RealtimeClient | null = null;

export function getRealtimeClient() {
  if (singleton) return singleton;
  singleton = new RealtimeClient({
    url: `${(globalThis as any).__KAZUMI_WS_BASE || ""}/ws`,
    connectToken: async () => null,
    shouldConnect: () => false,
    buildFinalUrl: (url) => url,
  });
  return singleton;
}

// Session-scoped singleton factory. We do this indirection because this file must not
// import react hooks, and we need access to apiClient utilities.
export function createOrGetRealtimeClient(deps: {
  url: string;
  connectToken: () => Promise<string | null>;
  shouldConnect: () => boolean;
  buildFinalUrl: (url: string, token: string | null) => string;
}) {
  if (!singleton || !singleton.hasActiveSubscribers()) {
    singleton = new RealtimeClient({
      url: deps.url,
      connectToken: deps.connectToken,
      shouldConnect: deps.shouldConnect,
      buildFinalUrl: deps.buildFinalUrl,
    });
  }
  return singleton;
}

