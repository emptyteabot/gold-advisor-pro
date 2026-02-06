"""
A股黄金板块数据接口（增强版）
akshare 免费数据 · 东方财富源 · 自动重试 · 多级缓存
Gold Advisor Pro™ v3.0
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import time
import traceback

logger = logging.getLogger(__name__)

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.error("akshare 未安装，请运行: pip install akshare")


class AShareGoldProvider:
    """A股黄金板块数据提供者（增强版）"""

    def __init__(self):
        if not AKSHARE_AVAILABLE:
            raise ImportError("akshare 未安装，请运行 pip install akshare")
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = 10
        self._retry_count = 2
        self._retry_delay = 1.0
        logger.info("AShareGoldProvider 已初始化（增强版）")

    # ─────────────────────────────────────────────────────────
    #  实时行情
    # ─────────────────────────────────────────────────────────
    def get_realtime_quote(self, code: str, market: str = 'SH') -> Optional[Dict]:
        """获取单只标的实时行情"""
        cache_key = f"quote_{code}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            full_code = f"{code}"
            df = self._retry_call(ak.stock_zh_a_spot_em)
            if df is None or df.empty:
                return None

            row = df[df['代码'] == full_code]
            if row.empty:
                try:
                    df_etf = self._retry_call(ak.fund_etf_spot_em)
                    if df_etf is not None and not df_etf.empty:
                        row = df_etf[df_etf['代码'] == full_code]
                except Exception:
                    pass

            if row.empty:
                logger.warning(f"未找到 {code} 的实时数据")
                return None

            row = row.iloc[0]
            result = self._parse_quote_row(code, row)
            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"获取 {code} 实时行情失败: {e}")
            return None

    def get_batch_realtime(self, codes: List[str]) -> Dict[str, Dict]:
        """批量获取实时行情（一次网络请求）"""
        cache_key = f"batch_{'_'.join(sorted(codes))}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        results = {}
        try:
            df_stock = self._retry_call(ak.stock_zh_a_spot_em)
            df_etf = None
            try:
                df_etf = self._retry_call(ak.fund_etf_spot_em)
            except Exception:
                pass

            for code in codes:
                row = None

                if df_stock is not None and not df_stock.empty:
                    match = df_stock[df_stock['代码'] == code]
                    if not match.empty:
                        row = match.iloc[0]

                if row is None and df_etf is not None and not df_etf.empty:
                    match = df_etf[df_etf['代码'] == code]
                    if not match.empty:
                        row = match.iloc[0]

                if row is not None:
                    results[code] = self._parse_quote_row(code, row)

            self._set_cache(cache_key, results)
        except Exception as e:
            logger.error(f"批量获取行情失败: {e}")

        return results

    # ─────────────────────────────────────────────────────────
    #  分钟K线（日内分时）
    # ─────────────────────────────────────────────────────────
    def get_intraday_klines(self, code: str, period: str = '5',
                            days: int = 5, market: str = 'SH') -> Optional[pd.DataFrame]:
        """获取日内分钟K线"""
        cache_key = f"kline_{code}_{period}_{days}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            symbol = f"{code}"
            df = None

            # 先尝试股票分钟线
            try:
                df = self._retry_call(
                    ak.stock_zh_a_hist_min_em,
                    symbol=symbol, period=period, adjust="qfq"
                )
            except Exception:
                pass

            # 再尝试ETF分钟线
            if df is None or df.empty:
                try:
                    df = self._retry_call(
                        ak.fund_etf_hist_min_em,
                        symbol=symbol, period=period, adjust="qfq"
                    )
                except Exception:
                    pass

            if df is None or df.empty:
                logger.warning(f"未获取到 {code} 的分钟K线数据")
                return None

            df = self._normalize_kline_df(df)

            if days > 0 and 'timestamp' in df.columns:
                cutoff = datetime.now() - timedelta(days=days)
                df = df[df['timestamp'] >= cutoff].reset_index(drop=True)

            self._set_cache(cache_key, df)
            return df

        except Exception as e:
            logger.error(f"获取 {code} 分钟K线失败: {e}")
            return None

    # ─────────────────────────────────────────────────────────
    #  日线数据
    # ─────────────────────────────────────────────────────────
    def get_daily_klines(self, code: str, days: int = 120) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        cache_key = f"daily_{code}_{days}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            df = None
            try:
                df = self._retry_call(
                    ak.stock_zh_a_hist,
                    symbol=code, period="daily",
                    start_date=start_date, end_date=end_date, adjust="qfq"
                )
            except Exception:
                pass

            if df is None or df.empty:
                try:
                    df = self._retry_call(
                        ak.fund_etf_hist_em,
                        symbol=code, period="daily",
                        start_date=start_date, end_date=end_date, adjust="qfq"
                    )
                except Exception:
                    pass

            if df is None or df.empty:
                return None

            df = self._normalize_kline_df(df)
            self._set_cache(cache_key, df)
            return df

        except Exception as e:
            logger.error(f"获取 {code} 日线失败: {e}")
            return None

    # ─────────────────────────────────────────────────────────
    #  国际金价参考
    # ─────────────────────────────────────────────────────────
    def get_international_gold_price(self) -> Optional[Dict]:
        """获取国际金价（美元/盎司）"""
        cache_key = "intl_gold"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            df = self._retry_call(ak.futures_foreign_hist, symbol="黄金")
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                result = {
                    'price': float(latest.get('收盘价', 0)),
                    'change_pct': float(latest.get('涨跌幅', 0)),
                    'date': str(latest.get('日期', '')),
                }
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            logger.warning(f"获取国际金价失败: {e}")

        return None

    # ─────────────────────────────────────────────────────────
    #  上海金价
    # ─────────────────────────────────────────────────────────
    def get_shanghai_gold_price(self) -> Optional[Dict]:
        """获取上海金交所 AU9999"""
        cache_key = "sh_gold"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            df = self._retry_call(ak.spot_golden_benchmark_sge_daily)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                result = {
                    'price': float(latest.iloc[1]) if len(latest) > 1 else 0,
                    'date': str(latest.iloc[0]) if len(latest) > 0 else '',
                }
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            logger.warning(f"获取上海金价失败: {e}")

        return None

    # ─────────────────────────────────────────────────────────
    #  黄金板块资金流向
    # ─────────────────────────────────────────────────────────
    def get_gold_sector_flow(self) -> Optional[Dict]:
        """获取黄金板块资金流向"""
        cache_key = "gold_flow"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            df = self._retry_call(ak.stock_sector_fund_flow_rank, indicator="今日")
            if df is not None and not df.empty:
                gold_row = df[df['名称'].str.contains('黄金', na=False)]
                if not gold_row.empty:
                    row = gold_row.iloc[0]
                    result = {
                        'net_inflow': float(row.get('主力净流入-净额', 0) or 0),
                        'change_pct': float(row.get('今日涨跌幅', 0) or 0),
                    }
                    self._set_cache(cache_key, result)
                    return result
        except Exception as e:
            logger.warning(f"获取板块资金流向失败: {e}")

        return None

    # ─────────────────────────────────────────────────────────
    #  工具方法
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def is_trading_time() -> bool:
        """判断当前是否为A股交易时间"""
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        t = now.strftime('%H:%M')
        return ('09:30' <= t <= '11:30') or ('13:00' <= t <= '15:00')

    @staticmethod
    def get_market_status() -> str:
        """获取市场状态描述"""
        now = datetime.now()
        if now.weekday() >= 5:
            return "周末休市"
        t = now.strftime('%H:%M')
        if t < '09:15':
            return "盘前准备"
        elif '09:15' <= t < '09:25':
            return "集合竞价"
        elif '09:25' <= t < '09:30':
            return "等待开盘"
        elif '09:30' <= t <= '11:30':
            return "上午交易中"
        elif '11:30' < t < '13:00':
            return "午间休市"
        elif '13:00' <= t <= '15:00':
            return "下午交易中"
        else:
            return "已收盘"

    @staticmethod
    def get_market_status_icon() -> str:
        """获取市场状态图标"""
        now = datetime.now()
        if now.weekday() >= 5:
            return "🔴"
        t = now.strftime('%H:%M')
        if ('09:30' <= t <= '11:30') or ('13:00' <= t <= '15:00'):
            return "🟢"
        elif '09:15' <= t < '09:30':
            return "🟡"
        elif '11:30' < t < '13:00':
            return "🟡"
        else:
            return "🔴"

    # ─────────────────────────────────────────────────────────
    #  内部方法
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def _parse_quote_row(code: str, row) -> Dict:
        """解析行情数据行"""
        return {
            'code': code,
            'name': str(row.get('名称', '')),
            'price': float(row.get('最新价', 0) or 0),
            'change_pct': float(row.get('涨跌幅', 0) or 0),
            'change_amt': float(row.get('涨跌额', 0) or 0),
            'volume': float(row.get('成交量', 0) or 0),
            'amount': float(row.get('成交额', 0) or 0),
            'open': float(row.get('今开', 0) or 0),
            'high': float(row.get('最高', 0) or 0),
            'low': float(row.get('最低', 0) or 0),
            'prev_close': float(row.get('昨收', 0) or 0),
            'turnover_rate': float(row.get('换手率', 0) or 0),
            'amplitude': float(row.get('振幅', 0) or 0),
            'timestamp': datetime.now(),
        }

    @staticmethod
    def _normalize_kline_df(df: pd.DataFrame) -> pd.DataFrame:
        """标准化K线 DataFrame"""
        col_map = {
            '时间': 'timestamp', '日期': 'timestamp',
            '开盘': 'open', '最高': 'high', '最低': 'low',
            '收盘': 'close', '成交量': 'volume', '成交额': 'amount',
        }
        df = df.rename(columns=col_map)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df

    def _retry_call(self, func, *args, **kwargs):
        """带重试的函数调用"""
        for attempt in range(self._retry_count + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < self._retry_count:
                    time.sleep(self._retry_delay)
                else:
                    raise

    def _get_cache(self, key: str):
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
        return None

    def _set_cache(self, key: str, data):
        self._cache[key] = (data, time.time())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    print("=" * 60)
    print("  测试 A股黄金数据接口（增强版）")
    print("=" * 60)

    provider = AShareGoldProvider()

    print(f"\n市场状态: {provider.get_market_status_icon()} {provider.get_market_status()}")
    print(f"是否交易时间: {provider.is_trading_time()}")

    print("\n批量获取行情...")
    quotes = provider.get_batch_realtime(['518880', '600547', '601899'])
    for code, q in quotes.items():
        print(f"  {q['name']}({code}): ¥{q['price']:.3f}  {q['change_pct']:+.2f}%")

    print("\n获取5分钟K线...")
    klines = provider.get_intraday_klines('518880', period='5', days=3)
    if klines is not None:
        print(f"  获取到 {len(klines)} 根K线")
