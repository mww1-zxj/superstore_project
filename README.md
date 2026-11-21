# Superstore 零售销售与利润分析

使用 Sample Superstore 的美国零售样例数据，分析销售和利润走势，找出亏损较多的子品类与折扣档，并比较地区、客户群体和发货方式。

主文件为 [01_data_cleaning.ipynb](01_data_cleaning.ipynb)，MySQL 建表脚本为 [sql/create_sales_detail.sql](sql/create_sales_detail.sql)。原始数据覆盖 2014 年 1 月至 2017 年 12 月，一行代表一条商品销售明细，一笔订单可包含多条明细。

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

## 数据库表结构（MySQL）

建表脚本位于 [sql/create_sales_detail.sql](sql/create_sales_detail.sql)，用于在 MySQL 8.0+ 中创建 `sales_detail` 明细表，与 Notebook 导出的 `data/processed/superstore_clean.csv`（9,994 行、27 列）一一对应。

- **主键与引擎**：以 `Row ID` 为主键，使用 `InnoDB` 存储引擎。
- **字符集**：`utf8mb4` / `utf8mb4_0900_ai_ci`，兼容 `Discount Band` 中的中文标签（如使用 MySQL 5.7，可将排序规则调整为 `utf8mb4_general_ci`）。
- **字段类型要点**：
  - `Postal Code` 采用 `varchar(5)` 文本存储，避免丢失美国邮编的前导零（如 `05401`）。
  - `Sales`、`Profit` 使用 `decimal(14,4)`，`Discount` 使用 `decimal(5,4)`，避免金额与折扣率出现浮点精度误差。
  - 字段名与清洗后的 CSV 表头保持一致，包含空格或连字符（如 `Order ID`、`Sub-Category`、`Year-Month`），在 SQL 查询时需使用反引号（`` ` ``）包裹。

### 字段说明

| 字段名 | 数据类型 | 分类 | 说明 |
|---|---|---|---|
| `Row ID` | `int unsigned` | 原始字段（主键） | 行编号，唯一标识每条商品销售明细 |
| `Order ID` | `varchar(20)` | 原始字段 | 订单编号，一笔订单可包含多条商品明细 |
| `Order Date` | `date` | 原始字段 | 下单日期（`YYYY-MM-DD`） |
| `Ship Date` | `date` | 原始字段 | 发货日期（`YYYY-MM-DD`） |
| `Ship Mode` | `varchar(30)` | 原始字段 | 发货方式 |
| `Customer ID` | `varchar(20)` | 原始字段 | 客户编号 |
| `Customer Name` | `varchar(100)` | 原始字段 | 客户姓名 |
| `Segment` | `varchar(30)` | 原始字段 | 客户群体（Consumer / Corporate / Home Office） |
| `Country` | `varchar(50)` | 原始字段 | 国家 |
| `City` | `varchar(80)` | 原始字段 | 城市 |
| `State` | `varchar(50)` | 原始字段 | 州 |
| `Postal Code` | `varchar(5)` | 原始字段 | 邮政编码（文本存储，保留前导零） |
| `Region` | `varchar(20)` | 原始字段 | 地区（West / East / Central / South） |
| `Product ID` | `varchar(25)` | 原始字段 | 商品编号 |
| `Category` | `varchar(30)` | 原始字段 | 产品大类（Furniture / Office Supplies / Technology） |
| `Sub-Category` | `varchar(30)` | 原始字段 | 产品子品类 |
| `Product Name` | `varchar(255)` | 原始字段 | 商品名称 |
| `Sales` | `decimal(14,4)` | 原始字段 | 销售额（美元） |
| `Quantity` | `int unsigned` | 原始字段 | 销售数量 |
| `Discount` | `decimal(5,4)` | 原始字段 | 折扣率（0 至 1 之间的小数） |
| `Profit` | `decimal(14,4)` | 原始字段 | 利润（美元，负值表示亏损） |
| `Order Year` | `smallint unsigned` | 衍生字段 | 下单年份 |
| `Order Month` | `tinyint unsigned` | 衍生字段 | 下单月份（1–12） |
| `Year-Month` | `char(7)` | 衍生字段 | 下单年月（`YYYY-MM`） |
| `Shipping Days` | `smallint unsigned` | 衍生字段 | 发货耗时天数（`Ship Date - Order Date`） |
| `Profit Margin` | `double` | 衍生字段 | 单条明细利润率（`Profit / Sales`，小数形式；销售额为 0 时为 0） |
| `Discount Band` | `varchar(20)` | 衍生字段 | 折扣分组：`无折扣`（0%）、`低折扣`（>0% 至 20%）、`中折扣`（>20% 至 40%）、`高折扣`（>40% 至 100%） |

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

5. 导入 MySQL：先在目标数据库中执行 [sql/create_sales_detail.sql](sql/create_sales_detail.sql) 创建 `sales_detail` 表，再通过 MySQL Workbench、DBeaver 或 `LOAD DATA LOCAL INFILE` 导入 `data/processed/superstore_clean.csv`（编码选择 UTF-8，字段分隔符 `,`，跳过首行表头）。导入完成后可执行 `SELECT COUNT(*) FROM sales_detail;` 校验记录数为 9,994 条。
