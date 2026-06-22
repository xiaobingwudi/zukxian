# Al Brooks AI Study Tool (single-file Streamlit version)
# Requirements:
# pip install streamlit pandas plotly openai

import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from openai import OpenAI

# 设置页面配置 - 必须在Streamlit命令之前
st.set_page_config(page_title="Al Brooks AI Study Tool", layout="wide")


# --------------------- AI 功能模块 ---------------------

def get_client():
    """
    获取OpenAI客户端实例
    从session_state中获取API密钥，创建DeepSeek客户端
    如果未设置API密钥则返回None
    """
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def ask_ai(system_prompt, user_prompt):
    """
    向AI发送请求并获取响应
    参数:
        system_prompt: 系统提示词，定义AI角色和行为
        user_prompt: 用户问题
    返回:
        AI响应文本或错误信息
    """
    client = get_client()
    if not client:
        return "请先填写 DeepSeek API Key"

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI错误: {e}"


def ai_translate(text):
    """
    将英文交易术语翻译为专业中文
    保留Al Brooks的专用术语缩写
    """
    return ask_ai(
        "你是Al Brooks价格行为专家。保留术语缩写，翻译成专业中文。",
        text
    )


def ai_explain(text):
    """
    解释Al Brooks原文背后的市场含义
    提供交易逻辑和价格行为的深层解读
    """
    return ask_ai(
        "解释Al Brooks真正想表达的市场含义，不要逐词翻译。",
        text
    )


def ai_plain(text):
    """
    将专业交易内容改写为通俗易懂的语言
    适合初学者理解
    """
    return ask_ai(
        "把内容改写成普通交易员能看懂的大白话。",
        text
    )


# --------------------- JSON 数据处理模块 ---------------------

def load_all_cases(uploaded):
    """
    从上传的JSON文件中加载所有案例数据
    参数:
        uploaded: Streamlit上传的文件对象
    返回:
        data: 完整的JSON数据
        cases: 案例列表
    """
    data = json.loads(uploaded.getvalue().decode("utf-8"))

    # 处理可能的数组格式
    if isinstance(data, list):
        data = data[0]

    cases = data.get("cases", [])
    return data, cases


def load_case_by_id(cases, case_id):
    """
    根据案例ID加载特定的案例数据
    参数:
        cases: 所有案例列表
        case_id: 要加载的案例ID
    返回:
        case: 案例数据
        bars_df: K线数据DataFrame
        comments: 注释数据
    """
    for case in cases:
        if str(case.get("case_id", "")) == str(case_id):
            bars = pd.DataFrame(case.get("bars", []))
            comments = case.get("comments", {})
            return case, bars, comments
    return None, None, None


def save_json(data):
    """
    将数据保存为JSON格式字符串
    参数:
        data: 要保存的数据
    返回:
        JSON格式字符串
    """
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    return txt


# --------------------- UI 界面模块 ---------------------

