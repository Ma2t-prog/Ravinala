import { useState, useMemo } from 'react'
import { Card } from '../../components/ui/Card'
import { useHealth } from '../../hooks/useMarketData'

// ─── Theme ───────────────────────────────────────────────────────────────────
const AMBER = '#F59E0B'
const BG = '#0A0E1A'
const ELEVATED = '#1A2332'
const TEXT = '#F1F5F9'
const MUTED = '#94A3B8'
const MONO = 'JetBrains Mono, monospace'
const SANS = 'Inter, system-ui, sans-serif'

// ─── Categories & data ───────────────────────────────────────────────────────
type Category = 'All' | 'Path-Dependent' | 'Correlation' | 'Volatility' | 'Credit' | 'Hybrid'

const CATEGORIES: Category[] = ['All', 'Path-Dependent', 'Correlation', 'Volatility', 'Credit', 'Hybrid']

interface ExoticEntry {
  name: string
  category: Category
  complexity: number // 1-5
  description: string
  formula: string
  useCase: string
}

const EXOTICS_DATA: ExoticEntry[] = [
  {
    name: 'Asian',
    category: 'Path-Dependent',
    complexity: 2,
    description: 'Payoff depends on the average price of the underlying over a period. Reduces impact of price manipulation at expiry and smooths volatility exposure.',
    formula: 'max( (1/n) * sum(S_ti) - K, 0 )',
    useCase: 'Commodity hedging, corporate treasury FX exposure management where average rate matters.',
  },
  {
    name: 'Barrier',
    category: 'Path-Dependent',
    complexity: 2,
    description: 'Option activates (knock-in) or terminates (knock-out) when the underlying crosses a specified barrier. Available as up/down, in/out combinations.',
    formula: 'max(S-K, 0) * 1{path condition}',
    useCase: 'Cheaper alternative to vanilla options for directional views. Popular in FX structured notes.',
  },
  {
    name: 'Lookback',
    category: 'Path-Dependent',
    complexity: 3,
    description: 'Allows holder to exercise at the most favorable price observed during the option life. Floating strike uses min/max as strike; fixed strike uses max/min as terminal.',
    formula: 'Floating: S_T - min(S_t) | Fixed: max(max(S_t) - K, 0)',
    useCase: 'Timing-sensitive investments, fund insurance products where hindsight value is desired.',
  },
  {
    name: 'Chooser',
    category: 'Path-Dependent',
    complexity: 3,
    description: 'At a specified date before expiry, the holder chooses whether the option is a call or a put. Provides flexibility when direction is uncertain but a move is expected.',
    formula: 'max( C(S, K, T-t_c), P(S, K, T-t_c) ) at choice date t_c',
    useCase: 'Pre-event hedging (earnings, elections) where direction is unknown but volatility is expected.',
  },
  {
    name: 'Compound',
    category: 'Path-Dependent',
    complexity: 4,
    description: 'An option on an option. The holder has the right to buy/sell another option at a future date for a specified premium. Four types: call-on-call, call-on-put, put-on-call, put-on-put.',
    formula: 'max( C_inner(S, K2, T2) - K1, 0 ) at T1',
    useCase: 'Corporate M&A contingent hedging, phased project financing where hedge may not be needed.',
  },
  {
    name: 'Rainbow',
    category: 'Correlation',
    complexity: 3,
    description: 'Depends on multiple underlying assets. Best-of, worst-of, and spread options are common variants. Correlation between assets is the key pricing driver.',
    formula: 'Best-of: max(S1-K, S2-K, 0) | Spread: max(S1-S2-K, 0)',
    useCase: 'Multi-asset portfolio protection, relative value trades between correlated assets.',
  },
  {
    name: 'Quanto',
    category: 'Correlation',
    complexity: 3,
    description: 'Payoff is in a different currency than the underlying, with a fixed exchange rate. Eliminates FX risk from cross-border investments.',
    formula: 'Q * max(S-K, 0) where Q is fixed FX rate',
    useCase: 'Cross-border equity investments, foreign index-linked structured products for domestic investors.',
  },
  {
    name: 'Himalaya',
    category: 'Correlation',
    complexity: 5,
    description: 'Multi-asset, multi-period option. Each period, the best-performing asset is locked in and removed. Final payoff is the average of locked-in returns.',
    formula: 'Payoff = avg( R_best(t1), R_best(t2), ..., R_best(tn) )',
    useCase: 'Structured products for retail investors seeking diversified equity exposure with participation.',
  },
  {
    name: 'Everest',
    category: 'Correlation',
    complexity: 5,
    description: 'Pays out based on the worst-performing asset in a large basket (10-25 assets) over a long tenor. Named for the "peak" difficulty of the correlation modeling.',
    formula: 'Payoff = max( min(R_i for all i) + spread, 0 )',
    useCase: 'Long-dated structured notes offering enhanced yield in exchange for worst-of risk on diversified baskets.',
  },
  {
    name: 'Atlas',
    category: 'Correlation',
    complexity: 4,
    description: 'Like a Himalaya but removes both the best and worst performers each period, averaging only the middle performers. Reduces tail risk exposure.',
    formula: 'Payoff = avg( trimmed returns per period )',
    useCase: 'Structured products seeking to reduce dispersion risk while maintaining multi-asset exposure.',
  },
  {
    name: 'Napoleon',
    category: 'Correlation',
    complexity: 4,
    description: 'Each period, the worst-performing asset determines the return (floored at some level). Opposite of Himalaya — locks in worst rather than best.',
    formula: 'Payoff = sum( max(floor, R_worst(ti)) ) per period',
    useCase: 'Yield enhancement products for investors comfortable with worst-of correlation risk.',
  },
  {
    name: 'Cliquet',
    category: 'Path-Dependent',
    complexity: 4,
    description: 'Series of forward-starting options with periodic resets. Each period return is floored and capped, then summed. Sensitive to forward volatility smile.',
    formula: 'Payoff = N * sum( min(cap, max(floor, R_i)) )',
    useCase: 'Insurance-linked equity participation, guaranteed minimum return products.',
  },
  {
    name: 'Ratchet',
    category: 'Path-Dependent',
    complexity: 3,
    description: 'Similar to a cliquet but the strike ratchets up to the previous period high. Locks in gains over time, providing a form of profit-taking mechanism.',
    formula: 'Strike_i = max(Strike_{i-1}, S_{t_i}); Payoff = sum(max(S_{t_i} - Strike_{i-1}, 0))',
    useCase: 'Long-term savings products, pension-linked investments with periodic lock-in of gains.',
  },
  {
    name: 'Accumulator',
    category: 'Path-Dependent',
    complexity: 4,
    description: 'Obligates the holder to buy (accumulate) shares at a discount on each fixing date, but at double quantity below a knock-in barrier. Can knock out above an upper barrier.',
    formula: 'Daily: Buy N shares at K if B_low < S < B_up; Buy 2N if S < B_low; KO if S > B_up',
    useCase: 'Equity-linked structured products in Asia. Known as "I kill you later" due to unlimited downside.',
  },
  {
    name: 'TARF',
    category: 'Path-Dependent',
    complexity: 4,
    description: 'Target Accrual Redemption Forward. Series of FX forwards that terminate once cumulative gains reach a target level. Asymmetric — losses are not capped.',
    formula: 'Each fixing: gain = max(K-S, 0); loss = max(S-K, 0)*L; terminates when sum(gains) >= Target',
    useCase: 'FX hedging for corporates, popular in Asian FX markets for USD/CNH and USD/KRW.',
  },
  {
    name: 'Variance Swap',
    category: 'Volatility',
    complexity: 3,
    description: 'Swap that pays the difference between realized and implied (strike) variance. Linear exposure to variance (quadratic to volatility). Model-free replication via options strip.',
    formula: 'Payoff = N_var * (sigma_realized^2 - K_var)',
    useCase: 'Pure volatility trading, hedging vega risk, portfolio insurance.',
  },
  {
    name: 'Volatility Swap',
    category: 'Volatility',
    complexity: 4,
    description: 'Similar to variance swap but pays on realized volatility directly. Harder to replicate because volatility is the square root of variance (convexity adjustment needed).',
    formula: 'Payoff = N_vol * (sigma_realized - K_vol)',
    useCase: 'Direct volatility trading when linear vol exposure is preferred over convex variance exposure.',
  },
  {
    name: 'Corridor',
    category: 'Path-Dependent',
    complexity: 3,
    description: 'Accrues value for each day the underlying stays within a specified range (corridor). Also called a range accrual in rates markets.',
    formula: 'Payoff = N * (days_in_corridor / total_days) * coupon',
    useCase: 'Yield enhancement in low-volatility environments, range-bound market views.',
  },
  {
    name: 'Range Accrual',
    category: 'Hybrid',
    complexity: 3,
    description: 'Pays an enhanced coupon that accrues only on days when a reference rate or asset stays within bounds. Combines fixed income with exotic features.',
    formula: 'Coupon = enhanced_rate * (fixing_days_in_range / total_fixing_days)',
    useCase: 'Structured notes for yield-seeking investors, interest rate products in stable rate environments.',
  },
  {
    name: 'Power Option',
    category: 'Path-Dependent',
    complexity: 3,
    description: 'Payoff is based on the underlying raised to a power. Amplifies returns but also risk. Symmetric or asymmetric power structures available.',
    formula: 'Payoff = max(S^p - K, 0) or max(S - K, 0)^p',
    useCase: 'Leveraged directional bets, structured products requiring convex payoff amplification.',
  },
  {
    name: 'Gap Option',
    category: 'Credit',
    complexity: 2,
    description: 'Has two strikes: a trigger strike (determines if in-the-money) and a payment strike (determines payoff amount). Can produce negative payoffs for the holder.',
    formula: 'Payoff = (S - K1) * 1{S > K2} where K1 is payment, K2 is trigger',
    useCase: 'Insurance products, credit-linked structures where trigger and payment levels differ.',
  },
  {
    name: 'Shout Option',
    category: 'Path-Dependent',
    complexity: 3,
    description: 'Holder can "shout" once during the life to lock in the intrinsic value at that moment. At expiry, receives the maximum of the locked value or the terminal payoff.',
    formula: 'Payoff = max( max(S_shout - K, 0), max(S_T - K, 0) )',
    useCase: 'Employee stock options, situations where partial profit-taking is desired without exercising.',
  },
  {
    name: 'Ladder Option',
    category: 'Path-Dependent',
    complexity: 3,
    description: 'Has predefined rungs (price levels). When the spot crosses a rung, the minimum payoff is locked in at that level. Provides automatic profit-taking.',
    formula: 'Payoff = max( max(rungs crossed) - K, max(S_T - K, 0) )',
    useCase: 'Retail structured products providing automatic gain locking, participation certificates.',
  },
  {
    name: 'Parisian Option',
    category: 'Path-Dependent',
    complexity: 5,
    description: 'Like a barrier option, but the barrier is only triggered if the underlying stays beyond the barrier for a consecutive specified duration (window). Prevents false triggers.',
    formula: 'Like barrier but requires consecutive time d beyond B: max(S-K,0) * 1{max consecutive time beyond B >= d}',
    useCase: 'More robust than standard barriers for hedging, less susceptible to short-term barrier breach.',
  },
]

