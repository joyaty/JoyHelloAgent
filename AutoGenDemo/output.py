import streamlit as st
import requests
import time

# --- 配置部分 ---
PAGE_TITLE = "比特币实时行情"
PAGE_ICON = "₿"
API_URL = "https://api.coingecko.com/api/v3/simple/price"
REQUEST_TIMEOUT = 5
# 普通缓存时间，避免自动运行时频繁请求
NORMAL_CACHE_TTL = 60 

# --- 数据获取逻辑 (纯函数) ---

def get_bitcoin_price_from_api():
    """
    内部函数：实际执行 API 请求
    不包含 UI 操作，仅返回数据或抛出异常
    """
    params = {
        'ids': 'bitcoin',
        'vs_currencies': 'usd',
        'include_24hr_change': 'true'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        btc_data = data.get('bitcoin', {})
        price = btc_data.get('usd')
        change_24h = btc_data.get('usd_24h_change')
        
        if price is None or change_24h is None:
            raise ValueError("API 返回数据格式异常，缺少关键字段")
            
        return price, change_24h

    except requests.exceptions.RequestException as e:
        # 这里仅抛出异常，不显示 st.error，由 UI 层处理
        raise ConnectionError(f"网络请求失败: {e}")
    except ValueError as e:
        raise ValueError(f"数据解析失败: {e}")

@st.cache_data(ttl=NORMAL_CACHE_TTL)
def fetch_bitcoin_data(cache_key=None):
    """
    缓存层包装函数
    cache_key 参数用于强制刷新：当传入不同的值时，缓存失效
    """
    return get_bitcoin_price_from_api()

# --- UI 布局 ---

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="centered"
)

# 简单的 CSS 样式优化 (移除强制背景色，保证主题兼容性)
st.markdown("""
    <style>
        .main-title {
            text-align: center;
            padding-bottom: 20px;
        }
        /* 增加指标卡片的间距 */
        div[data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True
)

st.markdown(f"<h1 class='main-title'>{PAGE_ICON} {PAGE_TITLE}</h1>", unsafe_allow_html=True)

# --- 交互控制 ---

# 初始化 session state 用于存储刷新时间戳
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = 0

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # 点击刷新按钮时，更新 session_state 中的时间戳
    if st.button("🔄 立即刷新", use_container_width=True, type="primary"):
        st.session_state.last_refresh = time.time()
        st.rerun()

# --- 数据展示 ---

# 使用占位符在加载数据时保持布局稳定
placeholder = st.container()

with placeholder:
    # 根据是否有用户点击刷新，决定是否强制获取新数据
    # 如果刚刚点击了按钮，传入当前时间戳，使缓存失效
    # 否则传入 None，利用 TTL 缓存
    cache_key = st.session_state.last_refresh if st.session_state.last_refresh > 0 else None
    
    try:
        with st.spinner("正在同步市场数据..."):
            price, change_24h = fetch_bitcoin_data(cache_key)
        
        # 成功获取数据
        st.markdown("---")
        
        # 计算涨跌额
        change_amount = price * (change_24h / 100)
        
        # 决定颜色方向
        # 国际惯例：绿涨红跌
        # 中国惯例：红涨绿跌
        delta_color = "normal" # 绿涨红跌
        
        st.metric(
            label="Bitcoin (BTC) / USD", 
            value=f"${price:,.2f}", 
            delta=f"{change_24h:+.2f}% (24h)", 
            delta_color=delta_color
        )
        
        # 次要信息
        st.caption(f"24小时涨跌额: ${change_amount:+,.2f}")
        st.markdown("---")
        st.info("💡 数据来源: CoinGecko API | 仅供参考，不构成投资建议")
        
    except Exception as e:
        # 错误处理层
        st.markdown("---")
        st.error(f"⚠️ 获取数据失败: {str(e)}")
        st.metric("Bitcoin (BTC) / USD", "--", "--")
        st.markdown("---")

# 底部信息
st.markdown("<div style='text-align: center; color: #666; font-size: 0.8em;'>Powered by Streamlit & Python</div>", unsafe_allow_html=True)