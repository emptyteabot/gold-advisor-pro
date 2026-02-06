"""
Gold Advisor Pro™ v3.0
A股黄金日内多维策略引擎
整合：行情识别 + K线形态 + 7大策略投票 + 宏观过滤 + 多周期分析
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

import gold_config as cfg

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  数据结构
# ═══════════════════════════════════════════════════════════════
@dataclass
class TradeSignal:
    """交易信号"""
    code: str
    name: str
    direction: str          # 'BUY' / 'SELL' / 'HOLD'
    score: float            # -1.0 ~ +1.0
    confidence: float       # 0 ~ 1.0
    strategies: Dict        # 各策略子信号
    entry_price: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    reason: str = ''
    timestamp: datetime = field(default_factory=datetime.now)
    is_t0: bool = True
    urgency: str = 'NORMAL' # CRITICAL / HIGH / NORMAL / LOW
    regime: str = 'RANGE'   # 行情类型
    regime_desc: str = ''
    patterns: List = field(default_factory=list)  # K线形态
    macro_bias: float = 0   # 宏观偏向
    risk_reward: float = 0  # 盈亏比

    @property
    def score_pct(self) -> str:
        return f"{self.score:+.0%}"

    @property
    def confidence_pct(self) -> str:
        return f"{self.confidence:.0%}"


# ═══════════════════════════════════════════════════════════════
#  技术指标计算工具箱
# ═══════════════════════════════════════════════════════════════
class TechnicalIndicators:
    """技术指标工具箱"""

    @staticmethod
    def rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26,
             signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = (dif - dea) * 2
        return dif, dea, hist

    @staticmethod
    def bollinger_bands(series: pd.Series, period: int = 20,
                        std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        mid = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = mid + std_dev * std
        lower = mid - std_dev * std
        return upper, mid, lower

    @staticmethod
    def moving_averages(series: pd.Series,
                        periods: List[int] = None) -> Dict[str, pd.Series]:
        if periods is None:
            periods = [5, 10, 20, 60]
        return {f'MA{p}': series.rolling(window=p).mean() for p in periods}

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 14) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        avg_vol = volume.rolling(window=period).mean()
        return volume / avg_vol.replace(0, np.nan)

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
            n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        lowest_low = low.rolling(window=n).min()
        highest_high = high.rolling(window=n).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan) * 100
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d
        return k, d, j

    @staticmethod
    def wr(high: pd.Series, low: pd.Series, close: pd.Series,
           period: int = 14) -> pd.Series:
        """威廉指标"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        return (highest_high - close) / (highest_high - lowest_low).replace(0, np.nan) * -100

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """能量潮 OBV"""
        direction = np.where(close > close.shift(1), 1,
                    np.where(close < close.shift(1), -1, 0))
        return (volume * direction).cumsum()

    @staticmethod
    def slope(series: pd.Series, period: int = 16) -> pd.Series:
        """趋势斜率（线性回归）"""
        def _calc_slope(s):
            if len(s) < 2:
                return 0
            x = np.arange(len(s))
            try:
                m, _ = np.polyfit(x, s, 1)
                return m
            except Exception:
                return 0
        return series.rolling(window=period).apply(_calc_slope, raw=False)

    @staticmethod
    def parkinson_volatility(high: pd.Series, low: pd.Series,
                             period: int = 20) -> pd.Series:
        """帕金森波动率（比收盘价波动率更精确）"""
        hl_sq = (np.log(high / low)) ** 2
        return np.sqrt(hl_sq.rolling(window=period).mean() / (4 * np.log(2)))


