"""
Superstore 自动化经营诊断月报生成器（Python + 大模型 API）
========================================================
核心设计思想（面试必讲）：
1. 「算归算、写归写」：所有指标（销售额、利润、同环比、亏损排名）全部由 Python/Pandas 精准计算，
   绝不让大模型直接算数，彻底杜绝算术幻觉。
2. 「防幻觉 Prompt」：将结构化 JSON 指标包喂给大模型，并严格约束禁止编造数字。
3. 「双模式运行」：
   - 未配置 API Key 时：自动导出 metrics.json + prompt.txt，可直接复制到任意大模型网页版体验；
   - 配置 LLM_API_KEY 后：一键直连大模型 API，自动生成 Markdown 月度经营诊断报告并做基础口径校验。

使用方式：
  # 方式 1：离线演练模式（无需 API Key，生成精准指标包与 Prompt）
  python3 generate_monthly_report.py 2017-11

  # 方式 2：直连大模型 API 自动生成报告（以 DeepSeek 为例，其他模型见下方配置）
  export LLM_API_KEY="sk-你的密钥"
  python3 generate_monthly_report.py 2017-11
"""

import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests

# ==================== 1. 大模型 API 配置（兼容国内主流模型） ====================
# 默认使用 DeepSeek（便宜且中文商业分析质量高）；
# 如需切换其他兼容 OpenAI 协议的平台，只需改下面两行环境变量或默认值：
#   - 阿里云百炼（通义千问）: BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1", MODEL="qwen-plus"
#   - 智谱清言（GLM）      : BASE_URL="https://open.bigmodel.cn/api/paas/v4",            MODEL="glm-4-flash"
#   - 月之暗面（Kimi）     : BASE_URL="https://api.moonshot.cn/v1",                      MODEL="moonshot-v1-8k"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()


# ==================== 2. 数据读取与精准指标计算层 ====================
def find_csv_path() -> Path:
    """自动寻找 superstore_clean.csv（兼容桌面运行或放入 GitHub 仓库运行）"""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / "data" / "processed" / "superstore_clean.csv",
        script_dir / "superstore_clean.csv",
        script_dir.parent / "superstore_clean.csv",
        Path.home() / "Desktop" / "superstore_clean.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        "未找到 superstore_clean.csv，请先导出至 data/processed/superstore_clean.csv 或放在项目根目录/桌面上。"
    )


def pct_change(curr: float, prev: float):
    """安全计算变动百分比，避免除零错误"""
    if prev is None or prev == 0:
        return None
    return round((curr - prev) / abs(prev) * 100, 2)


def get_prev_months(target_ym: str):
    """给定 '2017-11'，返回上月 '2017-10' 与去年同月 '2016-11'"""
    y, m = map(int, target_ym.split("-"))
    prev_m_ym = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
    yoy_ym = f"{y - 1}-{m:02d}"
    return prev_m_ym, yoy_ym


