"""
Gold Advisor Pro™ v3.0
A股黄金日内智能交易策略系统 · 商业版
Streamlit Web 主界面
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging
import time
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gold_config as cfg
from ashare_provider import AShareGoldProvider
from gold_strategy_engine import (GoldStrategyEngine, TechnicalIndicators, TradeSignal,
                                  RegimeDetector, CandlestickPatterns, MacroSignalAnalyzer)
from license_manager import (check_license, activate_license, get_tier_features,
                              _get_machine_id, activate_in_session)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  页面配置
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title=f"{cfg.PRODUCT_NAME} v{cfg.PRODUCT_VERSION}",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
#  OKX / Web3 风格 CSS
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ─── 全局 ─── */
* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Microsoft YaHei', sans-serif !important; }
.stApp {
    background: #0b0e11;
    background-image:
        radial-gradient(ellipse at 10% 20%, rgba(255,215,0,0.03) 0%, transparent 50%),
        radial-gradient(ellipse at 90% 80%, rgba(0,184,212,0.02) 0%, transparent 50%);
}

/* ─── 隐藏默认元素 ─── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

/* ─── 顶部横幅 (OKX hero) ─── */
.okx-banner {
    background: linear-gradient(135deg, #12161c 0%, #1a1f2e 50%, #0f1923 100%);
    border: 1px solid rgba(255,215,0,0.08);
    border-radius: 20px;
    padding: 28px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.okx-banner::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(255,215,0,0.06) 0%, transparent 40%);
    pointer-events: none;
}
.okx-banner h1 {
    margin: 0;
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(90deg, #ffd700, #f0c030, #ffd700);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.okx-banner .sub {
    color: #6b7280;
    font-size: 0.88rem;
    font-weight: 400;
    margin-top: 6px;
}
.okx-banner .badge {
    display: inline-block;
    background: rgba(255,215,0,0.1);
    border: 1px solid rgba(255,215,0,0.2);
    color: #ffd700;
    padding: 3px 14px;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-left: 12px;
    vertical-align: middle;
}
.okx-banner .live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    vertical-align: middle;
    animation: pulse 2s infinite;
}
.live-green { background: #00e676; box-shadow: 0 0 8px #00e676; }
.live-yellow { background: #ffc107; box-shadow: 0 0 8px #ffc107; }
.live-red { background: #ff5252; box-shadow: 0 0 8px #ff5252; }
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ─── 授权页面 (glassmorphism) ─── */
.license-box {
    background: rgba(18,22,28,0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,215,0,0.12);
    border-radius: 24px;
    padding: 48px 40px;
    text-align: center;
    max-width: 480px;
    margin: 50px auto;
    box-shadow: 0 24px 80px rgba(0,0,0,0.5);
}
.license-box h2 {
    background: linear-gradient(90deg, #ffd700, #f0c030);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 1.6rem;
}

/* ─── Tabs (OKX 风格) ─── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(255,255,255,0.02);
    border-radius: 12px;
    padding: 4px;
    border: 1px solid rgba(255,255,255,0.04);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 0.85rem;
    color: #6b7280;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: rgba(255,215,0,0.1) !important;
    color: #ffd700 !important;
    border: 1px solid rgba(255,215,0,0.15) !important;
}

/* ─── Metric 卡片 (neon glow) ─── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 16px 20px;
    transition: all 0.2s ease;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(255,215,0,0.2);
    box-shadow: 0 0 20px rgba(255,215,0,0.05);
}
[data-testid="stMetricLabel"] {
    color: #6b7280 !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="stMetricValue"] {
    font-weight: 700 !important;
    font-size: 1.4rem !important;
    letter-spacing: -0.5px;
}

/* ─── Expander (glass card) ─── */
.streamlit-expanderHeader {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background: rgba(255,255,255,0.01) !important;
    border: 1px solid rgba(255,255,255,0.04) !important;
    border-top: none !important;
    border-radius: 0 0 12px 12px !important;
}

/* ─── DataFrame / 表格 (OKX 数据风格) ─── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.06);
}

/* ─── 按钮 (Web3 gradient) ─── */
.stButton > button {
    background: linear-gradient(135deg, #ffd700, #f0a000) !important;
    color: #0b0e11 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    box-shadow: 0 0 24px rgba(255,215,0,0.3) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #ffd700, #ffaa00) !important;
}

/* ─── Sidebar (OKX 侧栏) ─── */
[data-testid="stSidebar"] {
    background: #0f1217 !important;
    border-right: 1px solid rgba(255,255,255,0.04);
}
[data-testid="stSidebar"] h3 {
    color: #e5e7eb !important;
    font-weight: 700;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ─── Alert 信号 ─── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border: none !important;
    backdrop-filter: blur(10px);
}

/* ─── 滚动条 ─── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,215,0,0.3); border-radius: 10px; }

/* ─── 输入框 ─── */
input, [data-baseweb="input"] {
    border-radius: 12px !important;
    border-color: rgba(255,255,255,0.08) !important;
    background: rgba(255,255,255,0.03) !important;
}
input:focus, [data-baseweb="input"]:focus-within {
    border-color: rgba(255,215,0,0.4) !important;
    box-shadow: 0 0 12px rgba(255,215,0,0.1) !important;
}

/* ─── Divider ─── */
hr { border-color: rgba(255,255,255,0.04) !important; }

/* ─── Radio 水平排列样式 ─── */
[data-testid="stRadio"] > div { gap: 4px; }
[data-testid="stRadio"] label {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 6px 16px;
    font-size: 0.85rem;
    transition: all 0.2s;
}

/* ─── 多选框 / Slider ─── */
.stSlider > div > div > div { color: #ffd700 !important; }

</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  授权检查
# ═══════════════════════════════════════════════════════════════
license_info = check_license()

if not license_info['valid']:
    # 显示激活页面
    st.markdown(f"""
    <div class="license-box">
        <h2>🥇 {cfg.PRODUCT_NAME}</h2>
        <p style="color:#aaa">{cfg.PRODUCT_SUBTITLE}</p>
        <hr style="border-color:rgba(255,215,0,0.2)">
        <p style="color:#ef4444; font-size:1.1rem">{license_info['message']}</p>
        <p style="color:#888; font-size:0.85rem">设备指纹: {license_info['machine_id']}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    col_lic1, col_lic2, col_lic3 = st.columns([1, 2, 1])
    with col_lic2:
        st.markdown("### 🔑 输入授权码激活")
        key_input = st.text_input("授权码", placeholder="GAP-XXXX-XXXX-XXXX-XXXX")
        if st.button("激活授权", use_container_width=True, type="primary"):
            ok, msg = activate_license(key_input)
            if ok:
                activate_in_session(key_input, 'PRO')
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

        st.markdown("---")
        st.markdown("### 💰 购买授权")
        st.markdown(f"""
        | 版本 | 功能 | 价格 |
        |------|------|------|
        | 标准版 | 6个标的 + 实时信号 + 回测 | ¥299/年 |
        | **专业版** | **20个标的 + AI分析 + 推送通知** | **¥599/年** |
        | 企业版 | 不限标的 + API接口 + 技术支持 | ¥1999/年 |

        📱 购买咨询微信: **{cfg.CONTACT_WECHAT}**
        📧 邮箱: **{cfg.CONTACT_EMAIL}**
        """)

        st.markdown(f"""
        ---
        <p style="text-align:center; color:#666; font-size:0.8rem">
        {cfg.PRODUCT_COPYRIGHT}
        </p>
        """, unsafe_allow_html=True)

    st.stop()