# ═══════════════════════════════════════════════════════════════
#  行情识别器（来自 智能交易系统.py）
# ═══════════════════════════════════════════════════════════════
class RegimeDetector:
    """
    行情类型识别器

    TREND_UP   - 上涨趋势
    TREND_DOWN - 下跌趋势
    RANGE      - 震荡
    CRASH      - 暴跌中
    REVERSAL   - 暴跌后反弹（倒车接人时机）
    """

    def detect(self, df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 20:
            return {'regime': 'RANGE', 'confidence': 0.5,
                    'description': '数据不足', 'features': {}, 'similar_history': []}

        features = self._calculate_features(df)
        regime = self._classify(features)
        similar = self._find_similar_history(features)

        return {
            'regime': regime['type'],
            'confidence': regime['confidence'],
            'description': regime['description'],
            'features': features,
            'similar_history': similar,
        }

    def _calculate_features(self, df: pd.DataFrame) -> Dict:
        close = df['close']
        n = min(20, len(close))

        # 趋势斜率
        x = np.arange(n)
        slope_val, _ = np.polyfit(x, close.iloc[-n:].values, 1)
        trend_strength = slope_val / float(close.iloc[-1]) * 100

        # 波动率
        returns = close.pct_change()
        volatility = float(returns.iloc[-n:].std()) * np.sqrt(252)

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_s = 100 - (100 / (1 + rs))
        rsi_val = float(rsi_s.iloc[-1]) if not rsi_s.empty and not pd.isna(rsi_s.iloc[-1]) else 50

        # 高低点距离
        high_n = float(close.iloc[-n:].max())
        low_n = float(close.iloc[-n:].min())
        cur = float(close.iloc[-1])
        dist_high = (cur - high_n) / high_n * 100
        dist_low = (cur - low_n) / low_n * 100

        # 量比
        vol = df['volume'] if 'volume' in df.columns else pd.Series(dtype=float)
        vol_ratio = float(vol.iloc[-5:].mean() / vol.iloc[-n:].mean()) if len(vol) >= n else 1.0

        # 连续涨跌
        cons_down = cons_up = 0
        for i in range(-1, -min(10, len(close)), -1):
            if close.iloc[i] < close.iloc[i - 1]:
                cons_down += 1
            else:
                break
        for i in range(-1, -min(10, len(close)), -1):
            if close.iloc[i] > close.iloc[i - 1]:
                cons_up += 1
            else:
                break

        return {
            'trend_strength': trend_strength,
            'volatility': volatility,
            'rsi': rsi_val,
            'dist_from_high': dist_high,
            'dist_from_low': dist_low,
            'vol_ratio': vol_ratio,
            'consecutive_down': cons_down,
            'consecutive_up': cons_up,
            'current_price': cur,
            'high_n': high_n,
            'low_n': low_n,
        }

    def _classify(self, f: Dict) -> Dict:
        rsi = f['rsi']
        trend = f['trend_strength']
        dist_low = f['dist_from_low']
        cons_down = f['consecutive_down']
        cons_up = f['consecutive_up']
        vr = f['vol_ratio']

        # 暴跌后反弹（倒车接人！）
        if rsi < 35 and dist_low < 2 and cons_up >= 1:
            return {'type': 'REVERSAL',
                    'confidence': min(0.9, (35 - rsi) / 20 + 0.5),
                    'description': f'倒车接人！RSI={rsi:.0f} 超卖，距低点{dist_low:.1f}%'}

        # 暴跌中
        if rsi < 30 and cons_down >= 3 and vr > 1.5:
            return {'type': 'CRASH', 'confidence': 0.8,
                    'description': f'暴跌中，RSI={rsi:.0f}，连跌{cons_down}根'}

        # 上涨趋势
        if trend > 0.05 and 50 < rsi < 75:
            return {'type': 'TREND_UP',
                    'confidence': min(0.85, 0.5 + trend * 2),
                    'description': f'上涨趋势，RSI={rsi:.0f}'}

        # 下跌趋势
        if trend < -0.05 and 25 < rsi < 50:
            return {'type': 'TREND_DOWN',
                    'confidence': min(0.85, 0.5 + abs(trend) * 2),
                    'description': f'下跌趋势，RSI={rsi:.0f}'}

        return {'type': 'RANGE', 'confidence': 0.6,
                'description': f'震荡行情，RSI={rsi:.0f}'}

    @staticmethod
    def _find_similar_history(f: Dict) -> List[Dict]:
        """参考黄金历史重要时刻"""
        results = []
        rsi = f['rsi']

        if rsi < 35 and f['dist_from_low'] < 3:
            results.append({
                'period': '2020-03 疫情暴跌',
                'pattern': 'V型反弹',
                'outcome': '随后反弹30%',
                'similarity': 0.85,
                'advice': 'RSI超卖做多，目标15-20%',
            })
        if rsi > 70 and f['dist_from_high'] > -2:
            results.append({
                'period': '2022-03 俄乌冲突',
                'pattern': '高位横盘',
                'outcome': '随后回调15%',
                'similarity': 0.7,
                'advice': '谨慎追高，设好止损',
            })
        if 40 < rsi < 60 and abs(f['trend_strength']) < 0.02:
            results.append({
                'period': '2023-Q2 银行危机后',
                'pattern': '窄幅震荡蓄势',
                'outcome': '突破后快速拉升20%',
                'similarity': 0.65,
                'advice': '关注布林带突破方向',
            })
        return results


# ═══════════════════════════════════════════════════════════════
#  K线形态识别器（来自 倒车接人.py）
# ═══════════════════════════════════════════════════════════════
class CandlestickPatterns:
    """K线形态识别"""

    @staticmethod
    def detect_all(df: pd.DataFrame) -> List[Dict]:
        """检测所有K线形态"""
        if df is None or len(df) < 3:
            return []

        patterns = []
        o, h, l, c = (float(df['open'].iloc[-1]), float(df['high'].iloc[-1]),
                       float(df['low'].iloc[-1]), float(df['close'].iloc[-1]))
        body = abs(c - o)
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        total_range = h - l if h != l else 0.0001

        o2 = float(df['open'].iloc[-2])
        c2 = float(df['close'].iloc[-2])
        body2 = abs(c2 - o2)

        # 锤子线（看涨）
        if lower_wick > body * 2 and upper_wick < body * 0.5 and c > o:
            patterns.append({
                'name': '锤子线', 'type': 'bullish', 'strength': 0.7,
                'desc': '长下影线+小实体，底部反转信号',
            })

        # 倒锤子（看涨）
        if upper_wick > body * 2 and lower_wick < body * 0.5 and c2 < o2:
            patterns.append({
                'name': '倒锤子', 'type': 'bullish', 'strength': 0.5,
                'desc': '长上影线，下跌后底部确认',
            })

        # 上吊线（看跌）
        if lower_wick > body * 2 and upper_wick < body * 0.3 and c < o:
            patterns.append({
                'name': '上吊线', 'type': 'bearish', 'strength': 0.6,
                'desc': '上涨后长下影线，顶部警告',
            })

        # 看涨吞没
        if len(df) >= 2:
            if c2 < o2 and c > o and c > o2 and o < c2:
                patterns.append({
                    'name': '看涨吞没', 'type': 'bullish', 'strength': 0.8,
                    'desc': '阳线完全包住前阴线，强反转信号',
                })

        # 看跌吞没
        if len(df) >= 2:
            if c2 > o2 and c < o and o > c2 and c < o2:
                patterns.append({
                    'name': '看跌吞没', 'type': 'bearish', 'strength': 0.8,
                    'desc': '阴线完全包住前阳线，强顶部信号',
                })

        # 十字星（变盘）
        if body < total_range * 0.1:
            patterns.append({
                'name': '十字星', 'type': 'neutral', 'strength': 0.5,
                'desc': '多空博弈激烈，即将变盘',
            })

        # 启明星（三根K线看涨）
        if len(df) >= 3:
            o3 = float(df['open'].iloc[-3])
            c3 = float(df['close'].iloc[-3])
            if c3 < o3 and body2 < abs(c3 - o3) * 0.3 and c > o and c > (o3 + c3) / 2:
                patterns.append({
                    'name': '启明星', 'type': 'bullish', 'strength': 0.9,
                    'desc': '阴线+小实体+阳线，强底部反转',
                })

        # 黄昏星（三根K线看跌）
        if len(df) >= 3:
            o3 = float(df['open'].iloc[-3])
            c3 = float(df['close'].iloc[-3])
            if c3 > o3 and body2 < abs(c3 - o3) * 0.3 and c < o and c < (o3 + c3) / 2:
                patterns.append({
                    'name': '黄昏星', 'type': 'bearish', 'strength': 0.85,
                    'desc': '阳线+小实体+阴线，强顶部反转',
                })

        return patterns


# ═══════════════════════════════════════════════════════════════
#  宏观信号分析（来自 智能交易系统.py + enhanced_macro_analyst.py）
# ═══════════════════════════════════════════════════════════════
class MacroSignalAnalyzer:
    """宏观面信号分析（使用akshare获取）"""

    def __init__(self):
        self._cache = {}
        self._cache_ts = {}
        self._cache_ttl = 3600  # 1小时缓存

    def get_macro_bias(self) -> Dict:
        """
        获取宏观偏向信号

        Returns:
            {
                'bias': float,      # -1 ~ +1, 正=利多黄金
                'confidence': float,
                'factors': dict,
                'summary': str,
            }
        """
        import time
        cache_key = 'macro_bias'
        if cache_key in self._cache:
            if time.time() - self._cache_ts.get(cache_key, 0) < self._cache_ttl:
                return self._cache[cache_key]

        factors = {}
        signals = []

        # 1. 国际金价趋势
        gold_info = self._get_intl_gold()
        if gold_info:
            factors['intl_gold'] = gold_info
            chg = gold_info.get('change_pct', 0)
            if chg > 0.5:
                signals.append(0.3)
                factors['gold_signal'] = f"国际金价上涨{chg:.1f}%，利多"
            elif chg < -0.5:
                signals.append(-0.3)
                factors['gold_signal'] = f"国际金价下跌{chg:.1f}%，利空"
            else:
                signals.append(0)
                factors['gold_signal'] = "国际金价平稳"

        # 2. 上海金价
        shau = self._get_shanghai_gold()
        if shau:
            factors['shanghai_gold'] = shau

        # 3. 板块资金流向
        flow = self._get_gold_sector_flow()
        if flow:
            factors['sector_flow'] = flow
            net = flow.get('net_inflow', 0)
            if net > 1e8:
                signals.append(0.25)
                factors['flow_signal'] = f"板块主力净流入{net/1e8:.1f}亿，利多"
            elif net < -1e8:
                signals.append(-0.2)
                factors['flow_signal'] = f"板块主力净流出{abs(net)/1e8:.1f}亿，利空"
            else:
                factors['flow_signal'] = "板块资金流向平稳"

        if signals:
            bias = float(np.mean(signals))
            confidence = max(0.3, 1 - float(np.std(signals))) if len(signals) > 1 else 0.5
        else:
            bias = 0
            confidence = 0.3

        if bias > 0.15:
            summary = "宏观面利多黄金"
        elif bias < -0.15:
            summary = "宏观面利空黄金"
        else:
            summary = "宏观面中性"

        result = {'bias': bias, 'confidence': confidence,
                  'factors': factors, 'summary': summary}
        self._cache[cache_key] = result
        self._cache_ts[cache_key] = time.time()
        return result

    def _get_intl_gold(self) -> Optional[Dict]:
        try:
            import akshare as ak
            df = ak.futures_foreign_hist(symbol="黄金")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'price': float(latest.get('收盘价', 0)),
                    'change_pct': float(latest.get('涨跌幅', 0)),
                }
        except Exception:
            pass
        return None

    def _get_shanghai_gold(self) -> Optional[Dict]:
        try:
            import akshare as ak
            df = ak.spot_golden_benchmark_sge_daily()
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'price': float(latest.iloc[1]) if len(latest) > 1 else 0,
                    'date': str(latest.iloc[0]) if len(latest) > 0 else '',
                }
        except Exception:
            pass
        return None

    def _get_gold_sector_flow(self) -> Optional[Dict]:
        try:
            import akshare as ak
            df = ak.stock_sector_fund_flow_rank(indicator="今日")
            if df is not None and not df.empty:
                gold_row = df[df['名称'].str.contains('黄金', na=False)]
                if not gold_row.empty:
                    row = gold_row.iloc[0]
                    return {
                        'net_inflow': float(row.get('主力净流入-净额', 0) or 0),
                        'change_pct': float(row.get('今日涨跌幅', 0) or 0),
                    }
        except Exception:
            pass
        return None