def compute_monthly_metrics(df: pd.DataFrame, target_ym: str) -> dict:
    """纯 Python 精准计算当月经营指标包（所有数字 100% 可追溯）"""
    cur = df[df["Year-Month"] == target_ym]
    if cur.empty:
        valid_months = sorted(df["Year-Month"].unique())
        raise ValueError(
            f"数据中不存在月份 {target_ym}，可选范围：{valid_months[0]} ~ {valid_months[-1]}"
        )

    prev_ym, yoy_ym = get_prev_months(target_ym)
    prev_df = df[df["Year-Month"] == prev_ym]
    yoy_df = df[df["Year-Month"] == yoy_ym]

    # 1) 大盘核心指标
    sales = float(cur["Sales"].sum())
    profit = float(cur["Profit"].sum())
    margin = round(profit / sales * 100, 2) if sales else 0.0
    orders = int(cur["Order ID"].nunique())
    aov = round(sales / orders, 2) if orders else 0.0
    avg_discount = round(float(cur["Discount"].mean()) * 100, 2)

    # 全周期基准利润率（用于对比当月是否异常）
    overall_margin = round(float(df["Profit"].sum() / df["Sales"].sum()) * 100, 2)

    prev_sales = float(prev_df["Sales"].sum()) if not prev_df.empty else None
    prev_profit = float(prev_df["Profit"].sum()) if not prev_df.empty else None
    yoy_sales = float(yoy_df["Sales"].sum()) if not yoy_df.empty else None
    yoy_profit = float(yoy_df["Profit"].sum()) if not yoy_df.empty else None

    # 2) 分地区表现
    region_df = (
        cur.groupby("Region", as_index=False)
        .agg(
            sales=("Sales", "sum"),
            profit=("Profit", "sum"),
            orders=("Order ID", "nunique"),
            avg_discount=("Discount", "mean"),
        )
        .sort_values("profit", ascending=True)
    )
    regions = [
        {
            "region": r["Region"],
            "sales": round(float(r["sales"]), 2),
            "profit": round(float(r["profit"]), 2),
            "profit_margin_pct": round(float(r["profit"] / r["sales"]) * 100, 2),
            "orders": int(r["orders"]),
            "avg_discount_pct": round(float(r["avg_discount"]) * 100, 2),
        }
        for _, r in region_df.iterrows()
    ]

    # 3) 分折扣档表现
    band_order = ["无折扣", "低折扣", "中折扣", "高折扣"]
    band_df = cur.groupby("Discount Band", as_index=False).agg(
        rows=("Row ID", "count"),
        sales=("Sales", "sum"),
        profit=("Profit", "sum"),
    )
    band_df["sort_key"] = band_df["Discount Band"].apply(
        lambda x: band_order.index(x) if x in band_order else 99
    )
    band_df = band_df.sort_values("sort_key")
    discount_bands = [
        {
            "discount_band": r["Discount Band"],
            "line_items": int(r["rows"]),
            "sales": round(float(r["sales"]), 2),
            "profit": round(float(r["profit"]), 2),
            "profit_margin_pct": round(float(r["profit"] / r["sales"]) * 100, 2),
        }
        for _, r in band_df.iterrows()
    ]

    # 4) 亏损最严重的 Top 3 子品类 & 盈利最高的 Top 3 子品类
    subcat_df = cur.groupby("Sub-Category", as_index=False).agg(
        sales=("Sales", "sum"),
        profit=("Profit", "sum"),
        avg_discount=("Discount", "mean"),
    )
    subcat_df["margin_pct"] = (subcat_df["profit"] / subcat_df["sales"] * 100).round(2)

    worst_subcats = [
        {
            "sub_category": r["Sub-Category"],
            "sales": round(float(r["sales"]), 2),
            "profit": round(float(r["profit"]), 2),
            "profit_margin_pct": float(r["margin_pct"]),
            "avg_discount_pct": round(float(r["avg_discount"]) * 100, 2),
        }
        for _, r in subcat_df.sort_values("profit", ascending=True).head(3).iterrows()
        if r["profit"] < 0
    ]

    top_subcats = [
        {
            "sub_category": r["Sub-Category"],
            "sales": round(float(r["sales"]), 2),
            "profit": round(float(r["profit"]), 2),
            "profit_margin_pct": float(r["margin_pct"]),
        }
        for _, r in subcat_df.sort_values("profit", ascending=False).head(3).iterrows()
    ]

    # 5) 单笔/单品亏损 Top 3 明细（便于业务直接定位止损对象）
    worst_items = [
        {
            "product_name": r["Product Name"],
            "sub_category": r["Sub-Category"],
            "region": r["Region"],
            "sales": round(float(r["Sales"]), 2),
            "profit": round(float(r["Profit"]), 2),
            "discount_pct": round(float(r["Discount"]) * 100, 1),
        }
        for _, r in cur.sort_values("Profit", ascending=True).head(3).iterrows()
        if r["Profit"] < 0
    ]

    # 6) 规则预警（确定性业务规则 + LLM 解读相结合）
    alerts = []
    if margin < overall_margin:
        alerts.append(
            f"当月综合利润率 {margin}% 低于历史均值 {overall_margin}%（差值 {round(margin - overall_margin, 2)} 个百分点）"
        )
    for rg in regions:
        if rg["profit"] < 0 or rg["profit_margin_pct"] < 5:
            alerts.append(
                f"{rg['region']} 区域利润偏低（利润 ${rg['profit']}，利润率 {rg['profit_margin_pct']}%，平均折扣 {rg['avg_discount_pct']}%）"
            )
    for sc in worst_subcats:
        alerts.append(
            f"子品类 {sc['sub_category']} 当月亏损 ${abs(sc['profit'])}（平均折扣 {sc['avg_discount_pct']}%）"
        )

    return {
        "report_month": target_ym,
        "currency": "USD ($)",
        "overview": {
            "sales": round(sales, 2),
            "profit": round(profit, 2),
            "profit_margin_pct": margin,
            "historical_avg_margin_pct": overall_margin,
            "unique_orders": orders,
            "aov": aov,
            "avg_discount_pct": avg_discount,
            "sales_mom_pct": pct_change(sales, prev_sales),
            "profit_mom_pct": pct_change(profit, prev_profit),
            "sales_yoy_pct": pct_change(sales, yoy_sales),
            "profit_yoy_pct": pct_change(profit, yoy_profit),
        },
        "regions": regions,
        "discount_bands": discount_bands,
        "worst_sub_categories": worst_subcats,
        "top_profit_sub_categories": top_subcats,
        "worst_loss_orders": worst_items,
        "auto_alerts": alerts,
    }