# ═══════════════════════════════════════════════════════════════
#  授权通过 → 加载系统
# ═══════════════════════════════════════════════════════════════
tier = license_info['tier']
tier_features = get_tier_features(tier)


@st.cache_resource
def get_provider():
    return AShareGoldProvider()


@st.cache_resource
def get_engine():
    return GoldStrategyEngine()


provider = get_provider()
engine = get_engine()
ti = TechnicalIndicators()


# ═══════════════════════════════════════════════════════════════
#  侧边栏
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    # 品牌区 (OKX style)
    st.markdown(f"""
    <div style="text-align:center; padding:16px 0 8px 0">
        <div style="font-size:2.2rem; margin-bottom:4px">🥇</div>
        <div style="font-weight:800; font-size:1.1rem;
             background:linear-gradient(90deg,#ffd700,#f0c030);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent;
             letter-spacing:-0.3px">{cfg.PRODUCT_NAME}</div>
        <div style="margin-top:6px">
            <span style="background:rgba(255,215,0,0.08); border:1px solid rgba(255,215,0,0.15);
                  color:#ffd700; padding:3px 14px; border-radius:100px; font-size:0.68rem;
                  font-weight:600; letter-spacing:0.5px">
                v{cfg.PRODUCT_VERSION} · {tier_features['name']}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 授权信息
    st.markdown(f"📋 {license_info['message']}")
    st.divider()

    # 市场状态
    market_icon = provider.get_market_status_icon()
    market_status = provider.get_market_status()
    st.markdown(f"### {market_icon} 市场状态")
    st.markdown(f"**{market_status}**")
    st.markdown(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.divider()

    # 关注标的选择
    st.markdown("### 📋 关注标的")

    # 分类选择
    st.markdown("**快速选择:**")
    col_q1, col_q2, col_q3 = st.columns(3)
    with col_q1:
        select_etf = st.checkbox("ETF", value=True)
    with col_q2:
        select_fund = st.checkbox("基金", value=False)
    with col_q3:
        select_stock = st.checkbox("股票", value=True)

    # 构建选项
    available_codes = []
    if select_etf:
        available_codes.extend(cfg.ETF_CODES)
    if select_fund:
        available_codes.extend(cfg.FUND_CODES)
    if select_stock:
        available_codes.extend(cfg.STOCK_CODES)

    all_options = {code: f"{info['name']}({code})"
                   for code, info in cfg.ALL_INSTRUMENTS.items()
                   if code in available_codes}

    default_codes = [c for c in cfg.DEFAULT_WATCHLIST if c in available_codes]

    # 限制标的数量
    max_watchlist = tier_features['max_watchlist']

    selected_codes = st.multiselect(
        f"选择监控标的（最多{max_watchlist}只）",
        options=list(all_options.keys()),
        default=default_codes[:max_watchlist],
        format_func=lambda x: all_options.get(x, x),
        max_selections=max_watchlist,
    )

    st.divider()

    # 策略权重
    st.markdown("### ⚙️ 策略权重调节")
    w_rsi = st.slider("RSI反转", 0.0, 0.5, cfg.STRATEGY_WEIGHTS['rsi_reversal'], 0.05)
    w_macd = st.slider("MACD交叉", 0.0, 0.5, cfg.STRATEGY_WEIGHTS['macd_cross'], 0.05)
    w_bb = st.slider("布林带", 0.0, 0.5, cfg.STRATEGY_WEIGHTS['bollinger_squeeze'], 0.05)
    w_vol = st.slider("量价突破", 0.0, 0.5, cfg.STRATEGY_WEIGHTS['volume_breakout'], 0.05)
    w_ma = st.slider("均线趋势", 0.0, 0.5, cfg.STRATEGY_WEIGHTS['ma_trend'], 0.05)

    total_w = w_rsi + w_macd + w_bb + w_vol + w_ma
    if total_w > 0:
        engine.weights = {
            'rsi_reversal': w_rsi / total_w,
            'macd_cross': w_macd / total_w,
            'bollinger_squeeze': w_bb / total_w,
            'volume_breakout': w_vol / total_w,
            'ma_trend': w_ma / total_w,
        }

    st.divider()

    # 自动刷新
    auto_refresh = st.checkbox("🔄 自动刷新", value=False)
    refresh_interval = st.slider("刷新间隔(秒)", 10, 120, cfg.AUTO_REFRESH_SEC, 10)

    if st.button("🔄 立即刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(cfg.PRODUCT_COPYRIGHT)
    st.caption("⚠️ 仅供参考，不构成投资建议")


# ═══════════════════════════════════════════════════════════════
#  顶部横幅
# ═══════════════════════════════════════════════════════════════
_live_class = 'live-green' if '交易中' in market_status else 'live-yellow' if '竞价' in market_status or '准备' in market_status or '午间' in market_status else 'live-red'
st.markdown(f"""
<div class="okx-banner">
    <h1>{cfg.PRODUCT_NAME} <span class="badge">v{cfg.PRODUCT_VERSION}</span></h1>
    <p class="sub">
        <span class="live-dot {_live_class}"></span>
        {market_status} · {cfg.PRODUCT_SLOGAN} · {datetime.now().strftime('%H:%M:%S')}
    </p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  数据获取
# ═══════════════════════════════════════════════════════════════
@st.cache_data(ttl=15)
def fetch_all_data(codes_tuple):
    """获取所有数据（缓存15秒）"""
    codes = list(codes_tuple)
    quotes = provider.get_batch_realtime(codes)
    signals = []

    for code in codes:
        info = cfg.ALL_INSTRUMENTS.get(code, {})
        name = info.get('name', code)
        market = info.get('market', 'SH')
        is_t0 = info.get('t0', False)

        df = provider.get_intraday_klines(code, period='5', days=5, market=market)
        if df is None or df.empty:
            df = provider.get_daily_klines(code, days=60)

        quote = quotes.get(code, {})
        price = quote.get('price', 0)
        if price <= 0 and df is not None and not df.empty:
            price = float(df['close'].iloc[-1])

        if price > 0 and df is not None and not df.empty:
            sig = engine.analyze(code, name, df, price, is_t0)
            signals.append(sig)

    return quotes, signals


if selected_codes:
    with st.spinner("正在获取实时数据并分析..."):
        quotes, signals = fetch_all_data(tuple(selected_codes))
else:
    quotes, signals = {}, []


# ═══════════════════════════════════════════════════════════════
#  Tab 页面
# ═══════════════════════════════════════════════════════════════
tab_names = ["📊 实时看板", "🎯 交易信号", "📈 技术图表", "🌍 宏观分析"]
if tier_features.get('backtest'):
    tab_names.append("📉 策略回测")
tab_names.append("📋 交易日志")
tab_names.append("ℹ️ 关于")

tabs = st.tabs(tab_names)
tab_idx = 0


# ────────────────────────────────────────────────────────────
#  Tab: 实时看板
# ────────────────────────────────────────────────────────────
with tabs[tab_idx]:
    tab_idx += 1

    st.markdown("### 📊 黄金板块实时行情总览")

    if quotes:
        # 统计 KPI
        up_count = sum(1 for q in quotes.values() if q.get('change_pct', 0) > 0)
        down_count = sum(1 for q in quotes.values() if q.get('change_pct', 0) < 0)
        flat_count = len(quotes) - up_count - down_count
        total_amount = sum(q.get('amount', 0) for q in quotes.values())

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("监控标的", f"{len(quotes)} 只")
        c2.metric("🟢 上涨", f"{up_count} 只")
        c3.metric("🔴 下跌", f"{down_count} 只")
        c4.metric("⚪ 平盘", f"{flat_count} 只")
        c5.metric("总成交额", f"{total_amount/1e8:.1f} 亿")

        # 行情表格
        rows = []
        for code in selected_codes:
            q = quotes.get(code, {})
            if not q:
                continue
            info = cfg.ALL_INSTRUMENTS.get(code, {})
            type_labels = {'ETF': '📦 ETF', 'FUND': '💼 基金', 'STOCK': '📈 股票'}
            rows.append({
                '代码': code,
                '名称': q.get('name', info.get('name', '')),
                '类型': type_labels.get(info.get('type', ''), ''),
                '最新价': q['price'],
                '涨跌幅(%)': q.get('change_pct', 0),
                '成交额(万)': round(q.get('amount', 0) / 1e4, 1),
                '换手率(%)': q.get('turnover_rate', 0),
                '振幅(%)': q.get('amplitude', 0),
                'T+0': '✅' if info.get('t0') else '❌',
            })

        if rows:
            df_table = pd.DataFrame(rows)
            st.dataframe(
                df_table,
                column_config={
                    '最新价': st.column_config.NumberColumn('最新价(¥)', format="%.3f"),
                    '涨跌幅(%)': st.column_config.NumberColumn('涨跌幅(%)', format="%.2f%%"),
                    '成交额(万)': st.column_config.NumberColumn('成交额(万)', format="%.1f"),
                },
                hide_index=True,
                use_container_width=True,
            )

        # 涨跌幅分布图
        st.markdown("### 📊 涨跌幅分布")
        if rows:
            chart_data = pd.DataFrame(rows)
            fig_bar = go.Figure()
            colors = ['#22c55e' if x >= 0 else '#ef4444' for x in chart_data['涨跌幅(%)']]
            fig_bar.add_trace(go.Bar(
                x=chart_data['名称'],
                y=chart_data['涨跌幅(%)'],
                marker_color=colors,
                text=[f"{v:+.2f}%" for v in chart_data['涨跌幅(%)']],
                textposition='outside',
            ))
            fig_bar.update_layout(
                height=350,
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(11,14,17,0.8)',
                yaxis_title='涨跌幅(%)',
                margin=dict(l=50, r=20, t=30, b=60),
                font=dict(color='#9ca3af', family='Inter'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.04)', zerolinecolor='rgba(255,255,255,0.08)'),
                xaxis=dict(gridcolor='rgba(255,255,255,0.04)'),
                bargap=0.3,
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("请在侧边栏选择监控标的")

    # 信号摘要
    st.markdown("### 🎯 交易信号快报")
    if signals:
        buy_signals = [s for s in signals if s.direction == 'BUY']
        sell_signals = [s for s in signals if s.direction == 'SELL']
        hold_signals = [s for s in signals if s.direction == 'HOLD']

        col_b, col_s, col_h = st.columns(3)
        with col_b:
            st.markdown(f"#### 🟢 买入信号 ({len(buy_signals)})")
            for sig in buy_signals:
                urg = {'CRITICAL': '🔥', 'HIGH': '⚡'}.get(sig.urgency, '')
                regime_tag = {'REVERSAL': '🚗倒车接人', 'TREND_UP': '📈趋势'}.get(sig.regime, '')
                pat_tag = ' '.join(p['name'] for p in sig.patterns[:2]) if sig.patterns else ''
                st.success(
                    f"{urg} **{sig.name}**（{sig.code}）{regime_tag}\n\n"
                    f"评分: **{sig.score:+.2f}** | 置信度: **{sig.confidence:.0%}** | "
                    f"盈亏比: **{sig.risk_reward}:1**\n\n"
                    f"入场: ¥{sig.entry_price:.3f} | "
                    f"止损: ¥{sig.stop_loss:.3f} | "
                    f"止盈: ¥{sig.take_profit:.3f}"
                    + (f"\n\n🕯️ {pat_tag}" if pat_tag else "")
                )
        with col_s:
            st.markdown(f"#### 🔴 卖出信号 ({len(sell_signals)})")
            for sig in sell_signals:
                pat_tag = ' '.join(p['name'] for p in sig.patterns[:2]) if sig.patterns else ''
                st.error(
                    f"**{sig.name}**（{sig.code}）\n\n"
                    f"评分: **{sig.score:+.2f}** | 置信度: **{sig.confidence:.0%}**\n\n"
                    f"建议减仓"
                    + (f"\n\n🕯️ {pat_tag}" if pat_tag else "")
                )
        with col_h:
            st.markdown(f"#### ⚪ 观望 ({len(hold_signals)})")
            for sig in hold_signals:
                regime_tag = {'RANGE': '↔️震荡', 'CRASH': '💥暴跌中'}.get(sig.regime, '')
                st.info(f"**{sig.name}**（{sig.code}）{regime_tag}\n\n{sig.reason[:60]}")
    else:
        st.info("暂无信号数据，等待分析...")


# ────────────────────────────────────────────────────────────
#  Tab: 详细交易信号
# ────────────────────────────────────────────────────────────
with tabs[tab_idx]:
    tab_idx += 1

    st.markdown("### 🎯 详细策略分析报告")

    if signals:
        for sig in signals:
            direction_text = {'BUY': '🟢 建议买入', 'SELL': '🔴 建议卖出', 'HOLD': '⚪ 观望'}
            urgency_text = {'CRITICAL': '🔥 紧急', 'HIGH': '⚡ 较强',
                           'NORMAL': '📊 一般', 'LOW': '💤 较弱'}

            icon = '🟢' if sig.direction == 'BUY' else '🔴' if sig.direction == 'SELL' else '⚪'

            with st.expander(
                f"{icon} {sig.name}（{sig.code}）— {direction_text[sig.direction]} "
                f"| 评分 {sig.score:+.2f} | 置信度 {sig.confidence:.0%}",
                expanded=(sig.direction != 'HOLD')
            ):
                # KPI 行
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.metric("综合评分", f"{sig.score:+.2f}")
                c2.metric("置信度", f"{sig.confidence:.0%}")
                c3.metric("信号强度", urgency_text.get(sig.urgency, ''))
                c4.metric("交易模式", "T+0 日内" if sig.is_t0 else "T+1 隔日")
                regime_icons = {'TREND_UP': '📈', 'TREND_DOWN': '📉', 'RANGE': '↔️',
                               'CRASH': '💥', 'REVERSAL': '🚗'}
                c5.metric("行情识别", f"{regime_icons.get(sig.regime, '')} {sig.regime}")
                if sig.risk_reward > 0:
                    c6.metric("盈亏比", f"{sig.risk_reward}:1")

                # 入场 / 止损 / 止盈
                if sig.direction != 'HOLD':
                    ce, csl, ctp = st.columns(3)
                    ce.metric("📍 建议入场价", f"¥{sig.entry_price:.3f}")
                    csl.metric("🛑 止损价", f"¥{sig.stop_loss:.3f}")
                    ctp.metric("🎯 止盈价", f"¥{sig.take_profit:.3f}")

                    if sig.is_t0:
                        st.info(f"💡 该标的支持日内T+0，可于 {cfg.INTRADAY_FORCE_EXIT} 前择机平仓")
                    else:
                        st.warning("⚠️ T+1标的，今日买入次日方可卖出，请控制仓位")

                # 行情识别 + K线形态 + 宏观
                if sig.regime_desc:
                    regime_color = {'TREND_UP': 'green', 'REVERSAL': 'green',
                                   'CRASH': 'red', 'TREND_DOWN': 'orange'}.get(sig.regime, 'blue')
                    st.info(f"🔍 **行情识别:** {sig.regime_desc}")

                if sig.patterns:
                    pat_str = " | ".join(
                        f"{'🟢' if p['type']=='bullish' else '🔴' if p['type']=='bearish' else '⚪'} "
                        f"**{p['name']}**（{p['desc']}）"
                        for p in sig.patterns
                    )
                    st.markdown(f"🕯️ **K线形态:** {pat_str}")

                if sig.macro_bias != 0:
                    macro_icon = '🟢' if sig.macro_bias > 0 else '🔴'
                    st.markdown(f"{macro_icon} **宏观偏向:** {sig.macro_bias:+.3f}")

                st.markdown(f"**📝 分析依据:** {sig.reason}")

                # 策略投票明细表
                st.markdown("#### 📊 七维策略投票")
                strategy_data = []
                for sname, sdata in sig.strategies.items():
                    w = engine.weights.get(sname, 0)
                    strategy_data.append({
                        '策略': sname.replace('_', ' ').title(),
                        '信号值': sdata['signal'],
                        '权重': f"{w:.0%}",
                        '加权贡献': round(sdata['signal'] * w, 4),
                        '说明': sdata['reason'],
                    })

                df_strat = pd.DataFrame(strategy_data)
                st.dataframe(
                    df_strat,
                    column_config={
                        '信号值': st.column_config.ProgressColumn(
                            '信号强度', min_value=-1, max_value=1, format="%.2f"),
                    },
                    hide_index=True, use_container_width=True,
                )

                # 雷达图
                cats = [s['策略'] for s in strategy_data]
                vals = [abs(s['信号值']) for s in strategy_data]
                vals.append(vals[0])
                cats.append(cats[0])

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals, theta=cats, fill='toself',
                    line=dict(color='#ffd700', width=2),
                    fillcolor='rgba(255,215,0,0.08)',
                    marker=dict(size=6, color='#ffd700'),
                ))
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 1],
                                       gridcolor='rgba(255,255,255,0.06)',
                                       tickfont=dict(size=9, color='#6b7280')),
                        angularaxis=dict(gridcolor='rgba(255,255,255,0.04)',
                                        tickfont=dict(size=10, color='#9ca3af')),
                        bgcolor='rgba(0,0,0,0)',
                    ),
                    showlegend=False, height=300,
                    margin=dict(l=60, r=60, t=30, b=30),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#9ca3af', family='Inter'),
                )
                st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("暂无信号")


