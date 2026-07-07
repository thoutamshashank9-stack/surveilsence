

type MessageCallback = (data: any) => void;

class WebSocketService {
  private socket: WebSocket | null = null;
  private url: string = '';
  private listeners: Map<string, Set<MessageCallback>> = new Map();
  private reconnectTimer: any = null;
  private reconnectDelay: number = 1000;
  private maxReconnectDelay: number = 30000;
  private isConnecting: boolean = false;

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    // Proxied websocket is mapped to /api/v1/ws
    this.url = `${protocol}//${host}/api/v1/ws`;
  }

  public connect(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) return;
    if (this.isConnecting) return;
    
    this.isConnecting = true;
    console.log('Connecting to WebSocket...', this.url);
    
    try {
      this.socket = new WebSocket(this.url);
      
      this.socket.onopen = () => {
        console.log('WebSocket connected successfully');
        this.isConnecting = false;
        this.reconnectDelay = 1000; // Reset delay
        this.trigger('open', null);
        
        // Start heartbeat ping every 15s to keep connection alive
        this.startHeartbeat();
      };
      
      this.socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type) {
            this.trigger(payload.type, payload);
          }
        } catch (e) {
          console.warn('Error parsing websocket message JSON:', e);
        }
      };
      
      this.socket.onclose = (event) => {
        console.log('WebSocket disconnected', event.reason);
        this.isConnecting = false;
        this.socket = null;
        this.trigger('close', null);
        this.scheduleReconnect();
      };
      
      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.socket?.close();
      };
    } catch (e) {
      console.error('Failed to create WebSocket instance:', e);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private heartbeatTimer: any = null;
  private startHeartbeat(): void {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 15000);
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    
    this.reconnectTimer = setTimeout(() => {
      console.log('Attempting WebSocket reconnection...');
      this.connect();
      // Exponential backoff
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    }, this.reconnectDelay);
  }

  public subscribe(eventType: string, callback: MessageCallback): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  private trigger(eventType: string, data: any): void {
    this.listeners.get(eventType)?.forEach((cb) => {
      try {
        cb(data);
      } catch (err) {
        console.error(`Error in WebSocket listener for ${eventType}:`, err);
      }
    });
  }

  public disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.socket?.close();
    this.socket = null;
  }
}

export const wsService = new WebSocketService();
export default wsService;
