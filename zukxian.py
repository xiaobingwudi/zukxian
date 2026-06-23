
# Al Brooks AI Study Tool (single-file Streamlit version)
# 支持从私有仓库加载数据，主程序公开

import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from openai import OpenAI
import requests
from datetime import datetime
import base64

# 设置页面配置
st.set_page_config(page_title="Al Brooks AI Study Tool", layout="wide")


# --------------------- 配置管理模块 ---------------------

def get_secret(key, default=None):
    """
    从Streamlit Secrets获取配置
    优先从secrets读取，如果没有则从session_state读取
    """
    try:
        value = st.secrets.get(key)
        if value is not None:
            return value
    except:
        pass
    return st.session_state.get(key, default)


def get_github_config():
    """获取GitHub配置"""
    return {
        "token": get_secret("GITHUB_TOKEN", ""),
        "branch": get_secret("GITHUB_BRANCH", "main")
    }


def get_data_repo_config():
    """获取数据仓库配置（独立于主程序仓库）"""
    return {
        "owner": get_secret("DATA_REPO_OWNER", ""),
        "repo": get_secret("DATA_REPO_NAME", ""),
        "path": get_secret("DATA_FILE_PATH", "cases_database.json"),
        "token": get_secret("GITHUB_TOKEN", ""),
        "branch": get_secret("DATA_REPO_BRANCH", "main")
    }


def get_api_key():
    """获取DeepSeek API Key"""
    return get_secret("DEEPSEEK_API_KEY", "")


def get_json_url():
    """获取默认JSON URL"""
    return get_secret("JSON_URL", "")


# --------------------- AI 功能模块 ---------------------

def get_client():
    api_key = get_api_key()
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def ask_ai(system_prompt, user_prompt):
    client = get_client()
    if not client:
        return "请配置 DeepSeek API Key（在Secrets中设置DEEPSEEK_API_KEY）"

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
    return ask_ai(
        "你是Al Brooks价格行为专家。保留术语缩写，翻译成专业中文。",
        text
    )


def ai_explain(text):
    return ask_ai(
        "解释Al Brooks真正想表达的市场含义，不要逐词翻译。",
        text
    )


def ai_plain(text):
    return ask_ai(
        "把内容改写成普通交易员能看懂的大白话。",
        text
    )


# --------------------- GitHub完整操作模块 ---------------------