# ────────────────────────────────────────────────────────────
#  Tab: 技术图表
# ────────────────────────────────────────────────────────────
with tabs[tab_idx]:
    tab_idx += 1

    st.markdown("### 📈 专业技术分析图表")

    chart_code = st.selectbox(
        "选择标的",
        options=selected_codes,
        format_func=lambda x: f"{cfg.ALL_INSTRUMENTS.get(x, {}).get('name', x)}（{x}）",
    ) if selected_codes else None

    chart_period = st.radio(
        "K线周期",
        ['5分钟', '15分钟', '30分钟', '60分钟', '日线'],
        horizontal=True,
    )
    period_map = {'5分钟': '5', '15分钟': '15', '30分钟': '30',
                  '60分钟': '60', '日线': 'daily'}

    if chart_code:
        period_val = period_map[chart_period]
        if period_val == 'daily':
            chart_df = provider.get_daily_klines(chart_code, days=120)
        else:
            chart_df = provider.get_intraday_klines(chart_code, period=period_val, days=5)

        if chart_df is not None and not chart_df.empty:
            close = chart_df['close']
            high = chart_df['high']
            low = chart_df['low']
            vol = chart_df['volume']

            # 计算指标
            rsi = ti.rsi(close)
            dif, dea, hist = ti.macd(close)
            bb_u, bb_m, bb_l = ti.bollinger_bands(close)
            mas = ti.moving_averages(close, [5, 20, 60])
            k_val, d_val, j_val = ti.kdj(high, low, close)

            # 子图
            fig = make_subplots(
                rows=4, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.45, 0.15, 0.2, 0.2],
                subplot_titles=('K线 + 均线 + 布林带', '成交量', 'MACD', 'RSI / KDJ'),
            )

            # K线
            fig.add_trace(go.Candlestick(
                x=chart_df['timestamp'],
                open=chart_df['open'], high=chart_df['high'],
                low=chart_df['low'], close=chart_df['close'],
                name='K线',
                increasing_line_color='#ef5350', decreasing_line_color='#26a69a',
                increasing_fillcolor='#ef5350', decreasing_fillcolor='#26a69a',
            ), row=1, col=1)

            # 均线
            ma_colors = {'MA5': '#ffd700', 'MA20': '#ff6b6b', 'MA60': '#4ecdc4'}
            for ma_name, ma_s in mas.items():
                fig.add_trace(go.Scatter(
                    x=chart_df['timestamp'], y=ma_s,
                    name=ma_name, line=dict(color=ma_colors.get(ma_name, '#888'), width=1),
                ), row=1, col=1)

            # 布林带
            fig.add_trace(go.Scatter(
                x=chart_df['timestamp'], y=bb_u,
                name='布林上轨', line=dict(color='rgba(255,215,0,0.3)', dash='dash', width=1),
            ), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=chart_df['timestamp'], y=bb_l,
                name='布林下轨', line=dict(color='rgba(255,215,0,0.3)', dash='dash', width=1),
                fill='tonexty', fillcolor='rgba(255,215,0,0.04)',
            ), row=1, col=1)

            # 成交量
            vol_colors = ['#ef5350' if chart_df['close'].iloc[i] >= chart_df['open'].iloc[i]
                          else '#26a69a' for i in range(len(chart_df))]
            fig.add_trace(go.Bar(
                x=chart_df['timestamp'], y=chart_df['volume'],
                name='成交量', marker_color=vol_colors, opacity=0.7,
            ), row=2, col=1)

            # MACD
            hist_clean = hist.dropna()
            macd_colors = ['#ef5350' if v >= 0 else '#26a69a' for v in hist_clean.values]
            fig.add_trace(go.Bar(
                x=chart_df['timestamp'].iloc[-len(hist_clean):],
                y=hist_clean.values,
                name='MACD柱', marker_color=macd_colors, opacity=0.7,
            ), row=3, col=1)
            fig.add_trace(go.Scatter(
                x=chart_df['timestamp'], y=dif, name='DIF',
                line=dict(color='#ffd700', width=1),
            ), row=3, col=1)
            fig.add_trace(go.Scatter(
                x=chart_df['timestamp'], y=dea, name='DEA',
                line=dict(color='#ff6b6b', width=1),
            ), row=3, col=1)

            # RSI
            fig.add_trace(go.Scatter(
                x=chart_df['timestamp'], y=rsi, name='RSI(14)',
                line=dict(color='#ffd700', width=1.5),
            ), row=4, col=1)
            fig.add_hline(y=cfg.RSI_OVERBOUGHT, line_dash="dash",
                         line_color="red", opacity=0.5, row=4, col=1)
            fig.add_hline(y=cfg.RSI_OVERSOLD, line_dash="dash",
                         line_color="green", opacity=0.5, row=4, col=1)

            chart_name = cfg.ALL_INSTRUMENTS.get(chart_code, {}).get('name', chart_code)
            fig.update_layout(
                title=dict(text=f'{chart_name}（{chart_code}）· {chart_period}',
                          font=dict(size=16, color='#e5e7eb')),
                height=850,
                template='plotly_dark',
                xaxis_rangeslider_visible=False,
                showlegend=True,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                           font=dict(size=11, color='#9ca3af')),
                margin=dict(l=50, r=20, t=80, b=30),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(11,14,17,0.6)',
                font=dict(family='Inter', color='#9ca3af'),
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)',
                            tickfont=dict(size=10))
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)',
                            tickfont=dict(size=10))

            st.plotly_chart(fig, use_container_width=True)

            # 关键指标面板
            st.markdown("#### 📊 当前关键指标")
            ci1, ci2, ci3, ci4, ci5, ci6 = st.columns(6)

            rsi_val = float(rsi.iloc[-1]) if not rsi.empty and not pd.isna(rsi.iloc[-1]) else 50
            dif_val = float(dif.iloc[-1]) if not dif.empty and not pd.isna(dif.iloc[-1]) else 0
            k_now = float(k_val.iloc[-1]) if not k_val.empty and not pd.isna(k_val.iloc[-1]) else 50
            d_now = float(d_val.iloc[-1]) if not d_val.empty and not pd.isna(d_val.iloc[-1]) else 50

            ci1.metric("RSI(14)", f"{rsi_val:.1f}",
                      delta="超卖" if rsi_val < 30 else "超买" if rsi_val > 70 else "中性")
            ci2.metric("MACD DIF", f"{dif_val:.4f}")
            ci3.metric("K值", f"{k_now:.1f}")
            ci4.metric("D值", f"{d_now:.1f}")
            ci5.metric("MA5", f"¥{float(mas['MA5'].iloc[-1]):.3f}" if not mas['MA5'].empty else '-')
            ci6.metric("MA20", f"¥{float(mas['MA20'].iloc[-1]):.3f}" if not mas['MA20'].empty else '-')
        else:
            st.warning(f"未获取到 {chart_code} 的K线数据")
    else:
        st.info("请在侧边栏选择监控标的")


