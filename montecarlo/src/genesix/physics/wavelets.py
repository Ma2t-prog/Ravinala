"""
Wavelet analysis — seeing the market at every time scale simultaneously.

Wavelets decompose signals into TIME AND FREQUENCY simultaneously,
revealing hidden relationships that Fourier analysis misses.

Financial applications:
1. Denoise prices (remove high-frequency noise)
2. Multi-scale correlation (decorrelated at daily, correlated at monthly)
3. Regime detection (energy shifts between scales during transitions)
"""

import numpy as np
import pandas as pd
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False
    logger.warning("PyWavelets not installed. Wavelet analysis will be limited.")


class WaveletAnalyzer:
    """Wavelet decomposition for financial time series."""
    
    def __init__(self, wavelet: str = 'db4'):
        """Initialize with Daubechies-4 wavelet (good for finance)."""
        self.wavelet = wavelet
        self.has_pywt = HAS_PYWT
    
    def decompose(self, series: pd.Series, wavelet: Optional[str] = None,
                  level: Optional[int] = None) -> dict:
        """
        Multi-level wavelet decomposition.
        
        Decomposes price into trend (low-freq) and details at each scale:
        - D1 (2-4 days): noise
        - D2 (4-8 days): weekly
        - D3 (8-16 days): bi-weekly
        - D4 (16-32 days): monthly
        - D5 (32-64 days): quarterly
        - D6 (64-128 days): semi-annual
        - A6: trend (> 128 days)
        """
        if not HAS_PYWT:
            return self._empty_decomposition()
        
        wavelet = wavelet or self.wavelet
        series_array = series.values
        
        # Remove NaN
        series_clean = series_array[~np.isnan(series_array)]
        
        if len(series_clean) < 64:
            return self._empty_decomposition()
        
        # Decompose
        level = level or pywt.dwt_max_level(len(series_clean), wavelet)
        level = min(level, 6)  # Cap at 6 levels
        
        try:
            coeffs = pywt.wavedec(series_clean, wavelet, level=level)
        except Exception as e:
            logger.debug(f"Wavelet decomposition failed: {e}")
            return self._empty_decomposition()
        
        # Reconstruct each component
        approximation = pywt.waverec([coeffs[0]] + [None] * (level), wavelet, mode='period')
        details = {}
        
        for i in range(1, len(coeffs)):
            coeff_list = [None] + [None] * (i - 1) + [coeffs[i]] + [None] * (level - i)
            detail = pywt.waverec(coeff_list, wavelet, mode='period')
            
            if detail is not None:
                # Trim to match original length
                detail = detail[:len(series_clean)]
                
                scale_name = f'D{i}'
                if i == 1:
                    scale_label = 'D1_2_4d'
                elif i == 2:
                    scale_label = 'D2_4_8d'
                elif i == 3:
                    scale_label = 'D3_8_16d'
                elif i == 4:
                    scale_label = 'D4_16_32d'
                elif i == 5:
                    scale_label = 'D5_32_64d'
                else:
                    scale_label = f'D{i}'
                
                details[scale_label] = pd.Series(detail, index=series.index[-len(detail):])
        
        approximation = approximation[:len(series_clean)]
        approximation_series = pd.Series(approximation, index=series.index[-len(approximation):])
        
        # Energy distribution
        energy = {}
        total_energy = np.var(series_clean)
        
        for i, d in enumerate(coeffs[1:], 1):
            if len(d) > 0:
                energy[f'D{i}'] = np.var(d) / (total_energy + 1e-10)
        
        energy['A6'] = np.var(approximation) / (total_energy + 1e-10)
        
        # Reconstruction error
        try:
            reconstructed = pywt.waverec(coeffs, wavelet, mode='period')[:len(series_clean)]
            recon_error = np.mean((series_clean - reconstructed) ** 2)
        except:
            recon_error = 0
        
        return {
            'original': series,
            'trend': approximation_series,
            'details': details,
            'energy_distribution': energy,
            'dominant_scale': max(energy, key=energy.get) if energy else 'unknown',
            'reconstruction_error': float(recon_error),
        }
    
    def denoise(self, series: pd.Series, remove_levels: list[int] = [1]) -> pd.Series:
        """Denoise by removing high-frequency components."""
        if not HAS_PYWT:
            return series
        
        series_array = series.values
        series_clean = series_array[~np.isnan(series_array)]
        
        try:
            level = pywt.dwt_max_level(len(series_clean), self.wavelet)
            level = min(level, 6)
            
            coeffs = pywt.wavedec(series_clean, self.wavelet, level=level)
            
            # Zero out detail coefficients at specified levels
            for lev in remove_levels:
                if lev < len(coeffs):
                    coeffs[lev] = np.zeros_like(coeffs[lev])
            
            denoised = pywt.waverec(coeffs, self.wavelet, mode='period')
            denoised = denoised[:len(series_clean)]
            
            return pd.Series(denoised, index=series.index[-len(denoised):])
        
        except Exception as e:
            logger.debug(f"Denoising failed: {e}")
            return series
    
    def multiscale_correlation(self, series1: pd.Series, series2: pd.Series) -> dict:
        """Correlation between two assets at each time scale."""
        if not HAS_PYWT:
            return {}
        
        decomp1 = self.decompose(series1)
        decomp2 = self.decompose(series2)
        
        if not decomp1.get('details') or not decomp2.get('details'):
            return {}
        
        by_scale = {}
        
        for scale in decomp1['details'].keys():
            if scale not in decomp2['details']:
                continue
            
            d1 = decomp1['details'][scale].values
            d2 = decomp2['details'][scale].values
            
            # Align lengths
            min_len = min(len(d1), len(d2))
            d1 = d1[-min_len:]
            d2 = d2[-min_len:]
            
            if min_len > 2:
                corr = np.corrcoef(d1, d2)[0, 1]
                if np.isnan(corr):
                    corr = 0
            else:
                corr = 0
            
            label = 'high_freq' if '1_2_4d' in scale else ('weekly' if '2_4_8d' in scale else 'other')
            
            by_scale[scale] = {
                'correlation': float(corr),
                'label': label,
            }
        
        # Trend correlation
        trend_corr = 0
        if 'trend' in decomp1 and 'trend' in decomp2:
            t1, t2 = decomp1['trend'].values, decomp2['trend'].values
            min_len = min(len(t1), len(t2))
            if min_len > 2:
                trend_corr = np.corrcoef(t1[-min_len:], t2[-min_len:])[0, 1]
                if np.isnan(trend_corr):
                    trend_corr = 0
        
        by_scale['trend'] = {'correlation': float(trend_corr), 'label': 'long_term'}
        
        # Overall correlation
        overall = np.corrcoef(series1.values[~np.isnan(series1.values)], 
                             series2.values[~np.isnan(series2.values)])[0, 1]
        if np.isnan(overall):
            overall = 0
        
        return {
            'overall_correlation': float(overall),
            'by_scale': by_scale,
            'diversification_by_horizon': self._diversification_assessment(by_scale),
        }
    
    def wavelet_variance(self, series: pd.Series) -> dict:
        """Wavelet variance at each scale."""
        decomp = self.decompose(series)
        
        if not decomp.get('energy_distribution'):
            return {}
        
        energy = decomp['energy_distribution']
        total = sum(energy.values())
        
        if total == 0:
            return {}
        
        pct_noise = energy.get('D1', 0) / total
        pct_weekly = (energy.get('D2', 0) + energy.get('D3', 0)) / total
        pct_monthly = (energy.get('D4', 0) + energy.get('D5', 0)) / total
        pct_trend = energy.get('A6', 0) / total
        
        pct_signal = pct_weekly + pct_monthly + pct_trend
        signal_to_noise = pct_signal / max(pct_noise, 0.01)
        
        return {
            'by_scale': energy,
            'total_variance': float(np.var(series.values[~np.isnan(series.values)])),
            'pct_trend': float(pct_trend * 100),
            'pct_cycles': float((pct_weekly + pct_monthly) * 100),
            'pct_noise': float(pct_noise * 100),
            'signal_to_noise': float(signal_to_noise),
        }
    
    def _diversification_assessment(self, by_scale: dict) -> dict:
        """Assess diversification benefit at each horizon."""
        assessment = {
            'intraweek': 'effective' if by_scale.get('D1_2_4d', {}).get('correlation', 0) < 0.3 else 'ineffective',
            'weekly': 'effective' if by_scale.get('D3_8_16d', {}).get('correlation', 0) < 0.3 else 'ineffective',
            'monthly': 'effective' if by_scale.get('D4_16_32d', {}).get('correlation', 0) < 0.3 else 'ineffective',
        }
        
        return assessment
    
    def _empty_decomposition(self) -> dict:
        return {
            'original': pd.Series(),
            'trend': pd.Series(),
            'details': {},
            'energy_distribution': {},
            'dominant_scale': 'unknown',
            'reconstruction_error': np.inf,
        }