// ─── Stars component ─────────────────────────────────────────────────────────
function Stars({ count }: { count: number }) {
  return (
    <span style={{ fontFamily: SANS, letterSpacing: 2 }}>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} style={{ color: i < count ? AMBER : 'rgba(51,65,85,0.6)', fontSize: 14 }}>
          &#9733;
        </span>
      ))}
    </span>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function MuseumExotics() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<Category>('All')
  const [expanded, setExpanded] = useState<string | null>(null)
  const { data: healthData, isError: healthError } = useHealth()
  const backendOnline = !!healthData && !healthError

  const filtered = useMemo(() => {
    return EXOTICS_DATA.filter(e => {
      const matchesSearch = search === '' ||
        e.name.toLowerCase().includes(search.toLowerCase()) ||
        e.description.toLowerCase().includes(search.toLowerCase())
      const matchesCategory = category === 'All' || e.category === category
      return matchesSearch && matchesCategory
    })
  }, [search, category])

  return (
    <div style={{ background: BG, minHeight: '100vh', padding: 24, fontFamily: SANS }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ fontFamily: MONO, fontSize: 26, color: TEXT, margin: 0 }}>
            <span style={{ color: AMBER }}>&#9670;</span> Museum of Exotic Derivatives
          </h1>
          <span
            title={backendOnline ? 'Backend connected' : 'Backend offline'}
            style={{
              display: 'inline-block',
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: backendOnline ? '#10B981' : '#EF4444',
              boxShadow: backendOnline ? '0 0 6px rgba(16,185,129,0.5)' : '0 0 6px rgba(239,68,68,0.5)',
              flexShrink: 0,
            }}
          />
        </div>
        <p style={{ color: MUTED, fontSize: 14, marginTop: 4 }}>
          An encyclopedia of {EXOTICS_DATA.length} exotic derivative instruments
        </p>
      </div>

      {/* Search & Filter bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          style={{
            backgroundColor: ELEVATED,
            border: '1px solid rgba(51,65,85,0.5)',
            borderRadius: 6,
            padding: '8px 14px',
            color: TEXT,
            fontFamily: SANS,
            fontSize: 13,
            width: 280,
            outline: 'none',
          }}
          placeholder="Search derivatives..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              style={{
                padding: '6px 14px',
                borderRadius: 6,
                border: category === cat ? `1px solid ${AMBER}` : '1px solid rgba(51,65,85,0.4)',
                background: category === cat ? 'rgba(245,158,11,0.12)' : 'transparent',
                color: category === cat ? AMBER : MUTED,
                fontFamily: SANS,
                fontSize: 12,
                fontWeight: category === cat ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {cat}
            </button>
          ))}
        </div>
        <span style={{ color: MUTED, fontSize: 12, marginLeft: 'auto' }}>
          {filtered.length} / {EXOTICS_DATA.length} instruments
        </span>
      </div>

      {/* List of exotics */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filtered.map(exotic => {
          const isExpanded = expanded === exotic.name
          return (
            <div
              key={exotic.name}
              style={{
                background: isExpanded ? ELEVATED : ELEVATED,
                border: isExpanded ? `1px solid rgba(245,158,11,0.3)` : '1px solid rgba(51,65,85,0.3)',
                borderRadius: 8,
                overflow: 'hidden',
                transition: 'all 0.2s',
              }}
            >
              {/* Header row */}
              <button
                onClick={() => setExpanded(isExpanded ? null : exotic.name)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  padding: '14px 18px',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                <span style={{
                  color: AMBER,
                  fontSize: 12,
                  transition: 'transform 0.2s',
                  transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                  display: 'inline-block',
                }}>
                  &#9654;
                </span>
                <span style={{ color: TEXT, fontSize: 14, fontWeight: 600, fontFamily: SANS, minWidth: 140 }}>
                  {exotic.name}
                </span>
                <span style={{
                  padding: '2px 10px',
                  borderRadius: 10,
                  background: 'rgba(245,158,11,0.1)',
                  color: AMBER,
                  fontSize: 11,
                  fontFamily: SANS,
                  whiteSpace: 'nowrap',
                }}>
                  {exotic.category}
                </span>
                <Stars count={exotic.complexity} />
                <span style={{ color: MUTED, fontSize: 12, fontFamily: SANS, flex: 1 }}>
                  {exotic.description.slice(0, 100)}...
                </span>
              </button>

              {/* Expanded detail */}
              {isExpanded && (
                <div style={{ padding: '0 18px 18px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <Card title="Description">
                    <p style={{ color: TEXT, fontSize: 13, lineHeight: 1.7, margin: 0 }}>
                      {exotic.description}
                    </p>
                  </Card>

                  <Card title="Payoff Formula">
                    <pre style={{
                      color: AMBER,
                      fontFamily: MONO,
                      fontSize: 12,
                      lineHeight: 1.8,
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}>
                      {exotic.formula}
                    </pre>
                  </Card>

                  <Card title="Use Case">
                    <p style={{ color: TEXT, fontSize: 13, lineHeight: 1.7, margin: 0 }}>
                      {exotic.useCase}
                    </p>
                  </Card>

                  <Card title="Complexity Rating">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <Stars count={exotic.complexity} />
                      <span style={{ color: MUTED, fontSize: 12 }}>
                        {exotic.complexity === 1 && 'Simple — vanilla-like pricing'}
                        {exotic.complexity === 2 && 'Standard — closed-form or standard PDE'}
                        {exotic.complexity === 3 && 'Moderate — requires careful numerical methods'}
                        {exotic.complexity === 4 && 'Complex — Monte Carlo or advanced PDE solvers'}
                        {exotic.complexity === 5 && 'Highly complex — multi-factor MC, model risk'}
                      </span>
                    </div>
                    <div style={{
                      marginTop: 12,
                      height: 6,
                      background: 'rgba(51,65,85,0.3)',
                      borderRadius: 3,
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${exotic.complexity * 20}%`,
                        background: exotic.complexity <= 2 ? '#10B981' : exotic.complexity <= 3 ? AMBER : '#EF4444',
                        borderRadius: 3,
                        transition: 'width 0.3s',
                      }} />
                    </div>
                  </Card>
                </div>
              )}
            </div>
          )
        })}

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: MUTED }}>
            No exotic derivatives match your search criteria.
          </div>
        )}
      </div>
    </div>
  )
}