# ────────────────────────────────────────────────────────────
#  Tab: 宏观分析
# ────────────────────────────────────────────────────────────
with tabs[tab_idx]:
    tab_idx += 1

    st.markdown("### 🌍 黄金宏观面分析")
    st.markdown("*整合国际金价、上海金价、板块资金流向等数据，综合判断宏观环境对黄金的影响*")

    if st.button("🔄 刷新宏观数据", key='refresh_macro'):
        st.cache_data.clear()

    try:
        macro_analyzer = engine.macro_analyzer
        macro_data = macro_analyzer.get_macro_bias()

        # 宏观偏向 KPI
        mc1, mc2, mc3 = st.columns(3)
        bias = macro_data['bias']
        bias_icon = '🟢 利多' if bias > 0.1 else '🔴 利空' if bias < -0.1 else '⚪ 中性'
        mc1.metric("宏观偏向", f"{bias:+.3f}", delta=bias_icon)
        mc2.metric("宏观置信度", f"{macro_data['confidence']:.0%}")
        mc3.metric("综合判断", macro_data['summary'])

        # 各因素明细
        st.markdown("#### 📋 宏观因素明细")
        factors = macro_data.get('factors', {})

        # 国际金价
        if 'intl_gold' in factors:
            gold = factors['intl_gold']
            st.markdown(f"**🥇 国际金价:** ${gold.get('price', 0):.2f}/盎司 "
                       f"({gold.get('change_pct', 0):+.2f}%)")

        if 'gold_signal' in factors:
            st.markdown(f"  → {factors['gold_signal']}")

        # 上海金
        if 'shanghai_gold' in factors:
            shau = factors['shanghai_gold']
            st.markdown(f"**🏛️ 上海金价 (AU9999):** ¥{shau.get('price', 0):.2f}/克 "
                       f"（{shau.get('date', '')}）")

        # 板块资金流向
        if 'sector_flow' in factors:
            flow = factors['sector_flow']
            net = flow.get('net_inflow', 0)
            flow_icon = '🟢' if net > 0 else '🔴'
            st.markdown(f"**{flow_icon} 黄金板块资金流向:** "
                       f"{'净流入' if net > 0 else '净流出'} "
                       f"¥{abs(net)/1e8:.2f}亿")
        if 'flow_signal' in factors:
            st.markdown(f"  → {factors['flow_signal']}")

        # 行情识别
        st.markdown("---")
        st.markdown("#### 🔍 行情类型识别")

        if signals:
            for sig in signals[:3]:  # 前3个
                regime_icons = {'TREND_UP': '📈 上涨趋势', 'TREND_DOWN': '📉 下跌趋势',
                               'RANGE': '↔️ 震荡', 'CRASH': '💥 暴跌', 'REVERSAL': '🚗 反转'}
                regime_text = regime_icons.get(sig.regime, sig.regime)
                st.markdown(f"**{sig.name}（{sig.code}）:** {regime_text} — {sig.regime_desc}")

                # 历史相似行情
                regime_detector = engine.regime_detector
                info = cfg.ALL_INSTRUMENTS.get(sig.code, {})
                market = info.get('market', 'SH')
                df_check = provider.get_intraday_klines(sig.code, period='5', days=5, market=market)
                if df_check is not None and len(df_check) >= 20:
                    regime_result = regime_detector.detect(df_check)
                    if regime_result.get('similar_history'):
                        for h in regime_result['similar_history']:
                            st.caption(f"  📜 历史参考: {h['period']} — {h['pattern']} → {h['outcome']} "
                                      f"（相似度{h['similarity']:.0%}）建议: {h['advice']}")

    except Exception as e:
        st.warning(f"宏观数据获取失败: {e}")
        st.info("宏观分析需要网络连接，部分数据在非交易时段可能不可用")


