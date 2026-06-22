# Al Brooks AI Study Tool (single-file Streamlit version)
# 使用Streamlit Secrets管理所有配置

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
        # 尝试从secrets读取
        value = st.secrets.get(key)
        if value is not None:
            return value
    except:
        pass
    
    # 如果secrets没有，从session_state读取
    return st.session_state.get(key, default)


def get_github_config():
    """获取GitHub配置"""
    return {
        "owner": get_secret("GITHUB_OWNER", ""),
        "repo": get_secret("GITHUB_REPO", ""),
        "path": get_secret("GITHUB_PATH", "cases_database.json"),
        "token": get_secret("GITHUB_TOKEN", ""),
        "branch": get_secret("GITHUB_BRANCH", "main")
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
    """从GitHub读取文件内容"""
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
        elif response.status_code == 404:
            return False, None, None, "文件不存在"
        else:
            return False, None, None, f"读取失败: {response.status_code}"
    except Exception as e:
        return False, None, None, f"错误: {str(e)}"


def github_write_file(owner, repo, path, content, token, commit_message=None, branch="main", sha=None):
    """写入文件到GitHub"""
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


def github_delete_file(owner, repo, path, token, commit_message=None, branch="main"):
    """删除GitHub文件"""
    if not token:
        return False, "❌ 请提供GitHub Token"
    
    if not commit_message:
        commit_message = f"删除文件 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        success, _, sha, _ = github_read_file(owner, repo, path, token, branch)
        if not success:
            return False, "文件不存在"
        
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        payload = {
            "message": commit_message,
            "sha": sha,
            "branch": branch
        }
        
        response = requests.delete(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return True, "✅ 文件删除成功"
        else:
            return False, f"❌ 删除失败: {response.status_code}"
    except Exception as e:
        return False, f"❌ 错误: {str(e)}"


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
    if github_config["token"] and github_config["owner"] and github_config["repo"]:
        st.success(f"✅ GitHub 已配置: {github_config['owner']}/{github_config['repo']}")
    else:
        st.error("❌ GitHub 配置不完整")
    
    st.markdown("---")
    st.markdown("### 📂 数据源")
    
    data_source = st.radio(
        "选择数据源",
        ["GitHub", "在线URL", "上传文件"],
        index=0,
        label_visibility="collapsed"
    )
    
    # 从GitHub加载
    if data_source == "GitHub":
        st.session_state.data_source = "github"
        st.markdown("#### GitHub文件")
        
        github_config = get_github_config()
        st.caption(f"📁 {github_config['path']}")
        st.caption(f"📂 {github_config['branch']}")
        
        if st.button("📖 从GitHub读取", use_container_width=True, type="primary"):
            if not github_config["token"]:
                st.error("❌ GitHub Token未配置")
            elif not github_config["owner"] or not github_config["repo"]:
                st.error("❌ GitHub配置不完整")
            else:
                with st.spinner("正在读取文件..."):
                    success, content, sha, message = github_read_file(
                        github_config["owner"],
                        github_config["repo"],
                        github_config["path"],
                        github_config["token"],
                        github_config["branch"]
                    )
                    if success:
                        try:
                            data = json.loads(content)
                            all_data, all_cases = load_all_cases_from_data(data)
                            st.session_state.all_data = all_data
                            st.session_state.all_cases = all_cases
                            st.session_state.github_file_sha = sha
                            st.session_state.all_data_modified = False
                            st.success(f"✅ 读取成功！共 {len(all_cases)} 个案例")
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("❌ 文件格式错误，不是有效的JSON")
                    else:
                        st.error(f"❌ {message}")
        
        # 创建新文件
        if st.button("📝 创建新文件", use_container_width=True):
            if not github_config["token"]:
                st.error("❌ 请先配置GitHub Token")
            else:
                empty_data = {"cases": []}
                content = json.dumps(empty_data, ensure_ascii=False, indent=2)
                success, message = github_write_file(
                    github_config["owner"],
                    github_config["repo"],
                    github_config["path"],
                    content,
                    github_config["token"],
                    f"创建新文件 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    github_config["branch"]
                )
                if success:
                    st.success("✅ 新文件创建成功！请点击'从GitHub读取'加载")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        # 删除文件
        if st.button("🗑️ 删除文件", use_container_width=True):
            if not github_config["token"]:
                st.error("❌ 请先配置GitHub Token")
            else:
                if st.checkbox("确认删除", value=False):
                    success, message = github_delete_file(
                        github_config["owner"],
                        github_config["repo"],
                        github_config["path"],
                        github_config["token"],
                        f"删除文件 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        github_config["branch"]
                    )
                    if success:
                        st.success("✅ 文件删除成功")
                        st.session_state.all_data = {"cases": []}
                        st.session_state.all_cases = []
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.warning("⚠️ 请勾选'确认删除'")
    
    # 从在线URL加载
    elif data_source == "在线URL":
        st.session_state.data_source = "url"
        st.markdown("#### 🔗 在线数据")
        
        default_url = get_json_url()
        json_url = st.text_input(
            "JSON URL",
            value=st.session_state.get("json_url", default_url),
            placeholder="输入JSON文件的在线URL",
            label_visibility="collapsed"
        )
        
        if json_url:
            st.session_state.json_url = json_url
            if st.button("📥 加载在线数据", use_container_width=True, type="primary"):
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
    else:
        st.session_state.data_source = "upload"
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
    st.info("👈 请从GitHub读取、上传文件或加载在线数据")
    
    # 显示配置信息
    with st.expander("🔧 配置说明"):
        st.markdown("""
        ### 如何配置Streamlit Secrets
        
        在项目根目录创建 `.streamlit/secrets.toml` 文件：
        
        ```toml
        # DeepSeek API Key
        DEEPSEEK_API_KEY = "your_deepseek_api_key_here"
        
        # GitHub配置
        GITHUB_TOKEN = "your_github_token_here"
        GITHUB_OWNER = "your_username"
        GITHUB_REPO = "your_repo_name"
        GITHUB_PATH = "cases_database.json"
        GITHUB_BRANCH = "main"
        
        # 默认JSON URL（可选）
        JSON_URL = "https://raw.githubusercontent.com/your_username/your_repo/main/cases_database.json"
