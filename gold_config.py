"""
Gold Advisor Pro™ - A股黄金日内交易策略系统
专业配置文件
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent / '.env.trading'
load_dotenv(_ENV_PATH)

# ═══════════════════════════════════════════════════════════════
#  产品信息（商业品牌）
# ═══════════════════════════════════════════════════════════════
PRODUCT_NAME = "Gold Advisor Pro™"
PRODUCT_VERSION = "3.0.0"
PRODUCT_SUBTITLE = "A股黄金板块 · 日内智能交易策略系统"
PRODUCT_SLOGAN = "五维策略引擎 · 实时智能信号 · 专业级风控"
PRODUCT_COPYRIGHT = "© 2026 Gold Advisor Pro™ · All Rights Reserved"
CONTACT_WECHAT = "GoldAdvisorVIP"
CONTACT_EMAIL = "support@goldadvisor.pro"

# ═══════════════════════════════════════════════════════════════
#  黄金ETF（支持日内T+0，核心推荐）
# ═══════════════════════════════════════════════════════════════
GOLD_ETFS = {
    '518880': {'name': '黄金ETF（华安）',   'type': 'ETF', 'market': 'SH', 't0': True,
               'desc': '规模最大，日均成交额超10亿，流动性最佳'},
    '159934': {'name': '黄金ETF（易方达）', 'type': 'ETF', 'market': 'SZ', 't0': True,
               'desc': '深交所黄金ETF龙头'},
    '518800': {'name': '黄金股ETF',         'type': 'ETF', 'market': 'SH', 't0': True,
               'desc': '跟踪黄金产业链股票'},
    '159937': {'name': '博时黄金ETF',       'type': 'ETF', 'market': 'SZ', 't0': True,
               'desc': '跟踪AU9999'},
    '518660': {'name': '黄金基金ETF',       'type': 'ETF', 'market': 'SH', 't0': True,
               'desc': '低费率黄金ETF'},
    '159812': {'name': '黄金ETF（国泰）',   'type': 'ETF', 'market': 'SZ', 't0': True,
               'desc': '国泰基金旗下'},
    '159562': {'name': '黄金ETF基金',       'type': 'ETF', 'market': 'SZ', 't0': True,
               'desc': '新上市黄金ETF'},
    '518850': {'name': '黄金ETF（华夏）',   'type': 'ETF', 'market': 'SH', 't0': True,
               'desc': '华夏基金旗下'},
}

# ═══════════════════════════════════════════════════════════════
#  黄金概念基金（场内交易，部分支持T+0）
# ═══════════════════════════════════════════════════════════════
GOLD_FUNDS = {
    '159611': {'name': '黄金基金LOF',       'type': 'FUND', 'market': 'SZ', 't0': True,
               'desc': '场内LOF黄金基金'},
    '161116': {'name': '易方达黄金主题',    'type': 'FUND', 'market': 'SZ', 't0': False,
               'desc': '黄金主题LOF'},
}

# ═══════════════════════════════════════════════════════════════
#  黄金概念股（T+1）
# ═══════════════════════════════════════════════════════════════
GOLD_STOCKS = {
    '600547': {'name': '山东黄金', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '国内黄金行业龙头，A+H股'},
    '601899': {'name': '紫金矿业', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '全球化矿业龙头，金铜并重'},
    '600489': {'name': '中金黄金', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '中国黄金集团旗下'},
    '600988': {'name': '赤峰黄金', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '矿产金成长性强'},
    '002155': {'name': '湖南黄金', 'type': 'STOCK', 'market': 'SZ', 't0': False,
               'desc': '湖南省国资黄金矿业'},
    '600531': {'name': '豫光金铅', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '黄金冶炼+铅冶炼'},
    '000975': {'name': '银泰黄金', 'type': 'STOCK', 'market': 'SZ', 't0': False,
               'desc': '高品位金矿资源'},
    '603612': {'name': '索通发展', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '预焙阳极+黄金概念'},
    '002237': {'name': '恒邦股份', 'type': 'STOCK', 'market': 'SZ', 't0': False,
               'desc': '黄金冶炼深加工'},
    '600311': {'name': '荣华实业', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '甘肃金矿资源'},
    '002716': {'name': '金贵银业', 'type': 'STOCK', 'market': 'SZ', 't0': False,
               'desc': '白银冶炼+黄金副产'},
    '600916': {'name': '中国黄金', 'type': 'STOCK', 'market': 'SH', 't0': False,
               'desc': '中国黄金集团核心上市平台'},
}

# ═══════════════════════════════════════════════════════════════
#  合并所有标的 & 默认关注列表
# ═══════════════════════════════════════════════════════════════
ALL_INSTRUMENTS = {**GOLD_ETFS, **GOLD_FUNDS, **GOLD_STOCKS}

# 默认关注（核心ETF + 龙头股）
DEFAULT_WATCHLIST = [
    '518880', '159934', '518800',          # 核心ETF
    '600547', '601899', '600489',          # 龙头股
    '002155', '000975', '600916',          # 二线金股
]

# 按分类
ETF_CODES = list(GOLD_ETFS.keys())
FUND_CODES = list(GOLD_FUNDS.keys())
STOCK_CODES = list(GOLD_STOCKS.keys())

# ═══════════════════════════════════════════════════════════════
#  A股交易时间（北京时间）
# ═══════════════════════════════════════════════════════════════
MARKET_OPEN_AM = "09:30"
MARKET_CLOSE_AM = "11:30"
MARKET_OPEN_PM = "13:00"
MARKET_CLOSE_PM = "15:00"

# 集合竞价
CALL_AUCTION_START = "09:15"
CALL_AUCTION_END = "09:25"
CALL_AUCTION_PM = "14:57"

# 扫描间隔（秒）
SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', '30'))

# ═══════════════════════════════════════════════════════════════
#  策略参数
# ═══════════════════════════════════════════════════════════════
# RSI
RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
RSI_OVERSOLD = float(os.getenv('RSI_OVERSOLD', '30'))
RSI_OVERBOUGHT = float(os.getenv('RSI_OVERBOUGHT', '70'))

# MACD
MACD_FAST = int(os.getenv('MACD_FAST', '12'))
MACD_SLOW = int(os.getenv('MACD_SLOW', '26'))
MACD_SIGNAL = int(os.getenv('MACD_SIGNAL', '9'))

# 布林带
BB_PERIOD = int(os.getenv('BB_PERIOD', '20'))
BB_STD = float(os.getenv('BB_STD', '2.0'))

# 均线
MA_SHORT = int(os.getenv('MA_SHORT', '5'))
MA_MID = int(os.getenv('MA_MID', '20'))
MA_LONG = int(os.getenv('MA_LONG', '60'))

# 量能
VOLUME_SURGE_RATIO = float(os.getenv('VOLUME_SURGE_RATIO', '1.5'))

# ATR
ATR_PERIOD = int(os.getenv('ATR_PERIOD', '14'))

# ═══════════════════════════════════════════════════════════════
#  信号阈值
# ═══════════════════════════════════════════════════════════════
MIN_SIGNAL_SCORE = float(os.getenv('MIN_SIGNAL_SCORE', '0.4'))
MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', '0.5'))
STRONG_SIGNAL_SCORE = float(os.getenv('STRONG_SIGNAL_SCORE', '0.7'))

# ═══════════════════════════════════════════════════════════════
#  风控参数
# ═══════════════════════════════════════════════════════════════
MAX_POSITION_PCT = float(os.getenv('MAX_POSITION_PCT', '0.30'))
MAX_TOTAL_POSITION_PCT = float(os.getenv('MAX_TOTAL_POSITION_PCT', '0.80'))
STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.02'))
TAKE_PROFIT_PCT = float(os.getenv('TAKE_PROFIT_PCT', '0.05'))
MAX_DAILY_LOSS_PCT = float(os.getenv('MAX_DAILY_LOSS_PCT', '0.03'))
TRAILING_STOP_PCT = float(os.getenv('TRAILING_STOP_PCT', '0.015'))

# 日内交易参数
INTRADAY_MAX_TRADES = int(os.getenv('INTRADAY_MAX_TRADES', '5'))
INTRADAY_COOLDOWN_MIN = int(os.getenv('INTRADAY_COOLDOWN_MIN', '15'))
INTRADAY_LAST_ENTRY = "14:30"   # 最晚入场时间
INTRADAY_FORCE_EXIT = "14:50"   # 强制平仓时间（T+0）

# ═══════════════════════════════════════════════════════════════
#  策略权重（5大策略投票制）
# ═══════════════════════════════════════════════════════════════
STRATEGY_WEIGHTS = {
    'rsi_reversal':       float(os.getenv('W_RSI',  '0.20')),
    'macd_cross':         float(os.getenv('W_MACD', '0.20')),
    'bollinger_squeeze':  float(os.getenv('W_BB',   '0.20')),
    'volume_breakout':    float(os.getenv('W_VOL',  '0.20')),
    'ma_trend':           float(os.getenv('W_MA',   '0.20')),
}

# ═══════════════════════════════════════════════════════════════
#  数据源
# ═══════════════════════════════════════════════════════════════
DATA_SOURCE = os.getenv('DATA_SOURCE', 'akshare')
TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '')

# ═══════════════════════════════════════════════════════════════
#  通知推送
# ═══════════════════════════════════════════════════════════════
FEISHU_WEBHOOK = os.getenv('FEISHU_WEBHOOK_URL', '')
FEISHU_ENABLED = bool(os.getenv('FEISHU_ENABLED', ''))

# ═══════════════════════════════════════════════════════════════
#  Gemini AI
# ═══════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_BASE_URL = os.getenv('GEMINI_BASE_URL', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', '')

# ═══════════════════════════════════════════════════════════════
#  代理
# ═══════════════════════════════════════════════════════════════
HTTP_PROXY = os.getenv('HTTP_PROXY')
HTTPS_PROXY = os.getenv('HTTPS_PROXY')

# ═══════════════════════════════════════════════════════════════
#  Web 界面
# ═══════════════════════════════════════════════════════════════
WEB_PORT = int(os.getenv('WEB_PORT', '8501'))
AUTO_REFRESH_SEC = int(os.getenv('AUTO_REFRESH_SEC', '30'))