# ────────────────────────────────────────────────────────────
#  Tab: 策略回测（PRO+）
# ────────────────────────────────────────────────────────────
if tier_features.get('backtest'):
    with tabs[tab_idx]:
        tab_idx += 1

        st.markdown("### 📉 策略历史回测")

        bt_code = st.selectbox(
            "回测标的",
            options=selected_codes,
            format_func=lambda x: f"{cfg.ALL_INSTRUMENTS.get(x, {}).get('name', x)}（{x}）",
            key='bt_code',
        ) if selected_codes else None

        col_bt1, col_bt2 = st.columns(2)
        with col_bt1:
            bt_days = st.slider("回测天数", 30, 180, 90, key='bt_days')
        with col_bt2:
            bt_initial = st.number_input("初始资金(万)", 1.0, 1000.0, 10.0, 1.0, key='bt_init')

        if bt_code and st.button("🚀 开始回测", use_container_width=True, type="primary"):
            with st.spinner("正在回测..."):
                bt_df = provider.get_daily_klines(bt_code, days=bt_days)

                if bt_df is not None and len(bt_df) >= 30:
                    close_arr = bt_df['close'].values
                    rsi_series = ti.rsi(bt_df['close'])
                    dif_s, dea_s, hist_s = ti.macd(bt_df['close'])

                    trades = []
                    position = 0
                    entry_price = 0
                    total_pnl = 0
                    equity_curve = [bt_initial * 10000]  # 转为元
                    cash = bt_initial * 10000
                    shares = 0

                    for i in range(30, len(bt_df)):
                        rsi_v = float(rsi_series.iloc[i]) if not pd.isna(rsi_series.iloc[i]) else 50
                        dif_v = float(dif_s.iloc[i]) if not pd.isna(dif_s.iloc[i]) else 0
                        dea_v = float(dea_s.iloc[i]) if not pd.isna(dea_s.iloc[i]) else 0
                        dif_p = float(dif_s.iloc[i-1]) if not pd.isna(dif_s.iloc[i-1]) else 0
                        dea_p = float(dea_s.iloc[i-1]) if not pd.isna(dea_s.iloc[i-1]) else 0
                        price_now = close_arr[i]

                        if position == 0:
                            if rsi_v < 35 or (dif_p <= dea_p and dif_v > dea_v):
                                # 买入（全仓）
                                shares = int(cash / price_now / 100) * 100
                                if shares >= 100:
                                    cost = shares * price_now
                                    fee = cost * 0.00025  # 手续费万2.5
                                    cash -= (cost + fee)
                                    position = 1
                                    entry_price = price_now
                                    trades.append({
                                        '日期': str(bt_df['timestamp'].iloc[i])[:10],
                                        '操作': '买入',
                                        '价格': round(price_now, 3),
                                        '数量': shares,
                                        '金额': round(cost, 0),
                                        '收益(%)': '',
                                    })

                        elif position == 1:
                            pnl_pct = (price_now - entry_price) / entry_price
                            if (rsi_v > 65 or
                                (dif_p >= dea_p and dif_v < dea_v) or
                                pnl_pct <= -cfg.STOP_LOSS_PCT or
                                pnl_pct >= cfg.TAKE_PROFIT_PCT):
                                # 卖出
                                revenue = shares * price_now
                                fee = revenue * 0.00125  # 印花税+手续费
                                cash += (revenue - fee)
                                pnl = pnl_pct * 100
                                total_pnl += pnl
                                trades.append({
                                    '日期': str(bt_df['timestamp'].iloc[i])[:10],
                                    '操作': '卖出',
                                    '价格': round(price_now, 3),
                                    '数量': shares,
                                    '金额': round(revenue, 0),
                                    '收益(%)': f"{pnl:+.2f}%",
                                })
                                shares = 0
                                position = 0

                        total_val = cash + shares * price_now
                        equity_curve.append(total_val)

                    # 回测结果
                    sell_trades = [t for t in trades if t['操作'] == '卖出']
                    win_trades = [t for t in sell_trades
                                  if t['收益(%)'] and float(t['收益(%)'].replace('%', '').replace('+', '')) > 0]
                    total_trades = len(sell_trades)
                    win_rate = len(win_trades) / total_trades * 100 if total_trades > 0 else 0
                    final_val = equity_curve[-1]
                    total_return = (final_val / (bt_initial * 10000) - 1) * 100

                    max_dd = 0
                    peak = equity_curve[0]
                    for val in equity_curve:
                        peak = max(peak, val)
                        dd = (val / peak - 1) * 100
                        max_dd = min(max_dd, dd)

                    # KPI
                    cr1, cr2, cr3, cr4, cr5 = st.columns(5)
                    cr1.metric("总交易", f"{total_trades} 次")
                    cr2.metric("胜率", f"{win_rate:.1f}%")
                    cr3.metric("总收益", f"{total_return:+.2f}%",
                              delta="盈利" if total_return > 0 else "亏损")
                    cr4.metric("最大回撤", f"{max_dd:.2f}%")
                    cr5.metric("期末资金", f"¥{final_val:,.0f}")

                    # 净值曲线
                    fig_eq = go.Figure()
                    fig_eq.add_trace(go.Scatter(
                        y=[v / (bt_initial * 10000) for v in equity_curve],
                        mode='lines', name='策略净值',
                        line=dict(color='#ffd700', width=2),
                        fill='tozeroy', fillcolor='rgba(255,215,0,0.08)',
                    ))
                    fig_eq.update_layout(
                        title=dict(text=f'策略净值曲线（初始 {bt_initial:.0f}万）',
                                  font=dict(size=14, color='#e5e7eb')),
                        template='plotly_dark', height=400,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(11,14,17,0.6)',
                        yaxis_title='净值',
                        font=dict(color='#9ca3af', family='Inter'),
                        yaxis=dict(gridcolor='rgba(255,255,255,0.04)'),
                        xaxis=dict(gridcolor='rgba(255,255,255,0.04)'),
                    )
                    st.plotly_chart(fig_eq, use_container_width=True)

                    # 交易记录
                    if trades:
                        st.markdown("#### 📋 回测交易记录")
                        st.dataframe(pd.DataFrame(trades), hide_index=True,
                                    use_container_width=True)
                else:
                    st.warning("数据不足，无法回测")


