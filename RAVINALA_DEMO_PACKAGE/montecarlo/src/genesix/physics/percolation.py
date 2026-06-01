"""
Financial contagion as an epidemic — the Financial R₀.

SIR model (Susceptible-Infected-Recovered) applied to financial assets.
Each asset "infects" others through correlation-based exposure.
The R₀ (basic reproduction number) tells us if cascades are self-sustaining.

Percolation theory: there exists a CRITICAL connectivity threshold above which
localized shocks propagate system-wide.
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional, Dict, List
from collections import deque

logger = logging.getLogger(__name__)


class FinancialEpidemic:
    """SIR-inspired model for financial contagion."""
    
    def __init__(self, stress_threshold: float = 2.0):
        """Initialize epidemic model."""
        self.stress_threshold = stress_threshold
    
    def classify_assets(self, asset_returns: Dict[str, np.ndarray],
                       recent_window: int = 5) -> dict:
        """
        Classify assets into SIR categories.
        
        Susceptible: not currently stressed
        Infected: currently in stress (vol > threshold × historical avg)
        Recovered: was stressed but recovering
        """
        susceptible = []
        infected = []
        recovered = []
        
        for asset, returns in asset_returns.items():
            returns_clean = returns[~np.isnan(returns) & ~np.isinf(returns)]
            
            if len(returns_clean) < recent_window:
                susceptible.append(asset)
                continue
            
            recent_vol = np.std(returns_clean[-recent_window:])
            hist_vol = np.std(returns_clean[-252:]) if len(returns_clean) >= 252 else recent_vol
            
            if hist_vol == 0:
                susceptible.append(asset)
                continue
            
            vol_ratio = recent_vol / hist_vol
            
            if vol_ratio > self.stress_threshold:
                infected.append(asset)
            elif vol_ratio < (self.stress_threshold * 0.6) and len(recovered) > 0:
                recovered.append(asset)
            else:
                susceptible.append(asset)
        
        infection_rate = len(infected) / (len(susceptible) + len(infected) + len(recovered) + 1e-10)
        
        return {
            'susceptible': susceptible,
            'infected': infected,
            'recovered': recovered,
            'infection_rate': float(infection_rate),
            'total_assets': len(susceptible) + len(infected) + len(recovered),
        }
    
    def compute_R0(self, asset_returns: Dict[str, np.ndarray], 
                   lookback_days: int = 252) -> dict:
        """
        Compute Financial R₀ via historical infection tracking.
        
        For each infection event: count secondary infections within 5 days.
        R₀ = average number of secondary infections per primary.
        """
        returns_array = {}
        for asset, ret in asset_returns.items():
            ret_clean = ret[~np.isnan(ret) & ~np.isinf(ret)]
            if len(ret_clean) > 0:
                returns_array[asset] = ret_clean[-lookback_days:]
        
        if not returns_array:
            return self._empty_R0()
        
        if not all(len(r) == len(next(iter(returns_array.values()))) for r in returns_array.values()):
            # Pad to same length
            min_len = min(len(r) for r in returns_array.values())
            returns_array = {k: v[-min_len:] for k, v in returns_array.items()}
        
        # Detect infection events (vol spikes)
        infection_events = []
        
        for asset, returns in returns_array.items():
            vol_hist = np.std(returns)
            if vol_hist == 0:
                continue
            
            for i in range(1, len(returns)):
                recent_vol = np.abs(returns[i])
                if recent_vol > self.stress_threshold * vol_hist:
                    infection_events.append({'asset': asset, 'day': i})
        
        if not infection_events:
            return self._empty_R0()
        
        # For each infection event, count secondary infections in next 5 days
        secondary_infection_counts = []
        
        for event in infection_events:
            asset = event['asset']
            day = event['day']
            
            secondary_count = 0
            for other_asset, returns in returns_array.items():
                if other_asset == asset:
                    continue
                
                vol_hist = np.std(returns)
                if vol_hist == 0:
                    continue
                
                # Check for infections in this other asset in next 5 days
                for future_day in range(day + 1, min(day + 6, len(returns))):
                    if np.abs(returns[future_day]) > self.stress_threshold * vol_hist:
                        secondary_count += 1
                        break  # Count once per asset
            
            if secondary_count > 0:
                secondary_infection_counts.append(secondary_count)
        
        # Compute R₀
        if secondary_infection_counts:
            R0 = np.mean(secondary_infection_counts)
        else:
            R0 = 0.5  # Low baseline if no secondary infections
        
        # Effective R₀ (adjusted for current immunity)
        classification = self.classify_assets(asset_returns)
        immunity_fraction = len(classification['recovered']) / (classification['total_assets'] + 1e-10)
        R0_effective = R0 * (1 - immunity_fraction)
        
        # Status interpretation
        if R0 < 0.5:
            status = "VERY LOW — shocks are well-contained."
        elif R0 < 1.0:
            status = "MODERATE — shocks spread but fade naturally."
        elif R0 < 2.0:
            status = "HIGH — cascades can self-sustain."
        else:
            status = "CRITICAL — systemic crisis conditions."
        
        return {
            'R0': float(R0),
            'R0_effective': float(R0_effective),
            'is_supercritical': R0 > 1.0,
            'n_infection_events': len(infection_events),
            'status': status,
            'trend': 'increasing' if R0 > 1.5 else ('decreasing' if R0 < 0.5 else 'stable'),
        }
    
    def simulate_epidemic(self, asset_returns: Dict[str, np.ndarray],
                         trigger_asset: str, n_simulations: int = 1000) -> dict:
        """
        Monte Carlo epidemic simulation.
        """
        # Build correlation network
        assets = list(asset_returns.keys())
        n_assets = len(assets)
        
        if trigger_asset not in assets:
            return {'error': f'{trigger_asset} not in asset list'}
        
        # Compute correlation matrix
        returns_df = pd.DataFrame(asset_returns)
        corr_matrix = returns_df.corr().values
        corr_matrix[np.isnan(corr_matrix)] = 0
        
        # Run simulations
        infected_counts = []
        peak_days = []
        durations = []
        
        for sim in range(n_simulations):
            # Initialize
            infected = {trigger_asset}
            susceptible = set(assets) - {trigger_asset}
            recovered = set()
            
            day = 0
            max_days = 60
            peak_infected = 1
            
            while infected and day < max_days:
                day += 1
                
                # Spread to new assets
                new_infections = set()
                for inf_asset in infected:
                    inf_idx = assets.index(inf_asset)
                    
                    for susc_asset in susceptible:
                        susc_idx = assets.index(susc_asset)
                        
                        # Infection probability based on correlation
                        correlation = abs(corr_matrix[inf_idx, susc_idx])
                        recovery_prob = 0.1  # 10% recover per day
                        
                        spread_prob = correlation * (1 - recovery_prob)
                        if np.random.random() < spread_prob:
                            new_infections.add(susc_asset)
                
                # Update states
                susceptible -= new_infections
                infected |= new_infections
                recovered.update(np.random.choice(list(infected), size=min(len(infected)//10, len(infected)), replace=False))
                infected -= recovered
                
                peak_infected = max(peak_infected, len(infected))
                
                if not infected:
                    durations.append(day)
                    peak_days.append(day)
                    break
            
            if infected:  # Hit max_days
                durations.append(max_days)
                peak_days.append(max_days // 2)
            
            infected_counts.append(peak_infected)
        
        # Statistics
        median_infected = np.median(infected_counts)
        mean_infected = np.mean(infected_counts)
        p_systemic = np.mean(np.array(infected_counts) > n_assets * 0.5)
        p_contained = np.mean(np.array(infected_counts) < n_assets * 0.1)
        
        herd_immunity_threshold = 1 - (1 / (self.compute_R0(asset_returns).get('R0', 1)))
        
        return {
            'trigger': trigger_asset,
            'n_simulations': n_simulations,
            'median_infected': int(median_infected),
            'mean_infected': float(mean_infected),
            'p_systemic': float(p_systemic),
            'p_contained': float(p_contained),
            'expected_peak_day': int(np.median(peak_days)) if peak_days else 0,
            'expected_duration_days': int(np.median(durations)) if durations else 0,
            'distribution_of_outcomes': np.array(infected_counts),
            'herd_immunity_threshold': float(herd_immunity_threshold),
        }
    
    def percolation_threshold(self, asset_returns: Dict[str, np.ndarray]) -> dict:
        """
        Compute percolation threshold of the financial network.
        
        Below threshold: shocks stay local.
        Above threshold: shocks propagate system-wide.
        """
        # Build correlation network
        returns_df = pd.DataFrame(asset_returns)
        assets = list(asset_returns.keys())
        
        # Test different correlation thresholds
        correlations = returns_df.corr().values
        abs_correlations = np.abs(correlations)
        
        # Remove diagonals
        np.fill_diagonal(abs_correlations, 0)
        
        # Flatten and sort
        flat_corr = abs_correlations[abs_correlations > 0]
        sorted_corr = np.sort(flat_corr)[::-1]  # Descending
        
        if len(sorted_corr) == 0:
            return self._empty_percolation()
        
        # Test percolation at different thresholds
        n_assets = len(assets)
        best_threshold = None
        giant_component_size = 0
        
        for threshold in np.linspace(0, 1, 50):
            # Build network at this threshold
            network = abs_correlations >= threshold
            
            # Find connected components
            visited = set()
            components = []
            
            for i in range(n_assets):
                if i in visited:
                    continue
                
                # BFS
                component = set()
                queue = deque([i])
                
                while queue:
                    node = queue.popleft()
                    if node in visited:
                        continue
                    
                    visited.add(node)
                    component.add(node)
                    
                    for j in range(n_assets):
                        if j not in visited and network[node, j]:
                            queue.append(j)
                
                components.append(component)
            
            # Largest component
            largest = max(len(c) for c in components) if components else 0
            
            if largest > giant_component_size:
                giant_component_size = largest
                best_threshold = threshold
        
        # Are we above threshold?
        current_avg_corr = np.mean(flat_corr) if len(flat_corr) > 0 else 0
        above_threshold = current_avg_corr > (best_threshold or 0.3)
        
        fragmentation = len([c for c in components if len(c) < 3]) / (len(components) + 1e-10)
        
        return {
            'percolation_threshold': float(best_threshold or 0.5),
            'current_avg_correlation': float(current_avg_corr),
            'above_threshold': above_threshold,
            'giant_component_size': float(giant_component_size / n_assets),
            'fragmentation': float(fragmentation),
            'interpretation': self._percolation_interpretation(above_threshold, current_avg_corr, giant_component_size / n_assets),
        }
    
    def _percolation_interpretation(self, above: bool, corr: float, gc_size: float) -> str:
        """Generate percolation interpretation."""
        base = f"Avg correlation: {corr:.2f}. Giant component: {gc_size*100:.0f}% of assets. "
        
        if above and gc_size > 0.5:
            base += "SYSTEM IS PERCOLATING — a shock anywhere can cascade throughout."
        elif above:
            base += "Above percolation threshold — wide-ranging shocks are possible."
        else:
            base += "Below percolation threshold — shocks tend to stay localized."
        
        return base
    
    def _empty_R0(self) -> dict:
        return {
            'R0': 0.5, 'R0_effective': 0.3, 'is_supercritical': False,
            'n_infection_events': 0, 'status': 'VERY LOW',
            'trend': 'stable'
        }
    
    def _empty_percolation(self) -> dict:
        return {
            'percolation_threshold': 0.5, 'current_avg_correlation': 0,
            'above_threshold': False, 'giant_component_size': 0,
            'fragmentation': 1.0, 'interpretation': 'Insufficient data'
        }
