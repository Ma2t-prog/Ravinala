/**
 * RAVINALA Market Data WebSocket Client
 *
 * JavaScript client for real-time market data from WebSocket server.
 * Usage:
 *     const client = new MarketDataClient();
 *     client.subscribe("AAPL", (data) => {
 *         console.log(`AAPL: $${data.price}`);
 *         updateUI(data);
 *     });
 */

class MarketDataClient {
  constructor(url = "ws://localhost:8000/ws/marketdata") {
    this.url = url;
    this.ws = null;
    this.listeners = {}; // {symbol: [callbacks]}
    this.lastUpdate = {}; // {symbol: timestamp}
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000; // 3 seconds

    this.connect();
  }

  /**
   * Establish WebSocket connection
   */
  connect() {
    console.log(`🔌 Connecting to ${this.url}...`);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("✓ Connected to market data server");
        this.reconnectAttempts = 0;
        this.emit("connected", {
          timestamp: new Date().toISOString(),
        });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const symbol = data.symbol;

          // Handle subscription confirmations
          if (data.type === "subscription_confirmed") {
            console.log(`✓ ${data.action}: ${data.symbol}`);
            return;
          }

          // Emit event for this symbol
          if (this.listeners[symbol]) {
            this.listeners[symbol].forEach((callback) => {
              try {
                callback(data);
              } catch (e) {
                console.error("Callback error:", e);
              }
            });
          }

          // Store last update
          this.lastUpdate[symbol] = data.timestamp;

          // Optional: Flash animation
          this.flashSymbol(symbol);
        } catch (e) {
          console.error("Message parse error:", e);
        }
      };

      this.ws.onerror = (error) => {
        console.error("🔴 WebSocket error:", error);
        this.emit("error", { error });
      };

      this.ws.onclose = () => {
        console.log("✗ Disconnected from market data server");
        this.emit("disconnected", {});

        // Attempt reconnect
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(
            `🔄 Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`,
          );
          setTimeout(() => this.connect(), this.reconnectDelay);
        }
      };
    } catch (e) {
      console.error("Connection error:", e);
      this.emit("error", { error: e });
    }
  }

  /**
   * Subscribe to a symbol (start receiving updates)
   * @param {string} symbol - e.g., "AAPL", "BTCUSD", etc.
   * @param {function} callback - Called with each price update
   */
  subscribe(symbol, callback) {
    symbol = symbol.toUpperCase();

    if (!this.listeners[symbol]) {
      this.listeners[symbol] = [];
    }
    this.listeners[symbol].push(callback);

    // Send subscribe command to server
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: "subscribe",
          symbol: symbol,
        }),
      );
    }
  }

  /**
   * Unsubscribe from a symbol
   * @param {string} symbol - e.g., "AAPL"
   */
  unsubscribe(symbol) {
    symbol = symbol.toUpperCase();
    delete this.listeners[symbol];

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: "unsubscribe",
          symbol: symbol,
        }),
      );
    }
  }

  /**
   * Get last update time for a symbol
   * @param {string} symbol
   * @returns {string|null} - ISO timestamp or null
   */
  getLastUpdate(symbol) {
    return this.lastUpdate[symbol.toUpperCase()] || null;
  }

  /**
   * Flash animation for symbol cell (optional)
   * @private
   */
  flashSymbol(symbol) {
    const el = document.querySelector(`[data-symbol="${symbol}"]`);
    if (el) {
      el.classList.add("flash");
      setTimeout(() => el.classList.remove("flash"), 200);
    }
  }

  /**
   * Emit custom events
   * @private
   */
  emit(event, data = {}) {
    const customEvent = new CustomEvent(`market-${event}`, { detail: data });
    document.dispatchEvent(customEvent);
  }

  /**
   * Close connection
   */
  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// ================================
// UI INTEGRATION HELPERS
// ================================

/**
 * Create a market data display card
 * @param {string} symbol
 * @param {object} initialData
 * @returns {HTMLElement}
 */
function createMarketCard(symbol, initialData = {}) {
  const card = document.createElement("div");
  card.className = "market-card";
  card.setAttribute("data-symbol", symbol);

  card.innerHTML = `
        <div class="market-card-symbol">${symbol}</div>
        <div class="market-card-price">$${initialData.price || "---"}</div>
        <div class="market-card-change">${initialData.change || "0.00%"}</div>
        <div class="market-card-time">${initialData.timestamp || "---"}</div>
    `;

  return card;
}

/**
 * Update card with new market data
 * @param {HTMLElement} card
 * @param {object} data
 */
function updateMarketCard(card, data) {
  const priceEl = card.querySelector(".market-card-price");
  const timeEl = card.querySelector(".market-card-time");

  if (priceEl) priceEl.textContent = `$${data.price.toFixed(2)}`;
  if (timeEl)
    timeEl.textContent = new Date(data.timestamp).toLocaleTimeString();

  // Color indicator: green for up, red for down
  if (data.bid && data.ask) {
    const spread = (((data.ask - data.bid) / data.bid) * 100).toFixed(2);
    card.style.borderColor = spread < 0.1 ? "green" : "orange";
  }
}

// ================================
// EXAMPLE USAGE
// ================================

/*
// Initialize client
const marketClient = new MarketDataClient("ws://localhost:8000/ws/marketdata");

// Subscribe to AAPL updates
marketClient.subscribe("AAPL", (data) => {
    console.log(`AAPL: $${data.price}`);
    
    // Update UI
    const card = document.getElementById("aapl-card");
    if (card) {
        updateMarketCard(card, data);
    }
});

// Listen for connection events
document.addEventListener("market-connected", () => {
    console.log("🟢 Connected to market server");
});

document.addEventListener("market-disconnected", () => {
    console.log("🔴 Disconnected from market server");
});

document.addEventListener("market-error", (e) => {
    console.error("Market error:", e.detail);
});
*/

// Export for use in modules
if (typeof module !== "undefined" && module.exports) {
  module.exports = { MarketDataClient, createMarketCard, updateMarketCard };
}
