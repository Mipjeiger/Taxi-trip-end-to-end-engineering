class WebSocketService {
    private url: string;
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 3000;

    constructor() {
        // fallback logic to .env ( no hardcoded URL )
        const envUrl = process.env.REACT_APP_WS_URL;
        if (!envUrl) {
            throw new Error("WebSocket URL is not defined in environment variables");
        }
        this.url = envUrl;
    }

    connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(this.url);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    resolve();
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    reject(error);
                };

                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.attemptReconnect();
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    private attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connect(), this.reconnectDelay);
        }
    }

    subscribe(event: string, callback: (data: any) => void) {
        if (this.ws) {
            this.ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.event === event) callback(data.payload);
            };
        }
    }

    send(event: string, data: any) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ event, data }));
        }
    }

    disconnect() {
        if (this.ws) this.ws.close();
    }
}

export const wsService = new WebSocketService();