def github_read_file(owner, repo, path, token, branch="main"):
    """从GitHub读取文件内容（支持私有仓库）"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        params = {"ref": branch} if branch else {}
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode('utf-8')
            sha = data.get("sha")
            return True, content, sha, "读取成功"
        elif response.status_code == 401:
            return False, None, None, "Token无效或已过期"
        elif response.status_code == 403:
            return False, None, None, "Token权限不足，需要repo权限"
        elif response.status_code == 404:
            return False, None, None, "文件不存在"
        else:
            return False, None, None, f"读取失败: {response.status_code}"
    except Exception as e:
        return False, None, None, f"错误: {str(e)}"


def github_write_file(owner, repo, path, content, token, commit_message=None, branch="main", sha=None):
    """写入文件到GitHub（支持私有仓库）"""
    if not token:
        return False, "❌ 请提供GitHub Token"
    
    if not commit_message:
        commit_message = f"更新文件 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        if not sha:
            success, _, sha, _ = github_read_file(owner, repo, path, token, branch)
        
        content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": commit_message,
            "content": content_base64,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha
        
        response = requests.put(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            return True, "✅ 成功保存到GitHub！"
        else:
            error_msg = response.json().get("message", "未知错误")
            return False, f"❌ 保存失败: {error_msg}"
            
    except Exception as e:
        return False, f"❌ 保存失败: {str(e)}"


def load_data_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        st.error(f"❌ 加载失败: {e}")
        return None


def load_all_cases_from_data(data):
    if isinstance(data, list):
        data = data[0]
    cases = data.get("cases", [])
    return data, cases


def load_all_cases(uploaded):
    data = json.loads(uploaded.getvalue().decode("utf-8"))
    if isinstance(data, list):
        data = data[0]
    cases = data.get("cases", [])
    return data, cases


def load_case_by_id(cases, case_id):
    for case in cases:
        if str(case.get("case_id", "")) == str(case_id):
            bars = pd.DataFrame(case.get("bars", []))
            comments = case.get("comments", {})
            return case, bars, comments
    return None, None, None


def save_json(data):
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    return txt


def load_from_private_repo():
    """从私有仓库加载数据"""
    config = get_data_repo_config()
    
    if not config["token"]:
        return None, "❌ GitHub Token未配置"
    
    if not config["owner"] or not config["repo"]:
        return None, "❌ 数据仓库配置不完整（请设置DATA_REPO_OWNER和DATA_REPO_NAME）"
    
    success, content, sha, message = github_read_file(
        config["owner"],
        config["repo"],
        config["path"],
        config["token"],
        config["branch"]
    )
    
    if success:
        try:
            data = json.loads(content)
            return data, "✅ 数据加载成功"
        except json.JSONDecodeError:
            return None, "❌ 数据文件格式错误"
    else:
        return None, f"❌ {message}"


def save_to_private_repo(data, commit_message=None):
    """保存数据到私有仓库"""
    config = get_data_repo_config()
    
    if not config["token"]:
        return False, "❌ GitHub Token未配置"
    
    if not config["owner"] or not config["repo"]:
        return False, "❌ 数据仓库配置不完整"
    
    content = save_json(data)
    return github_write_file(
        config["owner"],
        config["repo"],
        config["path"],
        content,
        config["token"],
        commit_message or f"更新数据 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        config["branch"]
    )


# --------------------- UI 界面模块 ---------------------

# CSS样式
st.markdown("""
<style>
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.1rem !important;
        padding-left: 0.2rem !important;
        padding-right: 0.2rem !important;
        max-width: 100% !important;
    }
    .element-container {
        margin-bottom: 0.05rem !important;
    }
    .stButton button {
        padding: 0.1rem 0.3rem !important;
        font-size: 0.7rem !important;
        min-height: 1.4rem !important;
        margin: 0 !important;
    }
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
    .row-widget.stColumns {
        gap: 0.02rem !important;
        margin: 0 !important;
    }
    h1, h2, h3, h4, h5 {
        margin-top: 0.1rem !important;
        margin-bottom: 0.1rem !important;
        padding: 0 !important;
    }
    h1 { font-size: 1.2rem !important; }
    h3 { font-size: 0.85rem !important; }
    h4 { font-size: 0.75rem !important; }
    h5 { font-size: 0.7rem !important; }
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
    .top-status {
        background: #f8f9fa;
        padding: 6px 12px;
        border-radius: 4px;
        margin-bottom: 8px;
        border: 2px solid #dee2e6;
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px 12px;
        min-height: 36px;
        z-index: 100;
        position: relative;
    }
    .status-item {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        font-size: 0.9rem;
        white-space: nowrap;
        padding: 2px 6px;
    }
    .status-item .label {
        color: #6c757d;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .status-item .value {
        font-weight: 700;
        font-size: 0.95rem;
        color: #212529;
    }
    .price-inline {
        display: inline-flex;
        gap: 6px;
        flex-wrap: wrap;
        align-items: center;
        font-size: 0.85rem !important;
        margin-left: 4px;
    }
    .price-inline-item {
        background: white;
        padding: 2px 8px;
        border-radius: 3px;
        border-left: 2px solid #dee2e6;
        font-size: 0.85rem !important;
        white-space: nowrap;
        font-weight: 500;
    }
    .price-inline-item strong {
        font-weight: 700;
        color: #495057;
        font-size: 0.75rem !important;
        margin-right: 2px;
    }
    .has-comment { color: #28a745; font-weight: 700; font-size: 1rem; }
    .no-comment { color: #dc3545; font-weight: 700; font-size: 1rem; }
    .price-info {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        padding: 2px 0;
        margin: 0;
        align-items: center;
    }
    .price-item {
        background: #f8f9fa;
        padding: 1px 6px;
        border-radius: 3px;
        border-left: 2px solid #dee2e6;
        font-size: 0.7rem !important;
        line-height: 1.4;
    }
    .price-item strong {
        font-weight: 600;
        color: #495057;
        font-size: 0.65rem !important;
    }
    .save-status {
        background: #fff3cd;
        padding: 4px 10px;
        border-radius: 4px;
        border-left: 3px solid #ffc107;
        margin: 4px 0;
        font-size: 0.75rem;
    }
    .save-success {
        background: #d4edda;
        padding: 4px 10px;
        border-radius: 4px;
        border-left: 3px solid #28a745;
        margin: 4px 0;
        font-size: 0.75rem;
    }
    .config-status {
        background: #e8f4fd;
        padding: 8px 12px;
        border-radius: 4px;
        border: 1px solid #b8d4e8;
        margin: 8px 0;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# 页面标题
st.title("📚 Al Brooks 逐K训练器")

# ---------------- 初始化session_state ----------------
if "all_data" not in st.session_state:
    st.session_state.all_data = {"cases": []}
if "all_cases" not in st.session_state:
    st.session_state.all_cases = []
if "data_source" not in st.session_state:
    st.session_state.data_source = None
if "current_case_id" not in st.session_state:
    st.session_state.current_case_id = None
if "all_data_modified" not in st.session_state:
    st.session_state.all_data_modified = False
if "save_message" not in st.session_state:
    st.session_state.save_message = ""
if "github_file_sha" not in st.session_state:
    st.session_state.github_file_sha = None

# ---------------- 显示配置状态 ----------------
with st.sidebar:
    st.markdown("### 🔐 配置状态")
    
    # 检查API Key
    api_key = get_api_key()
    if api_key:
        st.success("✅ DeepSeek API Key 已配置")
    else:
        st.error("❌ DeepSeek API Key 未配置")
    
    # 检查GitHub配置
    github_config = get_github_config()
    data_repo_config = get_data_repo_config()
    
    if github_config["token"]:
        st.success("✅ GitHub Token 已配置")
    else:
        st.error("❌ GitHub Token 未配置")
    
    if data_repo_config["owner"] and data_repo_config["repo"]:
        st.success(f"✅ 数据仓库: {data_repo_config['owner']}/{data_repo_config['repo']}")
    else:
        st.error("❌ 数据仓库配置不完整")
    
    st.markdown("---")
    st.markdown("### 📂 数据源")
    
    # 从私有仓库加载
    st.markdown("#### 🔒 私有数据仓库")
    st.caption(f"📁 {data_repo_config['path']}")
    st.caption(f"📂 {data_repo_config['branch']}")
    
    col_load1, col_load2 = st.columns(2)
    with col_load1:
        if st.button("📖 加载数据", use_container_width=True, type="primary"):
            with st.spinner("正在从私有仓库加载数据..."):
                data, message = load_from_private_repo()
                if data:
                    all_data, all_cases = load_all_cases_from_data(data)
                    st.session_state.all_data = all_data
                    st.session_state.all_cases = all_cases
                    st.session_state.all_data_modified = False
                    st.success(f"✅ 加载成功！共 {len(all_cases)} 个案例")
                    st.rerun()
                else:
                    st.error(message)
    
    with col_load2:
        if st.button("📝 创建数据文件", use_container_width=True):
            if not github_config["token"]:
                st.error("❌ 请先配置GitHub Token")
            else:
                empty_data = {"cases": []}
                content = json.dumps(empty_data, ensure_ascii=False, indent=2)
                success, message = github_write_file(
                    data_repo_config["owner"],
                    data_repo_config["repo"],
                    data_repo_config["path"],
                    content,
                    data_repo_config["token"],
                    f"创建数据文件 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    data_repo_config["branch"]
                )
                if success:
                    st.success("✅ 数据文件创建成功！请点击'加载数据'")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    st.markdown("---")
    st.markdown("#### 📂 其他数据源")
    
    # 从在线URL加载
    default_url = get_json_url()
    json_url = st.text_input(
        "在线URL",
        value=st.session_state.get("json_url", default_url),
        placeholder="输入JSON文件的在线URL",
        label_visibility="collapsed"
    )
    
    if json_url:
        st.session_state.json_url = json_url
        if st.button("📥 加载在线数据", use_container_width=True):
            with st.spinner("正在加载在线数据..."):
                data = load_data_from_url(json_url)
                if data:
                    all_data, all_cases = load_all_cases_from_data(data)
                    st.session_state.all_data = all_data
                    st.session_state.all_cases = all_cases
                    st.session_state.all_data_modified = False
                    st.success("✅ 数据加载成功！")
                    st.rerun()
    
    # 上传文件
    st.markdown("#### 📂 上传文件")
    file = st.file_uploader("上传JSON文件", type=["json"], label_visibility="collapsed")
    
    if file:
        all_data, all_cases = load_all_cases(file)
        st.session_state.all_data = all_data
        st.session_state.all_cases = all_cases
        st.session_state.all_data_modified = False
        st.success("✅ 数据加载成功")

# 使用session_state中的数据
all_data = st.session_state.all_data
all_cases = st.session_state.all_cases

if all_data is None or all_cases is None or not all_cases:
    st.warning("⚠️ 请加载数据")
    
    with st.expander("📖 使用说明"):
        st.markdown("""
        ### 如何配置
            
        在Streamlit Cloud的Settings -> Secrets中添加以下配置：
        
        ```toml
        # DeepSeek API Key
        DEEPSEEK_API_KEY = "sk-你的DeepSeek密钥"
        
        # GitHub Token（需要有repo权限）
        GITHUB_TOKEN = "github_pat_你的Token"
        
        # 数据仓库配置（私有仓库）
        DATA_REPO_OWNER = "xiaobingwudi"
        DATA_REPO_NAME = "private-data"
        DATA_FILE_PATH = "cases_database.json"
        DATA_REPO_BRANCH = "main"
        ```
        
        ### 获取GitHub Token
        1. 访问 https://github.com/settings/tokens
        2. 点击 "Generate new token (classic)"
        3. 勾选 `repo` 权限
        4. 生成并复制Token
        
        ### 创建私有数据仓库
        1. 在GitHub创建新仓库，设置为 **Private**
        2. 上传 `cases_database.json` 文件
        3. 在Secrets中配置仓库信息
        """)
    
    # 显示当前配置状态
    with st.expander("🔧 当前配置状态"):
        data_repo = get_data_repo_config()
        st.json({
            "DeepSeek API Key": "✅ 已配置" if get_api_key() else "❌ 未配置",
            "GitHub Token": "✅ 已配置" if data_repo["token"] else "❌ 未配置",
            "数据仓库": f"{data_repo['owner']}/{data_repo['repo']}" if data_repo["owner"] and data_repo["repo"] else "未配置",
            "文件路径": data_repo["path"] or "未配置",
            "分支": data_repo["branch"] or "未配置"
        })
    
    st.info("💡 请在左侧边栏选择数据源并加载数据")
    st.stop()

# 获取所有案例的ID和标题
case_options = {}
for case in all_cases:
    case_id = case.get("case_id", "unknown")
    title = case.get("title", f"案例 {case_id}")
    case_options[f"{case_id}"] = case_id

# 案例选择
selected_case_id = st.sidebar.selectbox(
    "📋 案例",
    options=list(case_options.keys()),
    index=0,
    label_visibility="collapsed"
)

# 更新当前案例ID
st.session_state.current_case_id = selected_case_id

# 加载选中的案例
case, bars_df, comments = load_case_by_id(all_cases, selected_case_id)

if case is None:
    st.error(f"未找到案例 ID: {selected_case_id}")
    st.stop()

# 过滤编号0的空K线
if 0 in bars_df["bar"].values:
    bar_zero = bars_df[bars_df["bar"] == 0]
    if bar_zero.empty or (bar_zero["open"].isna().all() and bar_zero["close"].isna().all()):
        bars_df = bars_df[bars_df["bar"] != 0]

# 获取所有K线编号
all_bars = sorted(bars_df["bar"].unique())
total_bars = len(all_bars)
max_bar = max(all_bars) if len(all_bars) > 0 else 0
min_bar = min(all_bars) if len(all_bars) > 0 else 0

# 计算价格范围
price_min = bars_df["low"].min()
price_max = bars_df["high"].max()
price_padding = (price_max - price_min) * 0.05

# 获取有注释的K线列表
comment_bars = sorted([int(x) for x in comments.keys() if int(x) > 0])

# 获取第一根正数K线
first_positive_bar = min([b for b in all_bars if b > 0]) if any(b > 0 for b in all_bars) else None

# 初始化当前K线状态
if "current_bar" not in st.session_state or st.session_state.get("case_id") != selected_case_id:
    if first_positive_bar is not None:
        st.session_state.current_bar = first_positive_bar
    else:
        st.session_state.current_bar = max_bar if max_bar > 0 else 1
    st.session_state.case_id = selected_case_id

if st.session_state.current_bar > max_bar:
    st.session_state.current_bar = first_positive_bar if first_positive_bar is not None else max_bar

if first_positive_bar is not None and st.session_state.current_bar < first_positive_bar:
    st.session_state.current_bar = first_positive_bar

# =======================
# 显示保存状态
# =======================
if st.session_state.save_message:
    st.markdown(f'<div class="save-success">{st.session_state.save_message}</div>', unsafe_allow_html=True)
    st.session_state.save_message = ""

if st.session_state.all_data_modified:
    st.markdown('<div class="save-status">⚠️ 数据已修改，请点击"💾 保存数据"保存</div>', unsafe_allow_html=True)

# =======================
# 顶部状态栏
# =======================
current_row = bars_df[bars_df["bar"] == st.session_state.current_bar]

price_html = ""
if not current_row.empty:
    row = current_row.iloc[0]
    change = row['close'] - row['open']
    change_pct = (change / row['open'] * 100) if row['open'] != 0 else 0
    is_up = row['close'] > row['open']
    color_style = '#28a745' if is_up else '#dc3545'
    
    price_html = (
        '<span class="price-inline-item"><strong>开</strong>' + f'{row["open"]:.2f}' + '</span>'
        '<span class="price-inline-item"><strong>高</strong>' + f'{row["high"]:.2f}' + '</span>'
        '<span class="price-inline-item"><strong>低</strong>' + f'{row["low"]:.2f}' + '</span>'
        '<span class="price-inline-item"><strong>收</strong>' + f'{row["close"]:.2f}' + '</span>'
        '<span class="price-inline-item" style="border-left-color: ' + color_style + ';">'
        '<strong>涨跌</strong> ' + f'{change:+.2f}' + '(' + f'{change_pct:+.2f}' + '%)'
        '</span>'
    )

bar_str = str(st.session_state.current_bar)
has_comment = st.session_state.current_bar > 0 and bar_str in comments
comment_status = '<span class="has-comment">✅</span>' if has_comment else '<span class="no-comment">❌</span>'

status_html = f'''
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
    <span class="status-item" style="flex:0;">
        <span class="label">{case.get('title', '')}</span>
    </span>
    <span class="price-inline">
        {price_html}
    </span>
</div>
'''

st.markdown(status_html, unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# =======================
# K线图表
# =======================
visible = bars_df[bars_df["bar"] <= st.session_state.current_bar]

current_row = bars_df[bars_df["bar"] == st.session_state.current_bar]
if not current_row.empty:
    row = current_row.iloc[0]
    is_up = row["close"] > row["open"]
    color = "red" if is_up else "black"
else:
    color = "blue"

fig = go.Figure()

up_bars = visible[visible["close"] > visible["open"]]
down_bars = visible[visible["close"] <= visible["open"]]

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

if min_bar < 0:
    fig.add_vline(x=0.5, line_width=1, line_color="gray", line_dash="dot")
    fig.add_annotation(
        x=0.5,
        y=price_max * 0.95,
        text="盘前 | 正式",
        showarrow=False,
        font=dict(size=8, color="gray")
    )

fig.add_vline(
    x=st.session_state.current_bar,
    line_width=2,
    line_color=color,
    line_dash="dash"
)

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

x_min = min_bar - 0.5 if min_bar < 0 else -0.5
x_max = max_bar + 0.5

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
    progress = (current_idx + 1) / total if total > 0 else 0
    st.progress(progress, text=f"{current_idx + 1}/{total}")

with ctrl_cols[4]:
    if st.button("⏭", help="最后一根"):
        if current_idx < total - 1:
            st.session_state.current_bar = all_bars[-1]
            st.rerun()

with ctrl_cols[5]:
    if positive_comment_bars := [b for b in comment_bars if b > 0]:
        if st.button("💬跳", help="跳转到有注释的K线"):
            for b in positive_comment_bars:
                if b > st.session_state.current_bar:
                    st.session_state.current_bar = b
                    st.rerun()
            st.session_state.current_bar = positive_comment_bars[0]
            st.rerun()

# =======================
# 下方信息面板 - 注释内容
# =======================

st.markdown("---")

if has_comment:
    item = comments[bar_str]
    original_text = item.get("original", "")
    translation = item.get("translation", "")
    plain_text = item.get("plain", "")
    
    st.markdown(f"### 📊 Bar {bar_str} 注释内容")
    
    if original_text:
        st.markdown(f'<div class="original-text">📖 <b>原文:</b> {original_text}</div>', unsafe_allow_html=True)
    else:
        st.info("ℹ️ 此K线没有原文内容")
    
    if translation:
        st.markdown(f'<div class="comment-box">📝 <b>翻译:</b> {translation}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="comment-box" style="border-left-color: #6c757d; color: #6c757d;">📝 <b>翻译:</b> (空)</div>', unsafe_allow_html=True)
    
    if plain_text:
        st.markdown(f'<div class="comment-box">💬 <b>白话:</b> {plain_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="comment-box" style="border-left-color: #6c757d; color: #6c757d;">💬 <b>白话:</b> (空)</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### ✏️ 编辑注释")
    edit_row = st.columns([2, 2])
    
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

    # 保存按钮
    st.markdown("---")
    st.markdown("#### 💾 保存操作")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn1:
        if st.button("💾 保存到内存", use_container_width=True, type="primary"):
            trans_edit = st.session_state.get(f"trans_edit_{bar_str}", "")
            plain_edit = st.session_state.get(f"plain_edit_{bar_str}", "")
            
            if bar_str not in comments:
                comments[bar_str] = {}
            comments[bar_str]["translation"] = trans_edit
            comments[bar_str]["plain"] = plain_edit
            
            for c in st.session_state.all_data["cases"]:
                if str(c.get("case_id", "")) == str(selected_case_id):
                    c["comments"] = comments
                    break
            
            st.session_state.all_data_modified = True
            st.session_state.save_message = "✅ 已保存到内存！"
            st.rerun()
    
    with col_btn2:
        if st.button("🌐 AI翻译", use_container_width=True):
            if original_text:
                with st.spinner("AI正在翻译..."):
                    result = ai_translate(original_text)
                    if bar_str not in comments:
                        comments[bar_str] = {}
                    comments[bar_str]["translation"] = result
                    
                    for c in st.session_state.all_data["cases"]:
                        if str(c.get("case_id", "")) == str(selected_case_id):
                            c["comments"] = comments
                            break
                    
                    st.session_state.all_data_modified = True
                    st.session_state[f"trans_edit_{bar_str}"] = result
                    st.session_state.save_message = "✅ AI翻译完成"
                    st.rerun()
            else:
                st.warning("没有原文可翻译")
    
    with col_btn3:
        if st.button("🗣️ AI白话", use_container_width=True):
            if original_text:
                with st.spinner("AI正在改写..."):
                    result = ai_plain(original_text)
                    if bar_str not in comments:
                        comments[bar_str] = {}
                    comments[bar_str]["plain"] = result
                    
                    for c in st.session_state.all_data["cases"]:
                        if str(c.get("case_id", "")) == str(selected_case_id):
                            c["comments"] = comments
                            break
                    
                    st.session_state.all_data_modified = True
                    st.session_state[f"plain_edit_{bar_str}"] = result
                    st.session_state.save_message = "✅ AI白话完成"
                    st.rerun()
            else:
                st.warning("没有原文可改写")

else:
    current_row = bars_df[bars_df["bar"] == st.session_state.current_bar]
    if not current_row.empty:
        row = current_row.iloc[0]
        st.markdown(f"##### Bar {bar_str} 价格信息")
        
        change = row['close'] - row['open']
        change_pct = (change / row['open'] * 100) if row['open'] != 0 else 0
        is_up = row['close'] > row['open']
        
        st.markdown(f"""
        <div class="price-info">
            <span class="price-item"><strong>开盘</strong> {row['open']:.2f}</span>
            <span class="price-item"><strong>最高</strong> {row['high']:.2f}</span>
            <span class="price-item"><strong>最低</strong> {row['low']:.2f}</span>
            <span class="price-item"><strong>收盘</strong> {row['close']:.2f}</span>
            <span class="price-item" style="border-left-color: {'#28a745' if is_up else '#dc3545'};">
                <strong>涨跌</strong> 
                {change:+.2f} 
                ({change_pct:+.2f}%)
            </span>
        </div>
        """, unsafe_allow_html=True)

# =======================
# 保存到私有仓库 - 在页面底部
# =======================
st.markdown("---")
st.markdown("### 💾 保存到私有仓库")

# 显示当前数据预览
with st.expander("📊 查看要保存的数据"):
    st.json({
        "case_id": selected_case_id,
        "bar": bar_str,
        "translation": comments.get(bar_str, {}).get("translation", ""),
        "plain": comments.get(bar_str, {}).get("plain", ""),
        "total_cases": len(all_cases)
    })

col_save1, col_save2 = st.columns([2, 1])

with col_save1:
    if st.button("💾 保存到私有仓库", use_container_width=True, type="primary"):
        data_repo = get_data_repo_config()
        if not data_repo["token"]:
            st.error("❌ GitHub Token未配置")
        elif not data_repo["owner"] or not data_repo["repo"]:
            st.error("❌ 数据仓库配置不完整")
        else:
            with st.spinner("正在保存到私有仓库..."):
                success, message = save_to_private_repo(
                    st.session_state.all_data,
                    f"更新案例 {selected_case_id} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                if success:
                    st.success(message)
                    st.session_state.all_data_modified = False
                    st.session_state.save_message = "✅ 成功保存到私有仓库！"
                    st.rerun()
                else:
                    st.error(message)

with col_save2:
    # 下载JSON作为备选
    json_str = save_json(st.session_state.all_data)
    st.download_button(
        "📥 下载JSON备份",
        json_str,
        file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True,
        help="下载JSON备份"
    )

# 显示修改状态和文件信息
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    if st.session_state.all_data_modified:
        st.info("💡 数据已修改，请点击 '💾 保存到私有仓库' 保存")
    else:
        st.success("✅ 数据已保存")
        
with col_info2:
    data_repo = get_data_repo_config()
    st.caption(f"📁 文件: {data_repo['path']}")
    
with col_info3:
    st.caption(f"📂 分支: {data_repo['branch']}")

# 显示当前注释内容
st.markdown("---")
st.markdown("### 📝 当前K线注释")
st.json({
    "bar": bar_str,
    "translation": comments.get(bar_str, {}).get("translation", ""),
    "plain": comments.get(bar_str, {}).get("plain", "")
})
