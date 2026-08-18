"""AI 集成核心：配置存取 + OpenAI 兼容 API 调用 + 提示词组装

使用 Python 标准库 urllib（不引入额外依赖），兼容 DeepSeek / OpenAI /
通义千问等 OpenAI 风格接口：
    POST {base_url}/chat/completions
    Authorization: Bearer <api_key>

配置保存在 settings.json（ai_base_url / ai_api_key / ai_model / ai_temperature）。
"""
from project_paths import PROJECT_ROOT

import json
import os
import urllib.request

SETTINGS_PATH = os.path.join(PROJECT_ROOT, "settings.json")


def get_ai_config():
    """读取 AI 配置（缺省 DeepSeek）。"""
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    return {
        "base_url": data.get("ai_base_url", "https://api.deepseek.com"),
        "api_key": data.get("ai_api_key", ""),
        "model": data.get("ai_model", "deepseek-chat"),
        "temperature": float(data.get("ai_temperature", 0.7)),
    }


def save_ai_config(base_url=None, api_key=None, model=None, temperature=None):
    """保存 AI 配置到 settings.json（保留其余字段）。"""
    data = {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        pass
    if base_url is not None:
        data["ai_base_url"] = base_url.strip().rstrip("/")
    if api_key is not None:
        data["ai_api_key"] = api_key.strip()
    if model is not None:
        data["ai_model"] = model.strip()
    if temperature is not None:
        data["ai_temperature"] = float(temperature)
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"保存 AI 配置失败: {e}")


def chat(messages, cfg=None, timeout=180):
    """调用 OpenAI 兼容 chat/completions 接口。

    Args:
        messages: [{"role": "system"|"user"|"assistant", "content": str}, ...]
        cfg: get_ai_config() 返回值；None 时自动读取
        timeout: 请求超时（秒）

    Returns:
        str: 模型回复文本

    Raises:
        RuntimeError: 未配置 Key / 网络错误 / 响应解析失败
    """
    cfg = cfg or get_ai_config()
    if not cfg.get("api_key"):
        raise RuntimeError("未配置 AI API Key（请先打开「工具 → AI 设置」）")
    base = (cfg.get("base_url") or "").rstrip("/")
    if not base:
        raise RuntimeError("未配置 API 地址")
    url = base + "/chat/completions"
    payload = {
        "model": cfg.get("model") or "deepseek-chat",
        "messages": messages,
        "temperature": float(cfg.get("temperature", 0.7)),
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + cfg["api_key"].strip(),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")[:300]
        except Exception:
            pass
        raise RuntimeError(f"AI 接口返回错误 {e.code}: {body or e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接 AI 接口: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"AI 请求失败: {e}")
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"AI 响应解析失败: {str(data)[:300]}")


def build_messages(content_type_label, user_text, extra=""):
    """组装提示词消息列表。

    Args:
        content_type_label: 内容类型中文名（如「国策」「事件」「民族精神」）
        user_text: 用户需求描述
        extra: 附加上下文（如目标国家、相关实体 id）
    """
    system = (
        "你是《钢铁雄心4》(Hearts of Iron IV) 模组脚本专家。"
        "你的任务是根据用户需求生成规范的 PDX 脚本代码。\n"
        "规则：\n"
        "1. 只输出 PDX 脚本，放在 ``` 代码块中，不要输出任何解释文字\n"
        "2. 使用 HOI4 标准语法（效果器/触发器/作用域）\n"
        "3. 实体 id 使用小写下划线的英文命名，带国家 tag 前缀（如 GER_xxx）\n"
        "4. 如果涉及本地化，输出格式： key: \"中文翻译\"\n"
        "5. 不要使用游戏不存在的效果器/触发器"
    )
    user = f"请生成「{content_type_label}」的 PDX 脚本。\n"
    if extra:
        user += f"上下文：{extra}\n"
    user += f"需求：{user_text}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def extract_code_blocks(text):
    """从模型回复中提取 ``` 代码块内容（支持 ```pdx / ```txt 标签）。

    Returns:
        list[str]: 代码块内容列表（无代码块时返回整体文本）。
    """
    import re
    blocks = re.findall(r"```[a-zA-Z0-9_\-]*\s*\n(.*?)```", text, re.DOTALL)
    if blocks:
        return [b.strip("\n") for b in blocks]
    # 无围栏：尝试提取看起来像脚本的整段
    stripped = text.strip()
    if stripped:
        return [stripped]
    return []
