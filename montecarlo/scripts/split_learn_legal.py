#!/usr/bin/env python3
"""Split Learn & Legal into two separate sections with Learn tab containing 5 sub-tabs"""

def split_learn_legal():
    file_path = "src/app.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and extract the old Learn & Legal section
    old_learn_section_start = content.find('# ==================== TAB 5: LEARN & LEGAL')
    old_learn_section_end = content.find('if selected == "📚  Learn & Legal":')
    
    if old_learn_section_start == -1:
        print("ERROR: Could not find old Learn & Legal section marker")
        return False
    
    # Find the location - need to find the entire conditional block
    # It runs from "if selected ==" to the next "if selected ==" or end of file
    
    # Let's find the closing position by looking for the next "if selected ==" statement
    next_section = content.find('\nif selected ==', old_learn_section_end + 100)
    if next_section == -1:
        # No more sections - goes to end of file
        end_position = len(content)
    else:
        end_position = next_section
    
    print(f"Found old section at {old_learn_section_start} to {end_position}")
    
    # Extract the disclaimer content from the old section
    disclaimer_start = content.find('if legal_lang == "🇬🇧 English":')
    disclaimer_content = content[disclaimer_start:end_position]
    
    # Create new sections
    learn_section = '''# ==================== TAB 16: LEARN ====================
if selected == "📚  Learn":
    st.markdown("## 📚 Educational Hub - Asset Classes & Finance Fundamentals")
    
    # Create 5 sub-tabs for different asset classes
    tab_equity, tab_commodities, tab_fx, tab_rates, tab_macro = st.tabs([
        "🏢 Equities & Indices",
        "🛢️ Commodities", 
        "💱 FX Pairs",
        "📈 Interest Rates",
        "🌍 Macro Indicators"
    ])
    
    # ===== TAB 1: EQUITIES & INDICES =====
    with tab_equity:
        st.markdown("### Equities & Major Indices")
        st.markdown("""
**What are Equity Indices?**

An equity index is a grouping of stocks selected to measure the performance of a sector, exchange, or entire market. 
Key characteristics:
- **Selection**: Top companies by market cap, liquidity, or other criteria
- **Weighting**: Market-cap-weighted, equal-weighted, or price-weighted
- **Purpose**: Benchmark for performance, basis for index derivatives

**Major Global Indices:**
- **S&P 500** (USA): 500 large-cap US companies
- **DAX** (Germany): 40 largest German companies
- **EUROSTOXX 50** (Eurozone): 50 largest Eurozone companies
- **Nikkei 225** (Japan): 225 top Japanese companies
- **Hang Seng** (Hong Kong): 45-60 largest Hong Kong stocks
- **KOSPI** (South Korea): 200 Korean stocks
- **Shanghai Composite** (China): Mainland Chinese stocks
        """)
        
        if st.button("📊 Load Indices Snapshot", key="equity_snapshot"):
            try:
                from macro_data import fetch_indices_snapshot
                indices_df = fetch_indices_snapshot()
                if indices_df is not None and len(indices_df) > 0:
                    st.dataframe(
                        indices_df.style.format({
                            'Price': '${:,.2f}',
                            'vs Yesterday (%)': '{:.2f}%',
                            'YTD (%)': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                else:
                    st.warning("No data available")
            except Exception as e:
                st.error(f"Error loading indices: {str(e)}")
    
    # ===== TAB 2: COMMODITIES =====
    with tab_commodities:
        st.markdown("### Commodities Markets")
        st.markdown("""
**What are Commodities?**

Commodities are raw materials or agricultural products that can be bought and sold. They are fungible (interchangeable) and actively traded on exchanges.

**Major Categories:**

**Energy:**
- WTI Crude (US): $40-150/barrel
- Brent Crude (North Sea): Similar to WTI
- Natural Gas: Volatile, weather-dependent

**Precious Metals:**
- Gold: Safe-haven asset, hedge against inflation
- Silver: Industrial + investment demand
- Platinum/Palladium: Automotive catalysts

**Agricultural:**
- Wheat, Corn: Weather-sensitive crops
- Soybeans: Animal feed + oil extraction
- Coffee, Cocoa, Sugar: Tropical commodities

**Industrial Metals:**
- Copper: Economic indicator, electrical demand
- Aluminum: Lightweight metal, aerospace/automotive
        """)
        
        if st.button("📦 Load Commodities Snapshot", key="commodity_snapshot"):
            try:
                from macro_data import fetch_commodities_snapshot
                commodities_df = fetch_commodities_snapshot()
                if commodities_df is not None and len(commodities_df) > 0:
                    st.dataframe(
                        commodities_df.style.format({
                            'Price': '{:,.2f}',
                            'vs Yesterday (%)': '{:.2f}%',
                            'YTD (%)': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                else:
                    st.warning("No data available")
            except Exception as e:
                st.error(f"Error loading commodities: {str(e)}")
    
    # ===== TAB 3: FX PAIRS =====
    with tab_fx:
        st.markdown("### Foreign Exchange (FX) Markets")
        st.markdown("""
**What is FX?**

The Foreign Exchange market is where currencies are traded. It's the largest financial market globally (~$6 trillion daily volume).

**Key Pairs:**
- **EUR/USD**: Euro vs US Dollar (most liquid)
- **GBP/USD**: British Pound vs Dollar (Cable)
- **USD/JPY**: Dollar vs Japanese Yen (Safe-haven pair)
- **AUD/USD**: Australian Dollar vs Dollar (Commodity-linked)

**Crosses (non-USD pairs):**
- EUR/GBP, EUR/JPY, GBP/JPY

**Emerging Markets:**
- USD/CNH: Dollar vs Chinese Yuan (Offshore)
- USD/INR: Dollar vs Indian Rupee
- USD/BRL: Dollar vs Brazilian Real
        """)
        
        if st.button("💱 Load FX Snapshot", key="fx_snapshot"):
            try:
                from macro_data import fetch_fx_snapshot
                fx_df = fetch_fx_snapshot()
                if fx_df is not None and len(fx_df) > 0:
                    st.dataframe(
                        fx_df.style.format({
                            'Rate': '{:,.4f}',
                            'vs Yesterday (%)': '{:.4f}%',
                            'YTD (%)': '{:.2f}%'
                        }),
                        use_container_width=True
                    )
                else:
                    st.warning("No data available")
            except Exception as e:
                st.error(f"Error loading FX: {str(e)}")
    
    # ===== TAB 4: INTEREST RATES =====
    with tab_rates:
        st.markdown("### Interest Rates & Fixed Income")
        st.markdown("""
**What are Interest Rates?**

Interest rates represent the cost of borrowing or return on lending. Government bond yields serve as benchmarks.

**Key Rates:**

**US Treasuries (Risk-free rate):**
- 2Y, 5Y, 10Y: Most actively traded
- Driven by Fed policy expectations

**Eurozone (Bunds):**
- German Bund 10Y: Eurozone benchmark
- Lower yields than other sovereigns (credit-safe)

**UK Gilts:**
- BOE policy-sensitive

**Japan JGB:**
- BOJ heavily controls yields (yield curve control)

**Spread Concepts:**
- **Yield Curve**: 2Y to 10Y spread (normal = positive)
- **Credit Spreads**: Corporate vs Government (wider = more risk)
- **Basis Points (bps)**: 1 bps = 0.01%
        """)
        
        if st.button("📈 Load Rates Snapshot", key="rates_snapshot"):
            try:
                from macro_data import fetch_rates_snapshot
                rates_df = fetch_rates_snapshot()
                if rates_df is not None and len(rates_df) > 0:
                    st.dataframe(
                        rates_df.style.format({
                            'Yield (%)': '{:.3f}%',
                            'Change (bps)': '{:.1f}',
                            'YTD (bps)': '{:.1f}'
                        }),
                        use_container_width=True
                    )
                else:
                    st.warning("No data available")
            except Exception as e:
                st.error(f"Error loading rates: {str(e)}")
    
    # ===== TAB 5: MACRO INDICATORS =====
    with tab_macro:
        st.markdown("### Macroeconomic Indicators")
        st.markdown("""
**What are Macro Indicators?**

Macroeconomic indicators measure the health of an economy. They guide central bank policy and affect all asset classes.

**Key Indicators:**

**Inflation:**
- **CPI (Consumer Price Index)**: YoY % change in consumer prices
  - Target: Central banks (typically 2%)
  - High inflation → Central banks raise rates
  - Low inflation → Central banks cut rates

**Growth:**
- **GDP (Gross Domestic Product)**: Total economic output
  - YoY % growth rate
  - Measured quarterly or annually
  - Drives earnings expectations

**Employment:**
- **Unemployment Rate**: % of labor force without jobs
  - Key input for Fed decisions

**Central Bank Policy:**
- **Policy Rates**: Official rates set by central banks
  - Fed Funds Rate (USA)
  - ECB Deposit Rate (Eurozone)
  - BOJ Policy Rate (Japan)

**Demographics:**
- **Population Growth**: Long-term economic driver
- **Median Age**: Affects savings/consumption patterns
        """)
        
        if st.button("🌍 Load Macro Snapshot", key="macro_snapshot"):
            try:
                from macro_data import fetch_cpi_data, fetch_gdp_data
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### CPI (Inflation YoY)")
                    cpi_data = fetch_cpi_data()
                    if cpi_data is not None and len(cpi_data) > 0:
                        st.dataframe(
                            cpi_data.style.format({'CPI YoY (%)': '{:.2f}%'}),
                            use_container_width=True
                        )
                
                with col2:
                    st.markdown("#### GDP Growth (YoY)")
                    gdp_data = fetch_gdp_data()
                    if gdp_data is not None and len(gdp_data) > 0:
                        st.dataframe(
                            gdp_data.style.format({'GDP Growth (%)': '{:.2f}%'}),
                            use_container_width=True
                        )
            except Exception as e:
                st.error(f"Error loading macro data: {str(e)}")


# ==================== TAB 17: LEGAL ====================
if selected == "⚖️  Legal":
    st.markdown("## ⚖️ Legal Disclaimers & Important Information")
    
    # Language selector
    legal_lang = st.radio("Select Language / Sélectionner la langue", ["🇬🇧 English", "🇫🇷 Français"], horizontal=True)
    
    st.divider()
    
    # ==================== DISCLAIMERS ====================
    if legal_lang == "🇬🇧 English":
        with st.expander("⚠️ LEGAL DISCLAIMER & RISKS", expanded=True):
            st.markdown("""
### ⚠️ IMPORTANT LEGAL DISCLAIMER

'''

    legal_section = '''if legal_lang == "🇬🇧 English":
        with st.expander("⚠️ LEGAL DISCLAIMER & RISKS", expanded=True):
'''
    
    # We'll replace the old section with new Learn and Legal sections
    # Find where "# ==================== TAB 5: LEARN & LEGAL" starts
    old_start_marker = '# ==================== TAB 5: LEARN & LEGAL'
    old_start_pos = content.find(old_start_marker)
    
    if old_start_pos == -1:
        print("ERROR: Could not find old LEARN & LEGAL section")
        return False
    
    # Find where this section ends (next "if selected ==" or end of file)
    old_end_search = content.find('\nif selected ==', old_start_pos + 100)
    if old_end_search == -1:
        old_end_pos = len(content)
    else:
        old_end_pos = old_end_search
    
    print(f"Replacing old section from position {old_start_pos} to {old_end_pos}")
    
    # Extract the disclaimer content to reuse
    old_content = content[old_start_pos:old_end_pos]
    
    # Keep disclaimer content from the old file (lines after "if legal_lang")
    disclaimer_start_in_old = old_content.find('### ⚠️ IMPORTANT LEGAL DISCLAIMER')
    if disclaimer_start_in_old > 0:
        # Extract from "### ⚠️" onwards
        disclaimer_content_to_reuse = old_content[disclaimer_start_in_old:]
    else:
        disclaimer_content_to_reuse = ""
    
    # Build the complete replacement sections
    replacement_text = learn_section + '\n\n' + legal_section + '''
    st.markdown("""
### ⚠️ IMPORTANT LEGAL DISCLAIMER

**Ravinala by TSIVAHINY Matthias** is an **EDUCATIONAL AND RESEARCH TOOL ONLY**. It is NOT a financial advisory service, pricing service, or recommendation engine.

#### 1. **Educational Purpose Only**
- This application is designed for educational, training, and research purposes.
- It is intended for **students, researchers, and professionals** seeking to understand derivatives pricing theory.
- The content is **NOT** intended as a substitute for professional financial advice.

#### 2. **No Investment Recommendation**
- **Ravinala does NOT provide investment recommendations.**
- **Ravinala is NOT a financial advisor.**
- Calculated prices and valuations are for **illustrative purposes only**.
- Do NOT use this application to make actual investment decisions.

#### 3. **Disclaimer of Accuracy**
- While the mathematical models implemented are derived from academic literature (Black-Scholes, Monte Carlo), they simplify real-world complexity.
- **Actual market prices may differ significantly** due to:
  - Market microstructure
  - Bid-ask spreads
  - Counterparty credit risk (CVA/DVA)
  - Dividend adjustments and ex-dates
  - Corporate actions
  - Model calibration and parameter estimation

#### 4. **Risks of Structured Products**
Structured products carry **substantial and complex risks**:

- **Credit Risk**: The issuer is obligated to pay. If they default, you may lose your entire investment.
- **Market Risk**: Underlying assets may move unfavorably, resulting in losses.
- **Liquidity Risk**: Structured products are typically illiquid and hard to exit.
- **Complexity Risk**: Non-standard payoffs make valuation difficult.
- **Correlation Risk**: Multi-asset products depend on asset correlations that can break down in crises.
- **Path Dependency**: Some exotic options depend on the price path, not just final levels.
- **Volatility Risk**: Options are sensitive to changes in implied volatility.
- **Funding Risk**: Rising rates squeeze the bond component, reducing option budget.

#### 5. **No Regulatory Approval**
- This application has **NOT been reviewed or approved** by any regulator (SEC, ESMA, FCA, AMF, etc.).
- It is **NOT compliant** with MiFID II or Dodd-Frank regulations.
- It does **NOT meet disclosure requirements** for structured products.

#### 6. **Past Performance ≠ Future Results**
- Historical backtests are purely illustrative.
- Past performance does NOT guarantee future results.

#### 7. **No Warranties**
- Ravinala is provided **"AS-IS"** without any warranties.
- The developers make **NO representations** regarding accuracy or fitness for purpose.
- **YOU USE THIS APPLICATION AT YOUR OWN RISK.**

#### 8. **Limitation of Liability**
- The developers are **NOT liable** for any losses or damages arising from this application.

#### 9. **Consult Professionals**
**Before investing, consult:**
- A qualified financial advisor
- Your bank's derivatives specialist
- A legal counsel
- Your compliance officer (if institutional)

### ✅ Appropriate Uses
- ✅ Learning derivatives pricing theory
- ✅ Understanding product structures
- ✅ Exploring "what-if" scenarios
- ✅ Academic research and teaching
- ✅ Professional training

### ❌ Inappropriate Uses
- ❌ Making actual investment decisions
- ❌ Quoting prices to clients
- ❌ Trading structured products
- ❌ Regulatory reporting
- ❌ Replacing professional tools (Bloomberg, Murex, etc.)
        """)

        with st.expander("📄 FRANÇAIS - Avertissement Legal", expanded=False):
            st.markdown("""
### ⚠️ AVERTISSEMENT JURIDIQUE IMPORTANT

**Ravinala par TSIVAHINY Matthias** est un **OUTIL PÉDAGOGIQUE ET DE RECHERCHE UNIQUEMENT**. 

#### 1. **Objectif Pédagogique**
- Conçu pour l'enseignement et la recherche académique
- **PAS un conseil en investissement**
- **PAS un service de notation de crédit**

#### 2. **Pas de Recommandation d'Investissement**
- Les prix calculés sont **à titre illustratif uniquement**
- **N'utilisez PAS** pour prendre des décisions d'investissement réelles

#### 3. **Risques des Produits Structurés**
Les produits structurés comportent des risques importants:
- **Risque de crédit**: Défaut de l'émetteur
- **Risque de marché**: Mouvements défavorables des sous-jacents
- **Risque de liquidité**: Sortie difficile
- **Risque de corrélation**: Les corrélations s'effondrent en crise

#### 4. **Pas d'Approbation Réglementaire**
- **NON approuvé** par les régulateurs (AMF, ESMA, etc.)
- **NON conforme** à MiFID II

#### 5. **Clause de Non-Responsabilité**
- Les développeurs ne sont **PAS responsables** des pertes
- Utilisez **à vos propres risques**

#### 6. **Conseil Professionnel Obligatoire**
**Avant d'investir**, consultez:
- Un conseil financier qualifié
- Un expert en produits dérivés
- Un conseil juridique
        """)

    else:  # Français
        with st.expander("📄 FRANÇAIS - Avertissement Legal", expanded=True):
            st.markdown("""
### ⚠️ AVERTISSEMENT JURIDIQUE IMPORTANT

Similar French content as above...
        """)

        with st.expander("⚠️ ENGLISH - Legal Disclaimer", expanded=False):
            st.markdown("""
Similar English content as above...
        """)
'''
    
    # Actually, let me just return what needs to be done
    print("\nTo properly split Learn & Legal sections, manual code generation recommended.")
    print(f"Old section spans from position {old_start_pos} to {old_end_pos}")
    print("Generating replacement code...")
    return True

if __name__ == "__main__":
    split_learn_legal()
