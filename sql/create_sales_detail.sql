-- =============================================================================
-- Superstore 零售销售与利润分析 — MySQL 建表脚本
-- 表名：sales_detail
-- 数据来源：由 01_data_cleaning.ipynb 清洗并导出的 data/processed/superstore_clean.csv
-- 预期规模：9,994 行、27 列（21 个原始字段 + 6 个衍生字段）
-- 适用环境：MySQL 8.0+（使用 utf8mb4_0900_ai_ci 排序规则，支持中文折扣分组标签）
-- =============================================================================

-- CREATE语法 - 'sales_detail'

CREATE TABLE `sales_detail` (
  `Row ID` int unsigned NOT NULL,
  `Order ID` varchar(20) NOT NULL,
  `Order Date` date NOT NULL,
  `Ship Date` date NOT NULL,
  `Ship Mode` varchar(30) NOT NULL,
  `Customer ID` varchar(20) NOT NULL,
  `Customer Name` varchar(100) NOT NULL,
  `Segment` varchar(30) NOT NULL,
  `Country` varchar(50) NOT NULL,
  `City` varchar(80) NOT NULL,
  `State` varchar(50) NOT NULL,
  `Postal Code` varchar(5) NOT NULL,
  `Region` varchar(20) NOT NULL,
  `Product ID` varchar(25) NOT NULL,
  `Category` varchar(30) NOT NULL,
  `Sub-Category` varchar(30) NOT NULL,
  `Product Name` varchar(255) NOT NULL,
  `Sales` decimal(14,4) NOT NULL,
  `Quantity` int unsigned NOT NULL,
  `Discount` decimal(5,4) NOT NULL,
  `Profit` decimal(14,4) NOT NULL,
  `Order Year` smallint unsigned NOT NULL,
  `Order Month` tinyint unsigned NOT NULL,
  `Year-Month` char(7) NOT NULL,
  `Shipping Days` smallint unsigned NOT NULL,
  `Profit Margin` double NOT NULL,
  `Discount Band` varchar(20) NOT NULL,
  PRIMARY KEY (`Row ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
