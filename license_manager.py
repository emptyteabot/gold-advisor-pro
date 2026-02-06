"""
Gold Advisor Pro™ - 授权许可管理
支持云端部署（Streamlit Cloud）+ 本地部署双模式
"""
import hashlib
import json
import os
import platform
import uuid
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple

TRIAL_DAYS = 3

# ═══════════════════════════════════════════════════════════════
#  云端模式检测
# ═══════════════════════════════════════════════════════════════
def _is_cloud() -> bool:
    """检测是否运行在 Streamlit Cloud 上"""
    return os.environ.get('STREAMLIT_SHARING_MODE') == '1' or \
           os.environ.get('IS_CLOUD', '') == '1' or \
           not _license_file().parent.joinpath('.venv').exists()


def _license_file() -> Path:
    return Path(__file__).resolve().parent / '.license'


def _trial_file() -> Path:
    return Path(__file__).resolve().parent / '.trial'


def _get_machine_id() -> str:
    """获取设备唯一标识"""
    raw = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
    return hashlib.md5(raw.encode()).hexdigest()[:12].upper()


def _make_secret(seed: str) -> str:
    salt = "GoldAdvisorPro2026!@#"
    return hashlib.sha256(f"{salt}{seed}{salt}".encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════
#  授权码生成（卖家端）
# ═══════════════════════════════════════════════════════════════
def generate_license_key(machine_id: str = "CLOUD", days: int = 365,
                         tier: str = 'PRO') -> str:
    """生成授权码"""
    expire_ts = int(time.time()) + days * 86400
    payload = f"{machine_id}|{expire_ts}|{tier}"
    sig = _make_secret(payload)[:16].upper()
    raw = f"{sig}{hashlib.md5(payload.encode()).hexdigest()[:16].upper()}"
    key = f"GAP-{raw[:4]}-{raw[4:8]}-{raw[8:12]}-{raw[12:16]}"
    return key


# ═══════════════════════════════════════════════════════════════
#  授权码验证（云端模式：用 st.secrets 或环境变量存储有效 key 列表）
# ═══════════════════════════════════════════════════════════════
def _get_valid_keys() -> list:
    """获取有效授权码列表（云端从 secrets/环境变量读取）"""
    keys = []

    # 方式1：从 Streamlit secrets 读取
    try:
        import streamlit as st
        secret_keys = st.secrets.get("license_keys", {})
        if isinstance(secret_keys, dict):
            keys.extend(secret_keys.values())
        elif isinstance(secret_keys, (list, tuple)):
            keys.extend(secret_keys)
        # 也支持单个 master_key
        master = st.secrets.get("master_key", "")
        if master:
            keys.append(master)
    except Exception:
        pass

    # 方式2：从环境变量读取（逗号分隔）
    env_keys = os.environ.get('LICENSE_KEYS', '')
    if env_keys:
        keys.extend([k.strip() for k in env_keys.split(',') if k.strip()])

    master_env = os.environ.get('MASTER_KEY', '')
    if master_env:
        keys.append(master_env)

    return keys


def activate_license(key: str) -> Tuple[bool, str]:
    """激活授权码"""
    if not key or not key.startswith("GAP-"):
        return False, "❌ 授权码格式无效，请联系客服获取正确的授权码"

    # 云端模式：验证 key 是否在有效列表中
    valid_keys = _get_valid_keys()
    if valid_keys and key not in valid_keys:
        return False, "❌ 授权码无效，请确认后重试"

    # 尝试写入本地文件（本地模式）
    license_data = {
        'key': key,
        'machine_id': _get_machine_id(),
        'activated_at': datetime.now().isoformat(),
        'tier': 'PRO',
    }
    try:
        with open(_license_file(), 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # 云端可能无法写文件，没关系

    return True, "✅ 授权码激活成功！感谢您的购买。"


def check_license() -> Dict:
    """检查授权状态（兼容云端 + 本地）"""
    result = {
        'valid': False,
        'tier': 'TRIAL',
        'days_left': 0,
        'machine_id': _get_machine_id(),
        'message': '',
    }

    # ── 检查 Streamlit session_state（云端持久化） ──
    try:
        import streamlit as st
        if st.session_state.get('_license_activated'):
            result['valid'] = True
            result['tier'] = st.session_state.get('_license_tier', 'PRO')
            result['days_left'] = 365
            result['message'] = f"✅ 授权有效（{result['tier']}版）"
            return result
    except Exception:
        pass

    # ── 检查本地授权文件 ──
    lf = _license_file()
    if lf.exists():
        try:
            with open(lf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            key = data.get('key', '')
            activated_at = datetime.fromisoformat(data.get('activated_at', ''))
            if key.startswith("GAP-"):
                result['valid'] = True
                result['tier'] = data.get('tier', 'PRO')
                expire_date = activated_at + timedelta(days=365)
                result['days_left'] = max(0, (expire_date - datetime.now()).days)
                if result['days_left'] <= 0:
                    result['valid'] = False
                    result['message'] = "⚠️ 授权已过期，请续费"
                    result['tier'] = 'EXPIRED'
                else:
                    result['message'] = f"✅ 授权有效（{result['tier']}版）剩余 {result['days_left']} 天"
                return result
        except Exception:
            pass

    # ── 检查环境变量中是否有默认启用（云端免激活模式） ──
    if os.environ.get('AUTO_ACTIVATE', '') == '1':
        result['valid'] = True
        result['tier'] = os.environ.get('DEFAULT_TIER', 'PRO')
        result['days_left'] = 365
        result['message'] = f"✅ 云端授权（{result['tier']}版）"
        return result

    # ── 试用模式 ──
    tf = _trial_file()
    if tf.exists():
        try:
            with open(tf, 'r') as f:
                first_run = datetime.fromisoformat(f.read().strip())
            elapsed = (datetime.now() - first_run).days
            if elapsed < TRIAL_DAYS:
                result['valid'] = True
                result['tier'] = 'TRIAL'
                result['days_left'] = TRIAL_DAYS - elapsed
                result['message'] = f"🆓 试用模式（剩余 {result['days_left']} 天）"
            else:
                result['message'] = "⚠️ 试用期已结束，请购买授权码"
        except Exception:
            result['message'] = "⚠️ 请输入授权码激活"
    else:
        try:
            with open(tf, 'w') as f:
                f.write(datetime.now().isoformat())
            result['valid'] = True
            result['tier'] = 'TRIAL'
            result['days_left'] = TRIAL_DAYS
            result['message'] = f"🆓 欢迎！试用期 {TRIAL_DAYS} 天，全功能体验"
        except Exception:
            # 云端无法写文件 → 直接给试用
            result['valid'] = True
            result['tier'] = 'TRIAL'
            result['days_left'] = TRIAL_DAYS
            result['message'] = f"🆓 试用模式（{TRIAL_DAYS} 天）"

    return result


def activate_in_session(key: str, tier: str = 'PRO'):
    """在 Streamlit session_state 中激活（云端专用）"""
    try:
        import streamlit as st
        st.session_state['_license_activated'] = True
        st.session_state['_license_tier'] = tier
        st.session_state['_license_key'] = key
    except Exception:
        pass


def get_tier_features(tier: str) -> Dict:
    """获取各版本功能列表"""
    features = {
        'TRIAL': {
            'name': '试用版', 'max_watchlist': 3,
            'realtime_refresh': False, 'backtest': False,
            'export': False, 'notification': False,
            'ai_analysis': False, 'multi_strategy': True, 'price': '免费（3天）',
        },
        'STANDARD': {
            'name': '标准版', 'max_watchlist': 6,
            'realtime_refresh': True, 'backtest': True,
            'export': False, 'notification': False,
            'ai_analysis': False, 'multi_strategy': True, 'price': '¥299/年',
        },
        'PRO': {
            'name': '专业版', 'max_watchlist': 20,
            'realtime_refresh': True, 'backtest': True,
            'export': True, 'notification': True,
            'ai_analysis': True, 'multi_strategy': True, 'price': '¥599/年',
        },
        'ENTERPRISE': {
            'name': '企业版', 'max_watchlist': 999,
            'realtime_refresh': True, 'backtest': True,
            'export': True, 'notification': True,
            'ai_analysis': True, 'multi_strategy': True, 'price': '¥1999/年',
        },
    }
    return features.get(tier, features['TRIAL'])


if __name__ == "__main__":
    print("=" * 60)
    print("  Gold Advisor Pro™ - 授权码管理工具")
    print("=" * 60)
    print(f"\n📟 本机设备指纹: {_get_machine_id()}")

    status = check_license()
    print(f"\n📋 当前授权状态:")
    print(f"   {status['message']}")
    print(f"   等级: {status['tier']}")

    print(f"\n🔑 生成云端授权码:")
    for tier in ['STANDARD', 'PRO', 'ENTERPRISE']:
        key = generate_license_key("CLOUD", 365, tier)
        print(f"   {tier:12s}: {key}")

    print(f"\n💡 将授权码添加到 Streamlit Cloud secrets 或发给客户")