# ────────────────────────────────────────────────────────────
#  Tab: 交易日志
# ────────────────────────────────────────────────────────────
with tabs[tab_idx]:
    tab_idx += 1

    st.markdown("### 📋 交易日志")

    # 用 session_state 管理日志
    if 'trade_journal' not in st.session_state:
        st.session_state.trade_journal = []

    st.markdown("#### ✏️ 记录新交易")
    jc1, jc2, jc3, jc4 = st.columns(4)
    with jc1:
        j_code = st.selectbox("标的", options=selected_codes,
                              format_func=lambda x: cfg.ALL_INSTRUMENTS.get(x, {}).get('name', x),
                              key='j_code')
    with jc2:
        j_action = st.selectbox("操作", ['买入', '卖出'], key='j_action')
    with jc3:
        j_price = st.number_input("价格", 0.0, 99999.0, 0.0, 0.001, key='j_price')
    with jc4:
        j_qty = st.number_input("数量(股)", 0, 1000000, 100, 100, key='j_qty')

    jc5, jc6 = st.columns(2)
    with jc5:
        j_reason = st.text_input("操作原因", key='j_reason')
    with jc6:
        j_note = st.text_input("备注", key='j_note')

    if st.button("📝 记录交易", use_container_width=True):
        if j_code and j_price > 0 and j_qty > 0:
            entry = {
                '时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '标的': f"{cfg.ALL_INSTRUMENTS.get(j_code, {}).get('name', j_code)}({j_code})",
                '操作': j_action,
                '价格': j_price,
                '数量': j_qty,
                '金额': round(j_price * j_qty, 2),
                '原因': j_reason,
                '备注': j_note,
            }
            st.session_state.trade_journal.append(entry)
            st.success("交易记录已保存!")
        else:
            st.warning("请完整填写交易信息")

    if st.session_state.trade_journal:
        st.markdown("#### 📖 历史记录")
        df_journal = pd.DataFrame(st.session_state.trade_journal)
        st.dataframe(df_journal, hide_index=True, use_container_width=True)

        if tier_features.get('export'):
            csv = df_journal.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 导出交易日志 (CSV)",
                csv,
                f"gold_trades_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True,
            )
    else:
        st.info("暂无交易记录。使用上方表单记录您的交易。")