# CSS样式
st.markdown("""
<style>
    /* 全局紧凑 */
    .block-container {
        padding-top: 0.3rem !important;
        padding-bottom: 0.1rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
        max-width: 100% !important;
    }

    /* 减少元素间距 */
    .element-container {
        margin-bottom: 0.05rem !important;
    }

    /* 紧凑的metric - 改为inline显示 */
    [data-testid="metric-container"] {
        padding: 0.02rem 0.1rem !important;
        margin: 0 !important;
        background: none !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 2px !important;
    }
    [data-testid="metric-container"] label {
        font-size: 0.55rem !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    [data-testid="metric-container"] div {
        font-size: 0.7rem !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 紧凑的按钮 */
    .stButton button {
        padding: 0.1rem 0.3rem !important;
        font-size: 0.7rem !important;
        min-height: 1.4rem !important;
        margin: 0 !important;
    }

    /* 紧凑的text area */
    .stTextArea textarea {
        font-size: 0.75rem !important;
        padding: 0.15rem !important;
        min-height: 1.5rem !important;
        line-height: 1.2 !important;
    }
    .stTextArea label {
        font-size: 0.7rem !important;
        margin-bottom: 0 !important;
    }

    /* 紧凑的列间距 */
    .row-widget.stColumns {
        gap: 0.02rem !important;
        margin: 0 !important;
    }

    /* 减少标题间距 */
    h1, h2, h3, h4, h5 {
        margin-top: 0.1rem !important;
        margin-bottom: 0.1rem !important;
        padding: 0 !important;
    }
    h1 {
        font-size: 1.2rem !important;
    }
    h3 {
        font-size: 0.85rem !important;
    }
    h4 {
        font-size: 0.75rem !important;
    }
    h5 {
        font-size: 0.7rem !important;
    }

    /* 紧凑的expander */
    .streamlit-expanderHeader {
        padding: 0.1rem 0.3rem !important;
        font-size: 0.7rem !important;
    }
    .streamlit-expanderContent {
        padding: 0.1rem 0.3rem !important;
    }

    /* 紧凑的caption */
    .caption, .stCaption {
        font-size: 0.55rem !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 减少sidebar间距 */
    section[data-testid="stSidebar"] > div {
        padding-top: 0.3rem !important;
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
    }
    section[data-testid="stSidebar"] label {
        font-size: 0.75rem !important;
    }

    /* 紧凑的进度条 */
    .stProgress {
        margin: 0 !important;
    }
    .stProgress > div {
        height: 0.5rem !important;
    }

    /* 紧凑的info/alert */
    .stAlert {
        padding: 0.2rem 0.5rem !important;
        margin: 0.1rem 0 !important;
        font-size: 0.75rem !important;
    }

    /* 紧凑的下载按钮 */
    .stDownloadButton button {
        padding: 0.1rem 0.3rem !important;
        font-size: 0.7rem !important;
        min-height: 1.4rem !important;
    }

    /* 减少分割线间距 */
    hr {
        margin: 0.2rem 0 !important;
    }

    /* 注释文本框全宽显示 */
    .comment-box {
        width: 100% !important;
        background-color: #f8f9fa;
        padding: 8px 12px !important;
        border-radius: 4px;
        border-left: 3px solid #ff6b6b;
        margin: 4px 0 !important;
        font-size: 0.85rem !important;
        line-height: 1.6 !important;
        word-wrap: break-word !important;
        white-space: pre-wrap !important;
    }
    
    /* 原文显示区域 */
    .original-text {
        width: 100% !important;
        padding: 6px 10px !important;
        background-color: #fff3cd;
        border-radius: 4px;
        border-left: 3px solid #ffc107;
        margin: 4px 0 !important;
        font-size: 0.85rem !important;
        line-height: 1.6 !important;
        word-wrap: break-word !important;
        white-space: pre-wrap !important;
    }

    /* 顶部状态栏样式 - 单行显示 */
    .top-status {
        background: #f8f9fa;
        padding: 2px 8px;
        border-radius: 4px;
        margin-bottom: 4px;
        border: 1px solid #e9ecef;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 4px 8px;
    }
    
    /* 状态项 */
    .status-item {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        font-size: 0.65rem;
        white-space: nowrap;
        padding: 1px 4px;
    }
    .status-item .label {
        color: #6c757d;
        font-size: 0.55rem;
    }
    .status-item .value {
        font-weight: 600;
        font-size: 0.7rem;
    }
    
    /* 价格信息在状态栏中 */
    .price-inline {
        display: inline-flex;
        gap: 4px;
        flex-wrap: wrap;
        align-items: center;
        font-size: 0.6rem !important;
        margin-left: 4px;
    }
    .price-inline-item {
        background: white;
        padding: 0px 4px;
        border-radius: 2px;
        border-left: 2px solid #dee2e6;
        font-size: 0.6rem !important;
        white-space: nowrap;
    }
    .price-inline-item strong {
        font-weight: 600;
        color: #495057;
        font-size: 0.55rem !important;
    }
    
    /* 注释状态标识 */
    .has-comment {
        color: #28a745;
        font-weight: 600;
    }
    .no-comment {
        color: #dc3545;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# 页面标题
st.title("📚 Al Brooks 逐K训练器")

# ---------------- 侧边栏配置 ----------------
with st.sidebar:
    st.markdown("### ⚙️ 配置")
    # API密钥输入框
    st.session_state["api_key"] = st.text_input(
        "API Key",
        type="password",
        value=st.session_state.get("api_key", ""),
        placeholder="输入API Key",
        label_visibility="collapsed"
    )

    # 文件上传
    file = st.file_uploader("📂 上传JSON", type=["json"], label_visibility="collapsed")

# 如果没有上传文件，显示提示信息
if not file:
    st.info("👈 请上传 JSON 文件")
    st.stop()

# 加载所有案例数据
all_data, all_cases = load_all_cases(file)

if not all_cases:
    st.error("未找到案例数据")
    st.stop()

# 获取所有案例的ID和标题，用于下拉选择
case_options = {}
for case in all_cases:
    case_id = case.get("case_id", "unknown")
    title = case.get("title", f"案例 {case_id}")
    case_options[f"{case_id}"] = case_id

# 案例选择下拉框
selected_case_id = st.sidebar.selectbox(
    "📋 案例",
    options=list(case_options.keys()),
    index=0,
    label_visibility="collapsed"
)

# 加载选中的案例
case, bars_df, comments = load_case_by_id(all_cases, selected_case_id)

if case is None:
    st.error(f"未找到案例 ID: {selected_case_id}")
    st.stop()

# 过滤编号0的空K线（盘前数据）
if 0 in bars_df["bar"].values:
    bar_zero = bars_df[bars_df["bar"] == 0]
    if bar_zero.empty or (bar_zero["open"].isna().all() and bar_zero["close"].isna().all()):
        bars_df = bars_df[bars_df["bar"] != 0]

# 获取所有K线编号
all_bars = sorted(bars_df["bar"].unique())
total_bars = len(all_bars)
max_bar = max(all_bars) if len(all_bars) > 0 else 0
min_bar = min(all_bars) if len(all_bars) > 0 else 0

# 计算价格范围用于图表
price_min = bars_df["low"].min()
price_max = bars_df["high"].max()
price_padding = (price_max - price_min) * 0.05

# 获取有注释的K线列表
comment_bars = sorted([int(x) for x in comments.keys() if int(x) > 0])

# 获取第一根正数K线（排除0号）
first_positive_bar = min([b for b in all_bars if b > 0]) if any(b > 0 for b in all_bars) else None

# 初始化当前K线状态
if "current_bar" not in st.session_state or st.session_state.get("case_id") != selected_case_id:
    if first_positive_bar is not None:
        st.session_state.current_bar = first_positive_bar
    else:
        st.session_state.current_bar = max_bar if max_bar > 0 else 1
    st.session_state.case_id = selected_case_id

# 确保当前K线在有效范围内
if st.session_state.current_bar > max_bar:
    st.session_state.current_bar = first_positive_bar if first_positive_bar is not None else max_bar

if first_positive_bar is not None and st.session_state.current_bar < first_positive_bar:
    st.session_state.current_bar = first_positive_bar

# =======================
# 顶部状态栏 - 单行显示所有信息
# =======================
# 获取当前K线数据
current_row = bars_df[bars_df["bar"] == st.session_state.current_bar]
current_price_info = ""
if not current_row.empty:
    row = current_row.iloc[0]
    change = row['close'] - row['open']
    change_pct = (change / row['open'] * 100) if row['open'] != 0 else 0
    is_up = row['close'] > row['open']
    color_style = '#28a745' if is_up else '#dc3545'
    current_price_info = f"""
    <span class="price-inline-item"><strong>开</strong>{row['open']:.2f}</span>
    <span class="price-inline-item"><strong>高</strong>{row['high']:.2f}</span>
    <span class="price-inline-item"><strong>低</strong>{row['low']:.2f}</span>
    <span class="price-inline-item"><strong>收</strong>{row['close']:.2f}</span>
    <span class="price-inline-item" style="border-left-color: {color_style};">
        <strong>涨跌</strong> {change:+.2f}({change_pct:+.2f}%)
    </span>
    """

# 检查是否有注释
has_comment = str(st.session_state.current_bar) in comments and st.session_state.current_bar > 0
comment_status = '<span class="has-comment">✅</span>' if has_comment else '<span class="no-comment">❌</span>'

# 单行显示所有状态
st.markdown(f'''
<div class="top-status">
    <span class="status-item">
        <span class="label">Bar</span>
        <span class="value">{st.session_state.current_bar}</span>
    </span>
    <span class="status-item">
        <span class="label">总数</span>
        <span class="value">{total_bars}</span>
    </span>
    <span class="status-item">
        <span class="label">注释</span>
        <span class="value">{comment_status}</span>
    </span>
    <span class="status-item">
        <span class="label">ID</span>
        <span class="value">{selected_case_id}</span>
    </span>
    <span class="status-item">
        <span class="label">📅</span>
        <span class="value">{case.get('date', '')}</span>
    </span>
    <span class="status-item" style="flex:1;">
        <span class="label">{case.get('title', '')}</span>
    </span>
    <span class="price-inline">
        {current_price_info}
    </span>
</div>
''', unsafe_allow_html=True)

# 添加一个小间距
st.markdown("<br>", unsafe_allow_html=True)

# =======================
# K线图表绘制
# =======================
# 只显示到当前K线的数据
visible = bars_df[bars_df["bar"] <= st.session_state.current_bar]

# 获取当前K线的颜色
current_row = bars_df[bars_df["bar"] == st.session_state.current_bar]
if not current_row.empty:
    row = current_row.iloc[0]
    is_up = row["close"] > row["open"]
    color = "red" if is_up else "black"
else:
    color = "blue"

# 创建图表
fig = go.Figure()

# 分离阳线和阴线绘制
up_bars = visible[visible["close"] > visible["open"]]
down_bars = visible[visible["close"] <= visible["open"]]

# 绘制阳线（红色）
if not up_bars.empty:
    fig.add_trace(go.Candlestick(
        x=up_bars["bar"],
        open=up_bars["open"],
        high=up_bars["high"],
        low=up_bars["low"],
        close=up_bars["close"],
        name="阳线",
        showlegend=False,
        increasing_line_color="red",
        decreasing_line_color="red"
    ))

# 绘制阴线（黑色）
if not down_bars.empty:
    fig.add_trace(go.Candlestick(
        x=down_bars["bar"],
        open=down_bars["open"],
        high=down_bars["high"],
        low=down_bars["low"],
        close=down_bars["close"],
        name="阴线",
        showlegend=False,
        increasing_line_color="black",
        decreasing_line_color="black"
    ))

# 如果有盘前数据（负编号），添加分隔线
if min_bar < 0:
    fig.add_vline(x=0.5, line_width=1, line_color="gray", line_dash="dot")
    fig.add_annotation(
        x=0.5,
        y=price_max * 0.95,
        text="盘前 | 正式",
        showarrow=False,
        font=dict(size=8, color="gray")
    )

# 标记当前K线位置
fig.add_vline(
    x=st.session_state.current_bar,
    line_width=2,
    line_color=color,
    line_dash="dash"
)

# 如果当前K线有注释，在图表上显示简短标记
bar_str = str(st.session_state.current_bar)
if bar_str in comments and st.session_state.current_bar > 0:
    trans = comments[bar_str].get("translation", "")
    if trans:
        trans_preview = trans[:20] + "..." if len(trans) > 20 else trans
        current_k = visible[visible["bar"] == st.session_state.current_bar]
        if not current_k.empty:
            y_pos = current_k["high"].max() * 1.02
            fig.add_annotation(
                x=st.session_state.current_bar,
                y=y_pos,
                text=f"📝 {trans_preview}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="orange",
                font=dict(size=8)
            )

# 设置图表范围
x_min = min_bar - 0.5 if min_bar < 0 else -0.5
x_max = max_bar + 0.5

# 更新图表布局
fig.update_layout(
    height=350,
    margin=dict(l=3, r=3, t=20, b=15),
    xaxis_rangeslider_visible=False,
    showlegend=False,
    xaxis=dict(
        tickmode='linear',
        dtick=max(1, total_bars // 20),
        gridcolor='lightgray',
        gridwidth=0.5,
        range=[x_min, x_max],
        tickfont=dict(size=8)
    ),
    yaxis=dict(
        range=[price_min - price_padding, price_max + price_padding],
        gridcolor='lightgray',
        gridwidth=0.5,
        tickfont=dict(size=8)
    ),
    plot_bgcolor='white',
    paper_bgcolor='white'
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# -------- K线导航控制条 --------
current_idx = all_bars.index(st.session_state.current_bar) if st.session_state.current_bar in all_bars else 0
total = len(all_bars)

ctrl_cols = st.columns([0.5, 0.5, 0.5, 3, 0.5, 0.5])

with ctrl_cols[0]:
    if st.button("⏮", help="第一根"):
        st.session_state.current_bar = all_bars[0]
        st.rerun()

with ctrl_cols[1]:
    if st.button("◀", help="上一根"):
        if current_idx > 0:
            st.session_state.current_bar = all_bars[current_idx - 1]
            st.rerun()

with ctrl_cols[2]:
    if st.button("▶", help="下一根"):
        if current_idx < total - 1:
            st.session_state.current_bar = all_bars[current_idx + 1]
            st.rerun()

with ctrl_cols[3]:
    # 进度条显示当前位置
    progress = (current_idx + 1) / total if total > 0 else 0
    st.progress(progress, text=f"{current_idx + 1}/{total}")

with ctrl_cols[4]:
    if st.button("⏭", help="最后一根"):
        if current_idx < total - 1:
            st.session_state.current_bar = all_bars[-1]
            st.rerun()

with ctrl_cols[5]:
    # 快速跳转到有注释的K线
    if positive_comment_bars := [b for b in comment_bars if b > 0]:
        if st.button("💬跳", help="跳转到有注释的K线"):
            # 找下一个有注释的K线
            for b in positive_comment_bars:
                if b > st.session_state.current_bar:
                    st.session_state.current_bar = b
                    st.rerun()
            # 如果没有下一个，跳转到第一个
            st.session_state.current_bar = positive_comment_bars[0]
            st.rerun()

# =======================
# 下方信息面板 - 完整显示注释内容
# =======================

st.markdown("---")

bar_str = str(st.session_state.current_bar)

# 判断当前K线是否有注释
has_comment = st.session_state.current_bar > 0 and bar_str in comments

if has_comment:
    # 获取注释数据
    item = comments[bar_str]
    original_text = item.get("original", "")
    translation = item.get("translation", "")
    plain_text = item.get("plain", "")
    
    # 显示Bar编号和原文
    st.markdown(f"### 📊 Bar {bar_str} 注释内容")
    
    # 显示原文
    if original_text:
        st.markdown(f'<div class="original-text">📖 <b>原文:</b> {original_text}</div>', unsafe_allow_html=True)
    else:
        st.info("ℹ️ 此K线没有原文内容")
    
    # 显示已有的翻译（如果有）
    if translation:
        st.markdown(f'<div class="comment-box">📝 <b>翻译:</b> {translation}</div>', unsafe_allow_html=True)
    
    # 显示已有的白话解释（如果有）
    if plain_text:
        st.markdown(f'<div class="comment-box">💬 <b>白话:</b> {plain_text}</div>', unsafe_allow_html=True)

    # AI功能按钮
    st.markdown("---")
    st.markdown("#### 🤖 AI辅助功能")
    ai_cols = st.columns([1, 1, 1, 0.5, 0.5])
    
    with ai_cols[0]:
        if st.button("🌐 翻译", key="btn_t", use_container_width=True):
            if original_text:
                with st.spinner("AI正在翻译..."):
                    result = ai_translate(original_text)
                    st.session_state[f"trans_{bar_str}"] = result
                    # 自动保存到comments
                    comments[bar_str]["translation"] = result
                    for c in all_data["cases"]:
                        if str(c.get("case_id", "")) == str(selected_case_id):
                            c["comments"] = comments
                            break
                    st.rerun()
            else:
                st.warning("没有原文可翻译")
    
    with ai_cols[1]:
        if st.button("💡 解释", key="btn_e", use_container_width=True):
            if original_text:
                with st.spinner("AI正在解释..."):
                    result = ai_explain(original_text)
                    st.session_state[f"explain_{bar_str}"] = result
                    st.rerun()
            else:
                st.warning("没有原文可解释")
    
    with ai_cols[2]:
        if st.button("🗣️ 白话", key="btn_p", use_container_width=True):
            if original_text:
                with st.spinner("AI正在改写..."):
                    result = ai_plain(original_text)
                    st.session_state[f"plain_{bar_str}"] = result
                    # 自动保存到comments
                    comments[bar_str]["plain"] = result
                    for c in all_data["cases"]:
                        if str(c.get("case_id", "")) == str(selected_case_id):
                            c["comments"] = comments
                            break
                    st.rerun()
            else:
                st.warning("没有原文可改写")
    
    with ai_cols[3]:
        if st.button("💾", key="save_btn", help="保存所有编辑", use_container_width=True):
            # 从编辑框中获取内容并保存
            trans_edit = st.session_state.get(f"trans_edit_{bar_str}", comments[bar_str].get("translation", ""))
            plain_edit = st.session_state.get(f"plain_edit_{bar_str}", comments[bar_str].get("plain", ""))
            comments[bar_str]["translation"] = trans_edit
            comments[bar_str]["plain"] = plain_edit
            for c in all_data["cases"]:
                if str(c.get("case_id", "")) == str(selected_case_id):
                    c["comments"] = comments
                    break
            st.success("✅ 已保存")
            st.rerun()
    
    with ai_cols[4]:
        st.download_button(
            "📥",
            save_json(all_data),
            file_name=f"albrooks_{selected_case_id}_updated.json",
            mime="application/json",
            use_container_width=True,
            help="下载JSON"
        )

    # 显示AI生成的结果（如果有）
    ai_results = []
    if st.session_state.get(f"trans_{bar_str}"):
        ai_results.append(("翻译", st.session_state[f"trans_{bar_str}"]))
    if st.session_state.get(f"explain_{bar_str}"):
        ai_results.append(("解释", st.session_state[f"explain_{bar_str}"]))
    if st.session_state.get(f"plain_{bar_str}"):
        ai_results.append(("白话", st.session_state[f"plain_{bar_str}"]))

    if ai_results:
        st.markdown("---")
        st.markdown("#### 🤖 AI生成结果")
        for label, content in ai_results:
            st.markdown(f'<div class="comment-box">💡 <b>{label}:</b> {content}</div>', unsafe_allow_html=True)

    # 编辑区域
    st.markdown("---")
    st.markdown("#### ✏️ 编辑注释")
    edit_row = st.columns([2, 2])
    
    # 获取当前编辑框的值，优先使用session_state
    trans_current = st.session_state.get(f"trans_edit_{bar_str}", comments[bar_str].get("translation", ""))
    plain_current = st.session_state.get(f"plain_edit_{bar_str}", comments[bar_str].get("plain", ""))

    with edit_row[0]:
        st.text_area(
            "翻译编辑",
            value=trans_current,
            height=80,
            key=f"trans_edit_{bar_str}",
            label_visibility="collapsed",
            placeholder="在此编辑翻译内容..."
        )

    with edit_row[1]:
        st.text_area(
            "白话编辑",
            value=plain_current,
            height=80,
            key=f"plain_edit_{bar_str}",
            label_visibility="collapsed",
            placeholder="在此编辑白话解释..."
        )

    # 保存和下载按钮
    col_save, col_download = st.columns([1, 1])
    with col_save:
        if st.button("💾 保存编辑", use_container_width=True):
            trans_val = st.session_state.get(f"trans_edit_{bar_str}", comments[bar_str].get("translation", ""))
            plain_val = st.session_state.get(f"plain_edit_{bar_str}", comments[bar_str].get("plain", ""))
            comments[bar_str]["translation"] = trans_val
            comments[bar_str]["plain"] = plain_val
            for c in all_data["cases"]:
                if str(c.get("case_id", "")) == str(selected_case_id):
                    c["comments"] = comments
                    break
            st.success("✅ 已保存")
            st.rerun()
    
    with col_download:
        st.download_button(
            "📥 下载JSON",
            save_json(all_data),
            file_name=f"albrooks_{selected_case_id}_updated.json",
            mime="application/json",
            use_container_width=True,
            help="下载更新后的JSON文件"
        )
