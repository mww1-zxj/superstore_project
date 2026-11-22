# Superstore 自动化经营诊断月报（Python + 大模型 API）

本模块实现 **「输入任意月份 → Python 精准核算指标 → 规则预警 → 大模型 API 自动输出管理层经营简报 → 自动口径校验」** 的完整闭环。

---

## 一、核心架构（为什么不直接把 CSV 扔给大模型？）

```
data/processed/superstore_clean.csv
        │
        ▼  【1. Python / Pandas 精准核算层】
  计算销售额、利润、利润率、同环比、分地区、分折扣档、亏损 Top3
  + 确定性规则自动预警  ──▶  output/2017-11_metrics.json
        │
        ▼  【2. 防幻觉 Prompt 工程层】
  注入 JSON 指标 + 严禁编造数字红线 + 4段式高管汇报模板
        │
        ▼  【3. 大模型 API 自动撰写层】
  调用兼容 OpenAI 协议的接口（DeepSeek / 通义千问 / 智谱等）
  temperature=0.2 保证严谨稳定  ──▶  output/2017-11_report.md
        │
        ▼  【4. 自动化一致校验层】
  检查核心利润率与主要亏损品类是否准确覆盖
```

---

## 二、怎么运行？（仅依赖 `pandas` 和 `requests`）

### 方式 A：离线演练模式（无需 API Key，立刻体验）
在项目根目录运行：
```bash
python3 automation/generate_monthly_report.py 2017-11
```
运行后会生成：
- `automation/output/2017-11_metrics.json`（Python 算好的 100% 精准指标包）
- `automation/output/2017-11_prompt.txt`（可直接复制粘贴到任意大模型网页版查看汇报效果）

> 可以将 `2017-11` 换成任意月份（`2014-01` ~ `2017-12`），例如 `2017-12`。

### 方式 B：一键直连大模型 API 自动生成报告
以 **DeepSeek** 为例：
```bash
export LLM_API_KEY="sk-换成你自己的密钥"
python3 automation/generate_monthly_report.py 2017-11
```
完成后会直接生成 `automation/output/2017-11_report.md`。

如需切换为**阿里云百炼（通义千问）**或**智谱 GLM**，只需额外设置两行环境变量：
```bash
# 通义千问示例
export LLM_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export LLM_MODEL="qwen-plus"
export LLM_API_KEY="sk-换成你的百炼密钥"
python3 automation/generate_monthly_report.py 2017-11
```

---

## 三、面试时怎么把这几十行代码讲出高级感？（必背 3 句话）

1. **防算术幻觉（算归算、写归写）**：大模型擅长总结和商业表达，但不擅长精确聚合计算，所以我把所有同环比、利润率和亏损排名全部留在 Python 端算成确定性 JSON，只让模型负责归因叙述与建议生成。
2. **业务规则 + LLM 双重兜底**：先用确定性规则标出低于历史均值的异常利润率、高折扣区域和亏损子品类（`auto_alerts`），再喂给低温度（`temperature=0.2`）模型，并做了基础数字覆盖校验。
3. **可复用、低成本落地**：只需改一个月份参数就能一键批量生成任意月份的经营复盘，把分析师从每周重复写周报里解放出来，专注做更深层的根因挖掘。
