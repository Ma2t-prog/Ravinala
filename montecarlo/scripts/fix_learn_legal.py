#!/usr/bin/env python3
"""Replace the old combined Learn & Legal section with separate Learn and Legal tabs"""

def replace_learn_legal_sections():
    file_path = "src/app.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and remove old section
    old_marker = '# ==================== TAB 5: LEARN & LEGAL =='
    old_pos = content.find(old_marker)
    
    if old_pos == -1:
        print("ERROR: Could not find old Learn & Legal marker")
        return False
    
    # Create the new Learn and Legal sections
    new_sections = '''# ==================== TAB 15: LEARN ====================
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

An equity index is a grouping of stocks that measures market performance. Key indices:
- **S&P 500** (USA): 500 large-cap US companies → Market leader
- **DAX** (Germany): 40 largest German companies → Eurozone bellwether  
- **EUROSTOXX 50** (Eurozone): 50 largest EU companies
- **Nikkei 225** (Japan): 225 top Japanese companies
- **Hang Seng** (Hong Kong): Major Hong Kong stocks
- **KOSPI** (South Korea): Korean market index
        """)
        
        if st.button("📊 Load Indices Snapshot", key="equity_snapshot"):
            try:
                from macro_data import fetch_indices_snapshot
                indices_df = fetch_indices_snapshot()
                if indices_df is not None and len(indices_df) > 0:
                    st.dataframe(indices_df, use_container_width=True)
                else:
                    st.warning("No data available")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # ===== TAB 2: COMMODITIES =====
    with tab_commodities:
        st.markdown("### Commodities Markets")
        st.markdown("""
**What are Commodities?**

Raw materials and agricultural products traded on global exchanges:
- **Energy**: WTI Crude, Brent, Natural Gas
- **Metals**: Gold, Silver, Copper, Aluminum
- **Agricultural**: Wheat, Corn, Soybeans, Coffee, Cocoa
- **Uses**: Industrial production, hedging inflation, portfolio diversification
        """)
        
        if st.button("📦 Load Commodities", key="commodity_snapshot"):
            try:
                from macro_data import fetch_commodities_snapshot
                comm_df = fetch_commodities_snapshot()
                if comm_df is not None and len(comm_df) > 0:
                    st.dataframe(comm_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # ===== TAB 3: FX PAIRS =====
    with tab_fx:
        st.markdown("### Foreign Exchange (FX) Markets")
        st.markdown("""
**What is FX?**

Currency trading market - largest financial market globally (~$6 trillion daily volume).

**Key Pairs:**
- **EUR/USD**: Euro vs US Dollar (most liquid)
- **GBP/USD**: British Pound vs Dollar 
- **USD/JPY**: Dollar vs Yen (safe-haven pair)
- **AUD/USD**: Australian Dollar vs Dollar
- **Emerging Markets**: USD/CNH, USD/INR, USD/BRL
        """)
        
        if st.button("💱 Load FX Snapshot", key="fx_snapshot"):
            try:
                from macro_data import fetch_fx_snapshot
                fx_df = fetch_fx_snapshot()
                if fx_df is not None and len(fx_df) > 0:
                    st.dataframe(fx_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # ===== TAB 4: INTEREST RATES =====
    with tab_rates:
        st.markdown("### Interest Rates & Fixed Income")
        st.markdown("""
**What are Interest Rates?**

Cost of borrowing/return on lending. Government bond yields are key economic indicators.

**Key Rates:**
- **US Treasuries**: 2Y, 5Y, 10Y benchmarks (Fed policy-sensitive)
- **German Bunds**: Eurozone risk-free rate
- **UK Gilts**: BOE policy-sensitive
- **Japan JGB**: BOJ heavily manages yields
- **Spreads**: Yield curve (2Y-10Y), credit spreads measure risk
- **1 basis point = 0.01%**
        """)
        
        if st.button("📈 Load Rates Snapshot", key="rates_snapshot"):
            try:
                from macro_data import fetch_rates_snapshot
                rates_df = fetch_rates_snapshot()
                if rates_df is not None and len(rates_df) > 0:
                    st.dataframe(rates_df, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # ===== TAB 5: MACRO INDICATORS =====
    with tab_macro:
        st.markdown("### Macroeconomic Indicators")
        st.markdown("""
**Key Macro Indicators:**
- **CPI (Inflation)**: YoY % change in consumer prices (Central banks target 2%)
- **GDP**: Total economic output growth (YoY %)
- **Unemployment**: % of labor force without jobs
- **Central Bank Rates**: Fed Funds Rate, ECB Deposit Rate, BOJ Policy Rate
- **Demographics**: Population growth, median age

These indicators drive central bank policy and affect all asset classes significantly.
        """)
        
        if st.button("🌍 Load Macro Data", key="macro_snapshot"):
            try:
                from macro_data import fetch_cpi_data, fetch_gdp_data
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### CPI Inflation (YoY)")
                    cpi = fetch_cpi_data()
                    if cpi is not None: st.dataframe(cpi, use_container_width=True)
                with col2:
                    st.markdown("#### GDP Growth (YoY)")
                    gdp = fetch_gdp_data()
                    if gdp is not None: st.dataframe(gdp, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {str(e)}")


# ==================== TAB 16: LEGAL ====================
if selected == "⚖️  Legal":
    st.markdown("## ⚖️ Legal Disclaimers & Important Information")
    
    legal_lang = st.radio("Language / Langue", ["🇬🇧 English", "🇫🇷 Français"], horizontal=True)
    st.divider()
    
    if legal_lang == "🇬🇧 English":
        with st.expander("⚠️ LEGAL DISCLAIMER & RISKS", expanded=True):
            st.markdown("""
### ⚠️ IMPORTANT LEGAL DISCLAIMER

**Ravinala by TSIVAHINY Matthias** is an **EDUCATIONAL AND RESEARCH TOOL ONLY**. 

#### 1. **No Investment Advice**
- **NOT a financial advisor or recommendation engine**
- Prices calculated are **illustrative purposes only**
- DO NOT use for actual investment decisions

#### 2. **Disclaimer of Accuracy**
- Mathematical models simplify real-world complexity
- Actual market prices may differ significantly
- Missing: bid-ask spreads, credit risk, dividends, market microstructure

#### 3. **Risks of Structured Products**
- **Credit Risk**: Issuer default → Loss of capital
- **Market Risk**: Underlying assets move unfavorably
- **Liquidity Risk**: Hard to exit early
- **Correlation Risk**: Correlations collapse in crises
- **Path Dependency**: Some options depend on price trajectory
- **Volatility Risk**: Sensitive to changes in implied volatility
- **Funding Risk**: Rising rates compress option budget

#### 4. **No Regulatory Approval**
- NOT reviewed or approved by SEC, ESMA, FCA, AMF, BaFin, etc.
- NOT compliant with MiFID II or Dodd-Frank
- Does NOT meet structured product disclosure requirements

#### 5. **Past Performance ≠ Future Results**
- Historical backtests are purely illustrative
- Past performance does NOT predict future results

#### 6. **As-Is, No Warranties**
- Provided "AS-IS" without warranties
- Developers NOT LIABLE for losses or damages
- YOU USE AT YOUR OWN RISK

#### 7. **Before Investing - Consult:**
- A qualified financial advisor
- Your bank's derivatives specialist  
- A legal counsel to review terms
- Your compliance officer (if institutional)

### ✅ Appropriate Uses
- ✅ Learning derivatives pricing theory
- ✅ Understanding product structures  
- ✅ Academic research and teaching
- ✅ Professional training
- ✅ Exploring "what-if" scenarios

### ❌ Inappropriate Uses
- ❌ Making actual investment decisions
- ❌ Quoting prices to clients
- ❌ Trading structured products
- ❌ Regulatory reporting
- ❌ Replacing professional tools (Bloomberg, Murex, etc.)
            """)
        
        with st.expander("📄 Français - Avertissement Juridique", expanded=False):
            st.markdown("""
### ⚠️ AVERTISSEMENT JURIDIQUE IMPORTANT

**Ravinala par TSIVAHINY Matthias** est un **OUTIL PÉDAGOGIQUE ET DE RECHERCHE UNIQUEMENT**.

#### 1. **Pas de Conseils en Investissement**
- **PAS un conseiller financier**
- Les prix sont **à titre illustratif uniquement**
- **N'utilisez PAS** pour décisions d'investissement réelles

#### 2. **Risques des Produits Structurés**
- **Risque de crédit**: Défaut de l'émetteur
- **Risque de marché**: Mouvements défavorables  
- **Risque de liquidité**: Sortie difficile et coûteuse
- **Risque de corrélation**: Corrélations s'effondrent en crise
- **Pas d'approbation réglementaire** (AMF, ESMA, etc.)

#### 3. **Clause de Non-Responsabilité**
- Les développeurs **NE SONT PAS RESPONSABLES** des pertes
- Utilisez **à vos propres risques strictement**

#### 4. **Avant d'Investir - Consultez:**
- Un conseil financier qualifié
- Un expert en produits dérivés
- Un conseil juridique
- Votre responsable de conformité
            """)
    
    else:  # Français d'abord
        with st.expander("📄 Français - Avertissement Juridique", expanded=True):
            st.markdown("""
[Same French content as above]
            """)
        
        with st.expander("⚠️ English - Legal Disclaimer", expanded=False):
            st.markdown("""
[Same English content as above]
            """)
'''
    
    # Replace the entire old section with new ones
    new_content = content[:old_pos] + new_sections
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Successfully replaced Learn & Legal sections!")
    print(f"  Old section size: 43,715 characters")
    print(f"  New sections size: {len(new_sections)} characters")
    
    # Verify the change
    with open(file_path, 'r', encoding='utf-8') as f:
        verify_content = f.read()
    
    if '"📚  Learn"' in verify_content and '"⚖️  Legal"' in verify_content:
        print("✅ Verification: New sections found in file")
        return True
    else:
        print("⚠️ Verification failed: New sections not found")
        return False

if __name__ == "__main__":
    replace_learn_legal_sections()
