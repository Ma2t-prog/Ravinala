# 🌍 GLOBAL MACRO DASHBOARD — User Guide

**Ravinala v2.0 — Professional Market Intelligence Interface**

---

## 🚀 Quick Start

### 1. **Open the Application**

```
URL: http://localhost:8501
```

### 2. **Login**

```
Username: admin
Password: ravinala2026
```

### 3. **Navigate to Dashboard**

- Click **"📊 Macro Analysis"** in the left sidebar
- Dashboard loads automatically

---

## 📊 DASHBOARD LAYOUT

The dashboard is organized into **6 main sections**:

### **SECTION 1: Global Equity Indices (30 Regions)**

**What it shows:**

- 30 major equity indices from all regions
- Organized into 4 geographic zones (Americas, Europe, Asia-Pacific, Middle East)
- Each index displays: Name, Current Price, Change %, Sentiment (🟢/🔴)

**How to use:**

1. Click **"🇺🇸 AMÉRIQUES"** expander to see US, Brazilian, Mexican indices
2. Each region is collapsible (click to expand/collapse)
3. Indices update in real-time when you click "🔄 Refresh"
4. Green arrow = market up, Red arrow = market down

**Key indices:**

- 🇺🇸 **S&P 500** (US broad market)
- 🇪🇺 **EURO STOXX 50** (Eurozone blue chips)
- 🌏 **Nikkei 225** (Japan)
- 🌏 **Hang Seng** (Hong Kong tech)
- 🌏 **Shanghai Composite** (China)

---

### **SECTION 2: Fixed Income - Government Bonds (20 Countries)**

**What it shows:**

- Bond yields for 20 major economies
- Three maturity points: **2Y**, **5Y**, **10Y** yields
- Spread vs benchmark rate
- Color indicators: ↓ Green (yields falling) / ↑ Red (yields rising)

**How to use:**

1. Scroll through the table
2. Compare yields across countries and maturities
3. **Spread column**: Shows deviation from "safe" benchmark (e.g., Bund 10Y for Europe)
4. Watch for inverted curves (10Y < 2Y) = recession signal

**Example reading:**

```
USA:  2Y=4.85% | 5Y=4.45% | 10Y=4.25% | Spread: +0bp (steepening yield curve)
```

---

### **SECTION 3: Foreign Exchange (20 Major Pairs)**

**What it shows:**

- Major FX pairs in two sub-sections:
  - **USD Base Pairs** (EUR/USD, GBP/USD, JPY, etc.)
  - **Cross Rates** (EUR/GBP, GBP/JPY, etc.)

**How to use:**

1. Left column: USD-denominated pairs
2. Right column: Cross rates between non-USD currencies
3. Each pair shows: **Price** (4 decimals), **Daily Change %**, **Volatility**
4. Monitor 🔴 **USD Index** for overall dollar strength

**What movements mean:**

- EUR/USD ↑ = Euro strong, Dollar weak
- USD/JPY ↑ = Dollar strong, Yen weak (risk-on)
- USD/JPY ↓ = Safe-haven bid (flight to quality)

---

### **SECTION 4: Commodities (22 Markets)**

**Organized into categories:**

#### 🥇 **Metals** (8)

- Gold, Silver (precious)
- Platinum, Palladium (rare)
- Copper, Aluminum, Zinc, Nickel (industrial)

#### 🛢️ **Energy** (4)

- WTI Crude, Brent Crude (oil prices)
- Natural Gas (energy heating fuel)
- Coal (power generation)

#### 🌾 **Agriculture** (6)

- Wheat, Corn, Soybeans (grains)
- Sugar, Coffee, Cocoa (soft commodities)

**How to use:**

1. Click expander for each category (metals/energy/agriculture)
2. Each shows price, YTD change %, emoji indicator
3. **Gold ↑** = Inflation/risk-off signal
4. **Oil ↑** = Inflation risk
5. **Ag prices ↑** = Food inflation

---

### **SECTION 5: Key Macro Indicators (By Region)**

**What it shows:**
A comprehensive table with:

- **GDP Growth**: Latest rate vs forecast
- **Inflation**: CPI (Consumer Price Index)
- **Unemployment**: % of workforce
- **Policy Rate**: Central bank interest rate
- **Manufacturing PMI**: Production activity index

**Regions covered:**

- 🇺🇸 USA
- 🇪🇺 Eurozone
- 🇬🇧 UK
- 🇯🇵 Japan
- 🇨🇳 China

**How to interpret:**

```
GDP > 2%       = Healthy growth
Inflation 2-3% = Target range
Unemployment < 4% = Tight labor market
PMI > 50       = Expansion
PMI < 50       = Contraction
```

---

### **SECTION 6: Advanced Indicators**

**Three information panels:**

#### **Volatility Indices**

- **VIX** (S&P 500 volatility):
  - 🟢 <20 = Complacent market
  - 🟡 20-30 = Normal
  - 🔴 >30 = Fear/Stress
- **V2X** (Eurostoxx50 volatility) — Same scale
- **MOVE** (Bond volatility) — Higher = rate uncertainty

#### **Credit Spreads**

- **HY vs IG**: High-Yield bonds vs Investment Grade
  - Wide spread = Risk-off environment
  - Narrow spread = Risk-on environment
- **IG Duration**: Time to recover par (rate sensitivity)
- **Emerging spreads**: Developing market bond premiums

#### **Valuation Metrics**

- **S&P 500 P/E**: Earnings multiple
  - <15x = Cheap
  - 15-20x = Fair
  - > 20x = Expensive
- **Shiller CAPE**: Cyclically-adjusted P/E (long-term valuation)
- **Dividend Yield**: Income from stocks