# ═══════════════════════════════════════════════════════════════
#  7大核心策略 + 行情自适应
# ═══════════════════════════════════════════════════════════════
class GoldStrategyEngine:
    """黄金日内多维策略引擎"""

    def __init__(self):
        self.ti = TechnicalIndicators()
        self.regime_detector = RegimeDetector()
        self.pattern_detector = CandlestickPatterns()
        self.macro_analyzer = MacroSignalAnalyzer()
        self.weights = dict(cfg.STRATEGY_WEIGHTS)
        logger.info("策略引擎初始化完成（7维策略 + 行情识别 + K线形态 + 宏观分析）")

    def analyze(self, code: str, name: str, df: pd.DataFrame,
                price: float, is_t0: bool = True) -> TradeSignal:
        """对单只标的执行完整策略分析"""
        if df is None or len(df) < 30:
            return TradeSignal(
                code=code, name=name, direction='HOLD',
                score=0, confidence=0, strategies={},
                reason='数据不足，无法分析', is_t0=is_t0,
            )

        # ── 计算所有技术指标 ──────────────────────────
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        rsi = self.ti.rsi(close, cfg.RSI_PERIOD)
        dif, dea, macd_hist = self.ti.macd(close, cfg.MACD_FAST, cfg.MACD_SLOW, cfg.MACD_SIGNAL)
        bb_upper, bb_mid, bb_lower = self.ti.bollinger_bands(close, cfg.BB_PERIOD, cfg.BB_STD)
        mas = self.ti.moving_averages(close, [cfg.MA_SHORT, cfg.MA_MID, cfg.MA_LONG])
        atr = self.ti.atr(high, low, close, cfg.ATR_PERIOD)
        vol_ratio = self.ti.volume_ratio(volume)
        k, d, j = self.ti.kdj(high, low, close)

        latest = {
            'rsi': float(rsi.iloc[-1]) if not rsi.empty else 50,
            'dif': float(dif.iloc[-1]) if not dif.empty else 0,
            'dea': float(dea.iloc[-1]) if not dea.empty else 0,
            'macd_hist': float(macd_hist.iloc[-1]) if not macd_hist.empty else 0,
            'bb_upper': float(bb_upper.iloc[-1]) if not bb_upper.empty else price,
            'bb_mid': float(bb_mid.iloc[-1]) if not bb_mid.empty else price,
            'bb_lower': float(bb_lower.iloc[-1]) if not bb_lower.empty else price,
            'atr': float(atr.iloc[-1]) if not atr.empty else 0,
            'vol_ratio': float(vol_ratio.iloc[-1]) if not vol_ratio.empty else 1,
            'k': float(k.iloc[-1]) if not k.empty else 50,
            'd': float(d.iloc[-1]) if not d.empty else 50,
            'j': float(j.iloc[-1]) if not j.empty else 50,
        }
        for ma_name, ma_s in mas.items():
            latest[ma_name] = float(ma_s.iloc[-1]) if not ma_s.empty else price

        # ── 行情识别 ──────────────────────────────────
        regime_info = self.regime_detector.detect(df)
        regime = regime_info['regime']
        regime_desc = regime_info['description']

        # ── K线形态检测 ───────────────────────────────
        patterns = self.pattern_detector.detect_all(df)

        # ── 宏观偏向（静默获取，不阻塞） ──────────────
        try:
            macro_info = self.macro_analyzer.get_macro_bias()
            macro_bias = macro_info['bias']
        except Exception:
            macro_info = {'bias': 0, 'summary': '宏观数据暂不可用', 'factors': {}}
            macro_bias = 0

        # ── 7大策略评分 ──────────────────────────────
        s1 = self._strategy_rsi_reversal(rsi, latest)
        s2 = self._strategy_macd_cross(dif, dea, macd_hist, latest)
        s3 = self._strategy_bollinger_squeeze(close, bb_upper, bb_mid, bb_lower, vol_ratio, latest)
        s4 = self._strategy_volume_breakout(close, volume, vol_ratio, mas, latest)
        s5 = self._strategy_ma_trend(close, mas, latest)
        s6 = self._strategy_kdj_signal(latest)
        s7 = self._strategy_pattern_signal(patterns, regime)

        strategies = {
            'rsi_reversal': s1,
            'macd_cross': s2,
            'bollinger_squeeze': s3,
            'volume_breakout': s4,
            'ma_trend': s5,
            'kdj_signal': s6,
            'pattern_regime': s7,
        }

        # ── 加权投票 ─────────────────────────────────
        w = self.weights
        # 对新增策略使用均分权重
        strategy_keys = list(strategies.keys())
        total_weight = 0
        final_score = 0
        for sk in strategy_keys:
            sw = w.get(sk, 1.0 / len(strategy_keys))
            final_score += strategies[sk]['signal'] * sw
            total_weight += sw
        if total_weight > 0:
            final_score /= total_weight

        # 宏观修正（±10%）
        final_score += macro_bias * 0.1

        # 行情修正
        if regime == 'REVERSAL':
            final_score += 0.15
        elif regime == 'CRASH':
            final_score -= 0.1
        elif regime == 'TREND_DOWN':
            final_score -= 0.05

        final_score = np.clip(final_score, -1.0, 1.0)

        # 共识度 & 置信度
        sig_vals = [s['signal'] for s in strategies.values()]
        consensus = 1 - (np.std(sig_vals) / 2) if len(sig_vals) > 1 else 0.5
        confidence = (abs(final_score) + consensus) / 2

        # ── 方向判定 ─────────────────────────────────
        if final_score >= cfg.MIN_SIGNAL_SCORE:
            direction = 'BUY'
        elif final_score <= -cfg.MIN_SIGNAL_SCORE:
            direction = 'SELL'
        else:
            direction = 'HOLD'

        # T+1 不发卖出
        if not is_t0 and direction == 'SELL':
            direction = 'HOLD'

        # ── 止损止盈 ─────────────────────────────────
        atr_val = latest['atr']
        if direction == 'BUY':
            entry = price
            stop_loss = round(price - max(atr_val * 2, price * cfg.STOP_LOSS_PCT), 3)
            take_profit = round(price + max(atr_val * 3, price * cfg.TAKE_PROFIT_PCT), 3)
        elif direction == 'SELL':
            entry = price
            stop_loss = round(price + max(atr_val * 2, price * cfg.STOP_LOSS_PCT), 3)
            take_profit = round(price - max(atr_val * 3, price * cfg.TAKE_PROFIT_PCT), 3)
        else:
            entry = stop_loss = take_profit = 0

        rr = 0
        if entry and stop_loss and take_profit and entry != stop_loss:
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
            rr = round(reward / risk, 1) if risk > 0 else 0

        # ── 紧急度 ───────────────────────────────────
        if abs(final_score) >= 0.8 and confidence >= 0.7:
            urgency = 'CRITICAL'
        elif abs(final_score) >= 0.6:
            urgency = 'HIGH'
        elif abs(final_score) >= 0.4:
            urgency = 'NORMAL'
        else:
            urgency = 'LOW'

        # ── 原因汇总 ─────────────────────────────────
        reasons = []
        for sname, sdata in strategies.items():
            if abs(sdata['signal']) >= 0.3:
                reasons.append(sdata['reason'])
        if patterns:
            reasons.append('K线形态: ' + ', '.join(p['name'] for p in patterns))
        if regime != 'RANGE':
            reasons.append(f'行情: {regime_desc}')
        if abs(macro_bias) > 0.1:
            reasons.append(macro_info['summary'])
        reason = '；'.join(reasons) if reasons else '信号不足，建议观望'

        return TradeSignal(
            code=code, name=name, direction=direction,
            score=round(final_score, 3), confidence=round(confidence, 3),
            strategies=strategies,
            entry_price=entry, stop_loss=stop_loss, take_profit=take_profit,
            reason=reason, is_t0=is_t0, urgency=urgency,
            regime=regime, regime_desc=regime_desc,
            patterns=patterns, macro_bias=round(macro_bias, 3),
            risk_reward=rr,
        )

    # ─────────────────────────────────────────────────────────
    #  策略1: RSI 背离反转
    # ─────────────────────────────────────────────────────────
    def _strategy_rsi_reversal(self, rsi: pd.Series, latest: Dict) -> Dict:
        rsi_val = latest['rsi']
        signal = 0.0
        reason = ''

        if rsi_val < cfg.RSI_OVERSOLD:
            strength = (cfg.RSI_OVERSOLD - rsi_val) / cfg.RSI_OVERSOLD
            signal = min(1.0, strength * 1.5)
            reason = f'RSI={rsi_val:.1f} 超卖反弹'
        elif rsi_val > cfg.RSI_OVERBOUGHT:
            strength = (rsi_val - cfg.RSI_OVERBOUGHT) / (100 - cfg.RSI_OVERBOUGHT)
            signal = max(-1.0, -strength * 1.5)
            reason = f'RSI={rsi_val:.1f} 超买回调'
        else:
            if rsi_val < 45:
                signal = 0.2
                reason = f'RSI={rsi_val:.1f} 偏弱'
            elif rsi_val > 55:
                signal = -0.1
                reason = f'RSI={rsi_val:.1f} 偏强'
            else:
                reason = f'RSI={rsi_val:.1f} 中性'

        # 底背离检测
        if len(rsi) >= 20:
            rsi_recent = rsi.iloc[-20:]
            if rsi_val < 40 and rsi_val > float(rsi_recent.min()):
                signal += 0.2
                reason += ' + 底背离'

        return {'signal': np.clip(signal, -1, 1), 'reason': reason, 'rsi': rsi_val}

    # ─────────────────────────────────────────────────────────
    #  策略2: MACD 金叉/死叉
    # ─────────────────────────────────────────────────────────
    def _strategy_macd_cross(self, dif, dea, hist, latest) -> Dict:
        signal = 0.0
        reason = ''
        if len(dif) < 3:
            return {'signal': 0, 'reason': '数据不足', 'dif': 0, 'dea': 0}

        dif_now, dea_now = latest['dif'], latest['dea']
        hist_now = latest['macd_hist']
        dif_prev = float(dif.iloc[-2])
        dea_prev = float(dea.iloc[-2])
        hist_prev = float(hist.iloc[-2])

        if dif_prev <= dea_prev and dif_now > dea_now:
            signal = 0.8 if dif_now >= 0 else 1.0
            reason = 'MACD金叉' if dif_now >= 0 else 'MACD零轴下金叉（强信号）'
        elif dif_prev >= dea_prev and dif_now < dea_now:
            signal = -0.8 if dif_now <= 0 else -1.0
            reason = 'MACD死叉' if dif_now <= 0 else 'MACD零轴上死叉（强信号）'
        else:
            if hist_now > hist_prev and hist_now > 0:
                signal, reason = 0.3, 'MACD红柱放大'
            elif hist_now < hist_prev and hist_now < 0:
                signal, reason = -0.3, 'MACD绿柱放大'
            elif hist_now > hist_prev and hist_now < 0:
                signal, reason = 0.2, 'MACD绿柱缩短'
            elif hist_now < hist_prev and hist_now > 0:
                signal, reason = -0.2, 'MACD红柱缩短'
            else:
                reason = 'MACD无明确信号'

        return {'signal': np.clip(signal, -1, 1), 'reason': reason,
                'dif': dif_now, 'dea': dea_now, 'hist': hist_now}

    # ─────────────────────────────────────────────────────────
    #  策略3: 布林带压缩突破
    # ─────────────────────────────────────────────────────────
    def _strategy_bollinger_squeeze(self, close, bb_upper, bb_mid, bb_lower,
                                     vol_ratio, latest) -> Dict:
        signal = 0.0
        reason = ''
        price = float(close.iloc[-1])
        upper, mid, lower = latest['bb_upper'], latest['bb_mid'], latest['bb_lower']
        vr = latest['vol_ratio']

        bb_width = (upper - lower) / mid if mid > 0 else 0
        bb_pos = (price - lower) / (upper - lower) if (upper - lower) > 0 else 0.5

        if bb_pos <= 0.1 and vr >= cfg.VOLUME_SURGE_RATIO:
            signal = 0.9
            reason = f'触及布林下轨 + 放量（量比{vr:.1f}），反弹信号'
        elif bb_pos <= 0.2:
            signal = 0.5
            reason = f'接近布林下轨（位置{bb_pos:.0%}）'
        elif bb_pos >= 0.9 and vr >= cfg.VOLUME_SURGE_RATIO:
            signal = -0.7
            reason = f'触及布林上轨 + 放量（量比{vr:.1f}），回调信号'
        elif bb_pos >= 0.8:
            signal = -0.4
            reason = f'接近布林上轨（位置{bb_pos:.0%}）'
        elif bb_width < 0.02:
            signal = 0.1
            reason = f'布林带极度收窄（宽度{bb_width:.1%}），即将变盘'
        else:
            reason = f'布林带中性（位置{bb_pos:.0%}）'

        return {'signal': np.clip(signal, -1, 1), 'reason': reason,
                'bb_pos': bb_pos, 'bb_width': bb_width}

    # ─────────────────────────────────────────────────────────
    #  策略4: 量价突破
    # ─────────────────────────────────────────────────────────
    def _strategy_volume_breakout(self, close, volume, vol_ratio, mas, latest) -> Dict:
        signal = 0.0
        reason = ''
        price = float(close.iloc[-1])
        vr = latest['vol_ratio']

        if len(close) < 20:
            return {'signal': 0, 'reason': '数据不足', 'vol_ratio': 1}

        high_20 = float(close.iloc[-20:].max())
        low_20 = float(close.iloc[-20:].min())

        if price >= high_20 * 0.998 and vr >= cfg.VOLUME_SURGE_RATIO:
            signal = 0.9
            reason = f'放量突破20周期高点¥{high_20:.3f}（量比{vr:.1f}）'
        elif price <= low_20 * 1.002 and vr >= cfg.VOLUME_SURGE_RATIO:
            signal = -0.8
            reason = f'放量跌破20周期低点¥{low_20:.3f}（量比{vr:.1f}）'
        elif vr < 0.5:
            signal = 0.1
            reason = f'极度缩量（量比{vr:.2f}），可能蓄势'
        elif vr >= 2.0 and len(close) >= 2 and abs(price / float(close.iloc[-2]) - 1) < 0.003:
            signal = -0.3
            reason = f'放量滞涨（量比{vr:.1f}），注意风险'
        else:
            reason = f'量能正常（量比{vr:.1f}）'

        return {'signal': np.clip(signal, -1, 1), 'reason': reason, 'vol_ratio': vr}

    # ─────────────────────────────────────────────────────────
    #  策略5: 均线趋势
    # ─────────────────────────────────────────────────────────
    def _strategy_ma_trend(self, close, mas, latest) -> Dict:
        signal = 0.0
        reason = ''
        price = float(close.iloc[-1])

        ma_short = latest.get(f'MA{cfg.MA_SHORT}', price)
        ma_mid = latest.get(f'MA{cfg.MA_MID}', price)
        ma_long = latest.get(f'MA{cfg.MA_LONG}', price)

        if ma_short > ma_mid > ma_long and price > ma_short:
            signal = 0.8
            reason = '均线多头排列 + 价格在均线上方'
        elif ma_short < ma_mid < ma_long and price < ma_short:
            signal = -0.8
            reason = '均线空头排列 + 价格在均线下方'
        elif len(close) >= 3:
            mk_s = f'MA{cfg.MA_SHORT}'
            mk_m = f'MA{cfg.MA_MID}'
            if mk_s in mas and mk_m in mas:
                s_prev = float(mas[mk_s].iloc[-2]) if len(mas[mk_s]) >= 2 else ma_short
                m_prev = float(mas[mk_m].iloc[-2]) if len(mas[mk_m]) >= 2 else ma_mid
                if s_prev <= m_prev and ma_short > ma_mid:
                    signal, reason = 0.7, f'MA{cfg.MA_SHORT}上穿MA{cfg.MA_MID}金叉'
                elif s_prev >= m_prev and ma_short < ma_mid:
                    signal, reason = -0.7, f'MA{cfg.MA_SHORT}下穿MA{cfg.MA_MID}死叉'
                elif price > ma_mid:
                    signal, reason = 0.2, f'价格在MA{cfg.MA_MID}上方'
                else:
                    signal, reason = -0.2, f'价格在MA{cfg.MA_MID}下方'
        else:
            reason = '均线无明确趋势'

        return {'signal': np.clip(signal, -1, 1), 'reason': reason,
                'ma_short': ma_short, 'ma_mid': ma_mid, 'ma_long': ma_long}

    # ─────────────────────────────────────────────────────────
    #  策略6: KDJ 金叉死叉
    # ─────────────────────────────────────────────────────────
    def _strategy_kdj_signal(self, latest: Dict) -> Dict:
        k_val = latest['k']
        d_val = latest['d']
        j_val = latest['j']
        signal = 0.0
        reason = ''

        # KDJ 超卖区金叉
        if k_val < 20 and d_val < 20:
            signal = 0.7
            reason = f'KDJ超卖区（K={k_val:.0f},D={d_val:.0f}），反弹信号'
        elif k_val > 80 and d_val > 80:
            signal = -0.7
            reason = f'KDJ超买区（K={k_val:.0f},D={d_val:.0f}），回调信号'
        elif j_val > 100:
            signal = -0.5
            reason = f'J值={j_val:.0f}>100，超强超买'
        elif j_val < 0:
            signal = 0.5
            reason = f'J值={j_val:.0f}<0，超强超卖'
        elif k_val > d_val:
            signal = 0.2
            reason = f'KDJ多头（K={k_val:.0f}>D={d_val:.0f}）'
        elif k_val < d_val:
            signal = -0.2
            reason = f'KDJ空头（K={k_val:.0f}<D={d_val:.0f}）'
        else:
            reason = f'KDJ中性'

        return {'signal': np.clip(signal, -1, 1), 'reason': reason,
                'k': k_val, 'd': d_val, 'j': j_val}

    # ─────────────────────────────────────────────────────────
    #  策略7: K线形态 + 行情识别
    # ─────────────────────────────────────────────────────────
    def _strategy_pattern_signal(self, patterns: List[Dict], regime: str) -> Dict:
        signal = 0.0
        reason = ''

        if not patterns:
            return {'signal': 0, 'reason': '无明显K线形态', 'patterns': []}

        bullish = sum(p['strength'] for p in patterns if p['type'] == 'bullish')
        bearish = sum(p['strength'] for p in patterns if p['type'] == 'bearish')

        signal = np.clip(bullish - bearish, -1, 1)

        # 行情加成
        if regime == 'REVERSAL' and signal > 0:
            signal = min(1.0, signal + 0.2)
        elif regime == 'CRASH' and signal < 0:
            signal = max(-1.0, signal - 0.1)

        names = [p['name'] for p in patterns]
        reason = ' + '.join(names)
        if regime != 'RANGE':
            reason += f'（{regime}行情加成）'

        return {'signal': np.clip(signal, -1, 1), 'reason': reason,
                'patterns': [p['name'] for p in patterns]}

    # ─────────────────────────────────────────────────────────
    #  批量分析（看板数据）
    # ─────────────────────────────────────────────────────────
    def analyze_watchlist(self, provider, codes: List[str] = None) -> List[TradeSignal]:
        if codes is None:
            codes = cfg.DEFAULT_WATCHLIST

        signals: List[TradeSignal] = []
        for code in codes:
            info = cfg.ALL_INSTRUMENTS.get(code, {})
            name = info.get('name', code)
            market = info.get('market', 'SH')
            is_t0 = info.get('t0', False)

            df = provider.get_intraday_klines(code, period='5', days=5, market=market)
            if df is None or df.empty:
                df = provider.get_daily_klines(code, days=60)

            quote = provider.get_realtime_quote(code, market)
            price = quote['price'] if quote else (
                float(df['close'].iloc[-1]) if df is not None and not df.empty else 0)

            if price <= 0:
                continue

            sig = self.analyze(code, name, df, price, is_t0)
            signals.append(sig)

        signals.sort(key=lambda s: abs(s.score), reverse=True)
        return signals

    # ─────────────────────────────────────────────────────────
    #  格式化
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def format_signal_text(sig: TradeSignal) -> str:
        direction_map = {'BUY': '🟢 建议买入', 'SELL': '🔴 建议卖出', 'HOLD': '⚪ 观望等待'}
        urgency_map = {'CRITICAL': '🔥 紧急', 'HIGH': '⚡ 较强',
                       'NORMAL': '📊 一般', 'LOW': '💤 较弱'}

        lines = [
            f"{'='*50}",
            f"  {sig.name}（{sig.code}）",
            f"  {direction_map.get(sig.direction, '⚪ 观望')}",
            f"  行情: {sig.regime_desc}",
            f"{'='*50}",
            f"  综合评分: {sig.score:+.2f}  |  置信度: {sig.confidence:.0%}  |  {urgency_map.get(sig.urgency, '')}",
        ]

        if sig.entry_price:
            lines.append(f"  当前价: ¥{sig.entry_price:.3f}")
        if sig.direction != 'HOLD':
            lines.append(f"  止损价: ¥{sig.stop_loss:.3f}  |  止盈价: ¥{sig.take_profit:.3f}  |  盈亏比: {sig.risk_reward}:1")
            lines.append(f"  {'支持日内T+0' if sig.is_t0 else '⚠️ T+1，今买明卖'}")

        if sig.patterns:
            lines.append(f"  K线形态: {', '.join(p['name'] for p in sig.patterns)}")

        lines.append(f"  分析: {sig.reason}")

        lines.append(f"\n  📊 策略明细:")
        for sname, sdata in sig.strategies.items():
            arrow = '🟢' if sdata['signal'] > 0.2 else '🔴' if sdata['signal'] < -0.2 else '⚪'
            lines.append(f"    {arrow} {sname}: {sdata['signal']:+.2f} - {sdata['reason']}")

        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════
#  测试入口
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    print("=" * 60)
    print("  测试黄金策略引擎 v3.0")
    print("=" * 60)

    np.random.seed(42)
    n = 200
    prices = 6.5 + np.random.randn(n).cumsum() * 0.02
    df = pd.DataFrame({
        'timestamp': pd.date_range('2026-01-01', periods=n, freq='5min'),
        'open': prices + np.random.randn(n) * 0.01,
        'high': prices + abs(np.random.randn(n) * 0.02),
        'low': prices - abs(np.random.randn(n) * 0.02),
        'close': prices,
        'volume': np.random.randint(10000, 100000, n).astype(float),
    })

    engine = GoldStrategyEngine()
    signal = engine.analyze('518880', '黄金ETF（华安）', df, float(prices[-1]), is_t0=True)
    print(engine.format_signal_text(signal))