# ==================== 3. Prompt 工程层（防幻觉约束） ====================
SYSTEM_PROMPT = """你是一位严谨、擅长商业汇报的资深零售数据分析师。
你的任务是根据程序精准算出的 JSON 经营指标，为业务管理层撰写一份简洁、专业、可直接用于周会/月会汇报的《月度经营诊断简报》。

必须严格遵守以下规则：
1. 【零幻觉红线】严禁编造、猜测或自行推算 JSON 中未给出的任何数字；引用的所有金额、百分比、订单数必须与 JSON 完全一致。
2. 【结论先行】用业务语言表达，先抛核心结论再给数据支撑，避免像流水账一样把 JSON 逐行翻译一遍。
3. 【聚焦归因与行动】重点把“亏损子品类 / 异常地区 / 高折扣档”之间的关联串起来，给出 2～3 条具体、可落地的下月优化建议。
4. 【输出格式】使用清晰的 Markdown 格式，严格包含以下 4 个一级/二级板块：
   - 一、核心经营概览（3 句话内说清大盘、同环比与利润率健康度）
   - 二、亮点与风险预警（分点列出核心增长引擎与异常出血点）
   - 三、亏损与折扣归因诊断（结合折扣档、区域及亏损单品分析原因）
   - 四、下月优先行动建议（2～3 条可落地的业务动作，说明对象与预期目标）
"""


def build_user_prompt(metrics: dict) -> str:
    metrics_json = json.dumps(metrics, ensure_ascii=False, indent=2)
    return (
        f"以下是 {metrics['report_month']} 的零售经营精准核算数据（单位：美元 USD），"
        f"请据此生成《{metrics['report_month']} 零售经营诊断月报》：\n\n"
        f"```json\n{metrics_json}\n```"
    )


# ==================== 4. API 调用与基础一致性校验 ====================
def call_llm_api(system_prompt: str, user_prompt: str) -> str:
    """使用标准 requests 调用兼容 OpenAI 协议的大模型 API（无需额外安装 SDK）"""
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,  # 低温度保证分析严谨、不胡说八道
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def validate_report(report_text: str, metrics: dict) -> list:
    """自动化校验：检查核心指标与关键亏损品类是否在报告中被正确提及"""
    warnings = []
    ov = metrics["overview"]
    margin_str = f"{ov['profit_margin_pct']}%"
    if margin_str not in report_text:
        warnings.append(f"报告中未精确出现综合利润率 {margin_str}，请人工核对。")
    for sc in metrics["worst_sub_categories"][:2]:
        if sc["sub_category"] not in report_text:
            warnings.append(f"报告中遗漏了主要亏损品类 {sc['sub_category']}。")
    return warnings


# ==================== 5. 主流程入口 ====================
def main():
    target_ym = sys.argv[1] if len(sys.argv) > 1 else "2017-11"
    csv_path = find_csv_path()
    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)

    print(f"[1/4] 读取数据：{csv_path}")
    df = pd.read_csv(csv_path)

    print(f"[2/4] 计算 {target_ym} 精准经营指标...")
    metrics = compute_monthly_metrics(df, target_ym)

    metrics_file = out_dir / f"{target_ym}_metrics.json"
    metrics_file.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"      已保存指标包：{metrics_file}")

    user_prompt = build_user_prompt(metrics)
    prompt_file = out_dir / f"{target_ym}_prompt.txt"
    prompt_file.write_text(
        f"=== SYSTEM PROMPT ===\n{SYSTEM_PROMPT}\n\n=== USER PROMPT ===\n{user_prompt}\n",
        encoding="utf-8",
    )
    print(f"[3/4] 已生成防幻觉 Prompt：{prompt_file}")

    if not LLM_API_KEY:
        print("\n[4/4] 当前未设置 LLM_API_KEY，已自动以【离线演练模式】完成！")
        print("👉 体验方式 A（零门槛）：打开上方生成的 prompt.txt，直接复制到 DeepSeek / 豆包 / 通义千问网页版，立刻看到报告效果。")
        print("👉 体验方式 B（API 自动化）：在终端运行：")
        print('   export LLM_API_KEY="sk-你的密钥"')
        print(f"   python3 {Path(__file__).name} {target_ym}")
        return

    print(f"[4/4] 正在调用模型 {LLM_MODEL} ({LLM_BASE_URL}) 生成月度经营简报...")
    report_md = call_llm_api(SYSTEM_PROMPT, user_prompt)

    report_file = out_dir / f"{target_ym}_report.md"
    report_file.write_text(report_md, encoding="utf-8")
    print(f"      ✅ 报告已生成：{report_file}")

    warnings = validate_report(report_md, metrics)
    if warnings:
        print("\n⚠️ 自动校验提醒：")
        for w in warnings:
            print("  -", w)
    else:
        print("✅ 自动校验通过：核心利润率与主要亏损品类均已准确覆盖。")


if __name__ == "__main__":
    main()