---

## 🎮 CONTROLS & FEATURES

### **Top Control Bar**

**1. 🔄 Refresh Button**

- Updates all market data from source (yFinance, etc.)
- Takes ~2-3 seconds
- Click when you notice data is stale

**2. Export Buttons** (Framework ready)

- 📄 **PDF Export** — Professional dashboard PDF (coming soon)
- 📊 **Excel Export** — Multi-sheet workbook by category (coming soon)
- 📧 **Email Export** — Send PDF to inbox with branding (coming soon)

**3. 📊 Last Update Timestamp**

- Shows when data was last refreshed
- 🟢 **LIVE** badge = Fresh data
- Refreshes every button click or manual reload

---

## 💡 HOW TO USE THIS DASHBOARD

### **For Portfolio Managers**

1. Check **Global Indices** for portfolio exposure
2. Monitor **FX pairs** if you have international holdings
3. Watch **Commodities** for inflation signals
4. Review **Bond yields** for duration risk
5. Check **VIX** before major decisions

### **For Risk Managers**

1. Monitor **Credit Spreads** for market stress
2. Watch **Volatility Indices** (VIX up = risk-off)
3. Check **Valuations** for bubble warnings
4. Review **Macro Indicators** for recession signs

### **For Traders**

1. Use **FX pairs** for currency trading signals
2. Watch **Commodities** for momentum trades
3. Monitor **Indices** for correlation patterns
4. Use **Volatility** for options strategy selection

### **For Economists**

1. Compare **Macro Indicators** across regions
2. Watch **Bond curves** for policy hints
3. Review **Inflation data** in indicators section
4. Monitor **PMI** for economic health

---

## 🎯 COMMON WORKFLOWS

### **Workflow 1: Morning Market Check (5 min)**

```
1. Open Dashboard
2. Scan Global Indices → Any overnight moves?
3. Check VIX → Stress in market?
4. Review FX pairs → Carry trade unwinding?
5. Glance at Bonds → Real rates changing?
6. → Decision: Risk-on or Risk-off?
```

### **Workflow 2: Macro Analysis (15 min)**

```
1. Review Key Macro Indicators by region
2. Compare to previous week
3. Check Bond yields
4. Monitor commodity prices
5. → Assess growth/inflation outlook
```

### **Workflow 3: Risk Monitoring (10 min)**

```
1. Check VIX, V2X, MOVE
2. Review Credit Spreads
3. Scan for extreme moves (red flags)
4. Monitor Valuation metrics
5. → Assess portfolio risk
```

### **Workflow 4: Export Report (2 min)**

```
1. Click 📊 Excel Export
2. File downloads
3. Open in Excel
4. Pivot tables auto-generated
5. Send to stakeholders
```

---

## 🔧 TROUBLESHOOTING

### **Issue: Some indices show no data**

**Solution**: Some Yahoo Finance tickers are outdated

- Affects: Some Middle East indices (TASI, DFM, TA125)
- Impact: Minimal (still 25/30 indices available)
- Fix coming: Updating to current ticker symbols

### **Issue: Dashboard loads slowly**

**Solution**: yFinance API has many requests

- Click 🔄 Refresh and wait 3-5 seconds
- If persistent: Check internet connection
- Workaround: Clear Streamlit cache

### **Issue: FX pairs show old data**

**Solution**: yFinance cache

- Click 🔄 Refresh
- FX data updates every 5 seconds usually

### **Issue: Cannot export to PDF/Excel**

**Solution**: Features are framework-ready, backends coming

- Buttons present but not yet connected to export engine
- Timeline: Available in 1-2 weeks
- Workaround: Use browser screenshot feature

---

## 📋 DATA DICTIONARY

### **Colors & Indicators**

| Symbol | Meaning                          |
| ------ | -------------------------------- |
| 🟢     | Price up or positive indicator   |
| 🔴     | Price down or negative indicator |
| ⚪     | No change or neutral             |
| 🟡     | Warning/caution threshold        |
| ↑      | Upward trend                     |
| ↓      | Downward trend                   |
| →      | Sideways/stable                  |

### **Key Thresholds**

```
VIX:           <20 = Calm,  20-30 = Normal,  >30 = Fear
P/E Ratio:     <15x = Cheap, 15-20x = Fair,  >25x = Expensive
Unemployment:  <4% = Tight,  4-5% = Healthy, >6% = Weak
Inflation:     <2% = Low,    2-3% = Target,  >3% = High
PMI:           >50 = Growth, <50 = Contraction
```

---

## 🔐 SECURITY & PERMISSIONS

- Dashboard is behind **authentication gate**
- All users (admin, tester, viewer) can access
- Data is **real-time** but "tamper-proof" (anti-copy enabled)
- No modifications to raw market data
- Audit trail of all access attempts

---

## 📞 SUPPORT

**For issues:**

1. Check Streamlit logs (terminal where you launched the app)
2. Try refreshing the dashboard (🔄 button)
3. Contact: matthew.tsivahiny@example.com

**For feature requests:**

- Global heatmaps (correlation matrices)
- Historical data charting (1D, 1W, 1M views)
- Sentiment analysis integration
- Trading alerts on moves

---

## 📚 ADDITIONAL RESOURCES

- **Ravinala Main App**: Full quantitative toolkit
- **Trading Book**: Derivative pricing and portfolio management
- **Admin Panel**: User and session management
- **Equity Research**: DCF and fundamental analysis
- **Fixed Income**: Bond analysis and OAS calculations

---

**🌴 Ravinala v2.0 — Your Complete Market Intelligence Platform**

_Last updated: March 16, 2026_