# ────────────────────────────────────────────────────────────
#  Tab: 关于
# ────────────────────────────────────────────────────────────
with tabs[tab_idx]:
    tab_idx += 1

    st.markdown(f"""
### 🥇 {cfg.PRODUCT_NAME} v{cfg.PRODUCT_VERSION}
**{cfg.PRODUCT_SUBTITLE}**

{cfg.PRODUCT_SLOGAN}

---

#### 🎯 核心功能矩阵

| 功能模块 | 说明 | 版本要求 |
|----------|------|----------|
    | 📊 实时行情监控 | A股黄金ETF/基金/股票实时行情、涨跌排行 | 全版本 |
    | 🎯 智能交易信号 | 七维策略投票，BUY/SELL/HOLD 信号生成 | 全版本 |
    | 📈 专业技术图表 | K线+均线+MACD+RSI+布林带+KDJ 多指标 | 全版本 |
    | 🔍 行情智能识别 | 趋势/震荡/暴跌/反转 自适应行情判断 | 全版本 |
    | 🕯️ K线形态识别 | 锤子线/启明星/吞没/十字星 等经典形态 | 全版本 |
    | 🌍 宏观面分析 | 国际金价+上海金+板块资金流向 | 全版本 |
    | 📉 策略历史回测 | 自定义回测天数、模拟真实交易成本 | 标准版+ |
    | 📋 交易日志管理 | 记录交易、导出CSV | 专业版+ |
    | 🔔 信号推送通知 | 飞书/企业微信实时推送交易信号 | 专业版+ |
    | 🤖 AI辅助分析 | Gemini大模型智能研判 | 专业版+ |
    | ⚡ T+0日内策略 | 黄金ETF专属日内交易策略 | 全版本 |
    | 🛡️ 智能风控 | 止损止盈+仓位管理+日内交易限制 | 全版本 |

    ---

    #### 📊 七维策略引擎

    1. **RSI反转策略** — 超卖反弹 + 底背离检测
    2. **MACD交叉策略** — 金叉/死叉 + 零轴位置判断
    3. **布林带突破策略** — 压缩变盘 + 量能确认
    4. **量价突破策略** — 放量创新高 / 缩量蓄势
    5. **均线趋势策略** — 多头/空头排列 + 金叉死叉
    6. **KDJ金叉死叉** — 超买超卖 + J值极端判断
    7. **K线形态+行情** — 锤子线/启明星/吞没 + 行情自适应加成

    #### 🔍 智能行情识别（源自AURUM系统）

    | 行情类型 | 说明 | 策略调整 |
    |----------|------|----------|
    | 📈 TREND_UP | 上涨趋势 | 顺势加仓 |
    | 📉 TREND_DOWN | 下跌趋势 | 降低信号 |
    | ↔️ RANGE | 震荡 | 高抛低吸 |
    | 💥 CRASH | 暴跌 | 谨慎观望 |
    | 🚗 REVERSAL | 暴跌后反弹 | 倒车接人！|

---

#### 📦 支持标的
    """)

    st.markdown("**黄金ETF（支持T+0日内交易）:**")
    for code, info in cfg.GOLD_ETFS.items():
        st.markdown(f"- {info['name']}（{code}）— {info.get('desc', '')}")

    if cfg.GOLD_FUNDS:
        st.markdown("\n**黄金基金:**")
        for code, info in cfg.GOLD_FUNDS.items():
            st.markdown(f"- {info['name']}（{code}）— {info.get('desc', '')}")

    st.markdown("\n**黄金概念股（T+1）:**")
    for code, info in cfg.GOLD_STOCKS.items():
        st.markdown(f"- {info['name']}（{code}）— {info.get('desc', '')}")

    st.markdown(f"""
---

#### 💰 版本与定价

| 版本 | 标的数 | 实时刷新 | 回测 | 导出 | 推送 | AI分析 | 价格 |
|------|--------|----------|------|------|------|--------|------|
| 试用版 | 3只 | ❌ | ❌ | ❌ | ❌ | ❌ | 免费3天 |
| 标准版 | 6只 | ✅ | ✅ | ❌ | ❌ | ❌ | ¥299/年 |
| **专业版** | **20只** | ✅ | ✅ | ✅ | ✅ | ✅ | **¥599/年** |
| 企业版 | 不限 | ✅ | ✅ | ✅ | ✅ | ✅ | ¥1999/年 |

---

#### ⚠️ 免责声明

本系统仅提供基于技术分析的**参考建议**，**不构成任何投资建议或承诺**。
投资有风险，入市需谨慎。过往回测业绩不代表未来实际表现。
用户应根据自身风险承受能力独立做出投资决策。

---

📱 购买咨询微信: **{cfg.CONTACT_WECHAT}**
📧 技术支持: **{cfg.CONTACT_EMAIL}**

{cfg.PRODUCT_COPYRIGHT}
    """)

    # 授权信息
    st.divider()
    st.markdown("#### 🔑 当前授权信息")
    lc1, lc2, lc3 = st.columns(3)
    lc1.metric("授权等级", tier_features['name'])
    lc2.metric("剩余天数", f"{license_info['days_left']} 天")
    lc3.metric("设备指纹", license_info['machine_id'])


# ═══════════════════════════════════════════════════════════════
#  自动刷新
# ═══════════════════════════════════════════════════════════════
if auto_refresh and tier_features.get('realtime_refresh'):
    time.sleep(refresh_interval)
    st.rerun()
