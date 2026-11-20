# Superstore 零售销售与利润分析

使用 Sample Superstore 的美国零售样例数据，分析销售和利润走势，找出亏损较多的子品类与折扣档，并比较地区、客户群体和发货方式。

主文件为 [01_data_cleaning.ipynb](01_data_cleaning.ipynb)。原始数据覆盖 2014 年 1 月至 2017 年 12 月，一行代表一条商品销售明细，一笔订单可包含多条明细。

## 主要结果

| 指标 | 结果 |
|---|---:|
| 销售明细 | 9,994 条 |
| 订单数 | 5,009 笔 |
| 客户数 | 793 位 |
| 总销售额 | $2,297,200.86 |
| 总利润 | $286,397.02 |
| 整体利润率 | 12.47% |
| 亏损明细占比 | 18.72% |

- **优先排查 Tables。** 该子品类销售额为 $206,965.53，利润为 −$17,725.48，是亏损金额最大的子品类。
- **核查高折扣明细。** 折扣高于 40% 的 933 条明细合计亏损 $99,558.59。这里比较的是历史记录，商品和地区的构成差异也可能影响表现。
- **比较地区盈利水平。** West 的总利润最高，为 $108,418.45。Central 的利润率为 7.92%，在四个地区中最低。

## 分析口径

- 整体及各大类、地区、客户群体的利润率采用总利润除以总销售额。折扣表的 `Avg_Profit_Margin` 是同一折扣档内各商品明细利润率的算术平均，单位为百分比。
- 订单数按 `Order ID` 去重。亏损明细占比按 `Profit < 0` 的商品明细计算。
- `Shipping Days` 是下单到发货的天数。发货方式表中的订单数按订单去重，平均发货耗时按商品明细计算。

## 本地复现

1. 从数据来源下载并解压 `Sample - Superstore.csv`，放到项目根目录的 `data/raw/` 中。保留原文件名，Notebook 使用 Windows-1252 编码读取。[Kaggle 数据来源](https://www.kaggle.com/datasets/vivek468/superstore-dataset-final)
2. 使用 Python 3.13，在 Notebook 的 Python 环境安装依赖。以下为已验证的分析库版本。

   ```bash
   python -m pip install notebook pandas==2.3.3 numpy==2.3.5 matplotlib==3.10.6 seaborn==0.13.2 holoviews==1.22.0 bokeh==3.8.0
   ```

3. 从项目根目录打开 Notebook，依次运行所有单元格。图表当前指定 `STHeiti` 字体，缺少该字体的环境可能会出现 Matplotlib 字体提示。
4. 如需把最后的明细表导入 MySQL 或 Power BI，在当前 Notebook 内核的临时单元格中执行以下导出。结果应为 9,994 行、27 列，导入时将 `Postal Code` 指定为文本。

   ```python
   from pathlib import Path

   output = Path("data/processed/superstore_clean.csv")
   output.parent.mkdir(parents=True, exist_ok=True)
   df.to_csv(output, index=False, encoding="utf-8", date_format="%Y-%m-%d")
   ```
