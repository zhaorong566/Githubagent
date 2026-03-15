# GitHub Assistant Agent

一个专业的 GitHub 开发助手 Agent，帮助开发者高效完成：**需求理解、Issue 分析、代码定位、修复方案设计、测试建议、PR 文案生成、Review 建议与风险识别**。

---

## ✨ 功能特性

| 功能 | CLI 命令 | 描述 |
|------|----------|------|
| 交互对话 | `chat` | 与 Agent 自由对话，支持引用 Issue/PR（如 #123） |
| Issue 分析 | `issue <编号>` | 获取 Issue 并输出结构化分析报告 |
| PR 描述生成 | `pr-desc <编号>` | 自动生成符合 Conventional Commits 的 PR 描述 |
| Code Review | `review <编号>` | 对 PR 进行分级 Review（Critical/Major/Minor/Nit） |
| 代码搜索 | `search <关键词>` | 在仓库中搜索代码并给出分析建议 |
| 文件分析 | `file <路径>` | 读取仓库文件并进行分析 |

---

## 🚀 快速开始

### 1. 克隆仓库并安装依赖

```bash
git clone https://github.com/zhaorong566/Githubagent.git
cd Githubagent
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 Token
```

`.env` 示例：

```
GITHUB_TOKEN=ghp_your_token_here
OPENAI_API_KEY=sk-your_key_here
GITHUB_REPO=owner/repo
```

> ⚠️ **安全提示**：请将密钥存储在 `.env` 文件中（已加入 `.gitignore`），切勿提交到代码仓库。  
> 在 CI/CD 环境中请使用 **GitHub Secrets**。

### 3. 运行

```bash
# 交互对话模式
python main.py chat

# 分析某个 Issue
python main.py issue 42

# 为 PR 生成描述
python main.py pr-desc 18

# 对 PR 进行 Code Review
python main.py review 18

# 搜索代码
python main.py search "authenticate_user" --max-results 5

# 分析仓库中的某个文件
python main.py file src/auth.py --concern "安全性"
```

所有命令都支持 `--repo owner/repo` 选项，可覆盖环境变量中的仓库配置。

---

## 🏗️ 项目结构

```
Githubagent/
├── main.py              # CLI 入口（Click）
├── agent.py             # 核心 Agent 逻辑
├── config.py            # 配置管理（从环境变量加载）
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
├── prompts/
│   ├── __init__.py
│   └── system_prompt.py # 系统提示词与输出模板
├── tools/
│   ├── __init__.py
│   ├── issue_tools.py   # Issue 获取与格式化
│   ├── pr_tools.py      # PR 获取与格式化
│   ├── code_tools.py    # 代码搜索与文件读取
│   └── review_tools.py  # Review 结构化工具
└── tests/
    ├── test_config.py
    ├── test_tools.py
    └── test_agent.py
```

---

## ⚙️ 配置参数

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `GITHUB_TOKEN` | — | GitHub Personal Access Token（必填） |
| `OPENAI_API_KEY` | — | OpenAI API Key（必填） |
| `GITHUB_REPO` | — | 目标仓库，格式：`owner/repo` |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | LLM API 端点（兼容 OpenAI 协议的服务均可） |
| `AGENT_MODEL` | `gpt-4o` | 使用的模型名称 |
| `AGENT_MAX_TOKENS` | `4096` | 最大输出 Token 数 |
| `AGENT_TEMPERATURE` | `0.2` | 生成温度（越低越确定） |
| `AGENT_VERBOSE` | `false` | 是否开启详细日志 |

---

## 🧪 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 工作模式

每次响应遵循以下结构：

- **A. 任务理解**：复述目标与约束（1–3 句）
- **B. 执行计划**：列出接下来要做的步骤（3–7 条）
- **C. 执行结果**：给出分析、定位、方案或草稿
- **D. 验证与风险**：说明如何验证、潜在风险、回滚建议
- **E. 下一步**：给用户一个最小可执行下一步

---

## 📄 License

MIT
