-- =============================================================================
-- Superstore 零售销售与利润分析 — MySQL 核心业务查询脚本
-- 依赖表：superstore.sales_detail（建表脚本见 sql/create_sales_detail.sql）
-- 适用环境：MySQL 8.0+（使用 CTE 与 DENSE_RANK 窗口函数）
-- =============================================================================

-- 数据预览（按需取消注释执行）
-- SELECT * FROM superstore.sales_detail LIMIT 10;


-- 1. 整体核心指标核对（与 Python Notebook 清洗结果对齐）
SELECT
    COUNT(*) AS detail_rows,
    COUNT(DISTINCT `Order ID`) AS orders,
    COUNT(DISTINCT `Customer ID`) AS customers,
    SUM(`Quantity`) AS units_sold,
    ROUND(SUM(`Sales`), 2) AS total_sales,
    ROUND(SUM(`Profit`), 2) AS total_profit,
    ROUND(100.0 * SUM(`Profit`) / NULLIF(SUM(`Sales`), 0), 2) AS margin_pct,
    ROUND(SUM(`Sales`) / NULLIF(COUNT(DISTINCT `Order ID`), 0), 2) AS avg_order_value,
    ROUND(100.0 * SUM(CASE WHEN `Profit` < 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2)
        AS loss_detail_pct
FROM superstore.sales_detail;


-- 2. 月度销售与利润趋势，以及销售额同比（YoY，对比去年同月）
WITH monthly AS (
    SELECT
        `Order Year` AS order_year,
        `Order Month` AS order_month,
        MIN(`Year-Month`) AS `year_month`,
        SUM(`Sales`) AS sales,
        SUM(`Profit`) AS profit,
        COUNT(DISTINCT `Order ID`) AS orders
    FROM superstore.sales_detail
    GROUP BY `Order Year`, `Order Month`
)
SELECT
    cur.`year_month`,
    cur.orders,
    ROUND(cur.sales, 2) AS total_sales,
    ROUND(cur.profit, 2) AS total_profit,
    ROUND(prev.sales, 2) AS last_year_sales,
    ROUND(100.0 * (cur.sales - prev.sales) / NULLIF(prev.sales, 0), 2)
        AS sales_yoy_pct
FROM monthly AS cur
LEFT JOIN monthly AS prev
    ON prev.order_year = cur.order_year - 1
   AND prev.order_month = cur.order_month
ORDER BY cur.order_year, cur.order_month;


-- 3. 商品大类表现对比（订单数、销售额、利润、整体利润率）
SELECT
    `Category` AS category,
    COUNT(DISTINCT `Order ID`) AS orders,
    ROUND(SUM(`Sales`), 2) AS total_sales,
    ROUND(SUM(`Profit`), 2) AS total_profit,
    ROUND(100.0 * SUM(`Profit`) / NULLIF(SUM(`Sales`), 0), 2) AS margin_pct
FROM superstore.sales_detail
GROUP BY `Category`
ORDER BY SUM(`Profit`) DESC;


-- 4. 折扣档表现（对比档内加权利润率与单条明细算术平均利润率）
SELECT
    `Discount Band` AS discount_band,
    COUNT(*) AS detail_rows,
    ROUND(SUM(`Sales`), 2) AS total_sales,
    ROUND(SUM(`Profit`), 2) AS total_profit,
    ROUND(100.0 * SUM(`Profit`) / NULLIF(SUM(`Sales`), 0), 2) AS band_margin_pct,
    ROUND(100.0 * AVG(`Profit Margin`), 2) AS avg_detail_margin_pct
FROM superstore.sales_detail
GROUP BY `Discount Band`
ORDER BY MIN(`Discount`);


-- 5. 合计亏损的州，按亏损金额从大到小取前 10
SELECT
    `Region` AS region,
    `State` AS state,
    ROUND(SUM(`Sales`), 2) AS total_sales,
    ROUND(SUM(`Profit`), 2) AS total_profit,
    ROUND(100.0 * SUM(`Profit`) / NULLIF(SUM(`Sales`), 0), 2) AS margin_pct
FROM superstore.sales_detail
GROUP BY `Region`, `State`
HAVING SUM(`Profit`) < 0
ORDER BY SUM(`Profit`) ASC, `State`
LIMIT 10;


-- 6. 下钻 Tables 子品类，定位亏损最严重的地区
SELECT
    `Region` AS region,
    COUNT(*) AS detail_rows,
    COUNT(DISTINCT `Order ID`) AS orders,
    ROUND(SUM(`Sales`), 2) AS total_sales,
    ROUND(SUM(`Profit`), 2) AS total_profit,
    ROUND(100.0 * SUM(`Profit`) / NULLIF(SUM(`Sales`), 0), 2) AS margin_pct
FROM superstore.sales_detail
WHERE `Sub-Category` = 'Tables'
GROUP BY `Region`
ORDER BY SUM(`Profit`) ASC;


-- 7. 各地区亏损最多的 Top 3 Tables 商品（使用 DENSE_RANK 保留并列名次）
WITH product_loss AS (
    SELECT
        `Region` AS region,
        `Product ID` AS product_id,
        `Product Name` AS product_name,
        COUNT(*) AS detail_rows,
        SUM(`Sales`) AS total_sales,
        SUM(`Profit`) AS total_profit
    FROM superstore.sales_detail
    WHERE `Sub-Category` = 'Tables'
    GROUP BY `Region`, `Product ID`, `Product Name`
    HAVING SUM(`Profit`) < 0
),
ranked AS (
    SELECT
        product_loss.*,
        DENSE_RANK() OVER (
            PARTITION BY region
            ORDER BY total_profit ASC
        ) AS loss_rank
    FROM product_loss
)
SELECT
    region,
    loss_rank,
    product_id,
    product_name,
    detail_rows,
    ROUND(total_sales, 2) AS total_sales,
    ROUND(total_profit, 2) AS total_profit
FROM ranked
WHERE loss_rank <= 3
ORDER BY region, loss_rank, product_id, product_name;


-- 8. 按发货方式比较平均发货耗时（先按订单去重聚合，每笔订单只计一次）
WITH order_shipping AS (
    SELECT
        `Order ID` AS order_id,
        `Ship Mode` AS ship_mode,
        MAX(`Shipping Days`) AS shipping_days,
        SUM(`Sales`) AS order_sales,
        SUM(`Profit`) AS order_profit
    FROM superstore.sales_detail
    GROUP BY `Order ID`, `Ship Mode`
)
SELECT
    ship_mode,
    COUNT(*) AS orders,
    ROUND(AVG(shipping_days), 2) AS avg_shipping_days,
    ROUND(SUM(order_sales), 2) AS total_sales,
    ROUND(SUM(order_profit), 2) AS total_profit
FROM order_shipping
GROUP BY ship_mode
ORDER BY avg_shipping_days ASC;
