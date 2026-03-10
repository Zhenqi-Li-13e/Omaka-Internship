"""
SQL练习模块 - 10个由简到难的SQL练习
"""

import sqlite3
from config import DB_PATH


def run_sql_exercises():
    """执行10个SQL练习"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("SQL练习1：查询所有ETF的基本信息")
    print("="*60)
    print("SQL: SELECT * FROM etf_basic;")
    print("\n结果:")
    cursor.execute("SELECT * FROM etf_basic")
    results = cursor.fetchall()
    for row in results[:5]:
        print(f"  {row}")
    print(f"  ... (共 {len(results)} 条记录)")
    print("\n说明：查询所有ETF的基本信息，了解表结构")

    print("\n" + "="*60)
    print("SQL练习2：筛选在上海市场上市的ETF")
    print("="*60)
    print("SQL: SELECT ts_code, name, market FROM etf_basic WHERE market = 'SH';")
    print("\n结果:")
    cursor.execute("SELECT ts_code, name, market FROM etf_basic WHERE market = 'SH'")
    results = cursor.fetchall()
    for row in results:
        print(f"  {row}")
    print("\n说明：使用WHERE子句进行条件筛选")

    print("\n" + "="*60)
    print("SQL练习3：统计每个市场的ETF数量")
    print("="*60)
    print("SQL: SELECT market, COUNT(*) as cnt FROM etf_basic GROUP BY market;")
    print("\n结果:")
    cursor.execute("SELECT market, COUNT(*) as cnt FROM etf_basic GROUP BY market")
    results = cursor.fetchall()
    for row in results:
        print(f"  市场: {row[0]}, 数量: {row[1]}")
    print("\n说明：使用GROUP BY进行分组统计")

    print("\n" + "="*60)
    print("SQL练习4：查询最近30个交易日的所有数据")
    print("="*60)
    print("""
SQL:
SELECT d.*, b.name
FROM etf_daily d
JOIN etf_basic b ON d.ts_code = b.ts_code
WHERE d.trade_date >= (
    SELECT cal_date FROM trade_calendar
    WHERE cal_date <= date('now')
    ORDER BY cal_date DESC LIMIT 1 OFFSET 30
)
ORDER BY d.trade_date DESC
""")
    # 获取最近30个交易日的日期
    cursor.execute("""
        SELECT cal_date FROM trade_calendar
        WHERE cal_date <= date('now')
        ORDER BY cal_date DESC LIMIT 30
    """)
    recent_30_days = [row[0] for row in cursor.fetchall()]

    if recent_30_days:
        cursor.execute("""
            SELECT d.ts_code, b.name, d.trade_date, d.close, d.vol, d.amount
            FROM etf_daily d
            JOIN etf_basic b ON d.ts_code = b.ts_code
            WHERE d.trade_date = ?
            LIMIT 10
        """, (recent_30_days[0],))
        print(f"\n结果 (最近交易日 {recent_30_days[0]}):")
        results = cursor.fetchall()
        for row in results:
            print(f"  代码: {row[0]}, 名称: {row[1]}, 收盘价: {row[3]:.2f}, 成交量: {row[4]:.0f}, 成交额: {row[5]:.2f}")
    print("\n说明：理解交易日期的概念，学会使用子查询")

    print("\n" + "="*60)
    print("SQL练习5：计算每只ETF的总成交额（按代码分组求和）")
    print("="*60)
    print("SQL: SELECT ts_code, SUM(amount) as total_amount FROM etf_daily GROUP BY ts_code;")
    print("\n结果:")
    cursor.execute("""
        SELECT d.ts_code, b.name, SUM(d.amount) as total_amount
        FROM etf_daily d
        JOIN etf_basic b ON d.ts_code = b.ts_code
        GROUP BY d.ts_code
        ORDER BY total_amount DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]} ({row[1]}): 总成交额 {row[2]:,.2f}")
    print("\n说明：使用聚合函数SUM进行计算")

    print("\n" + "="*60)
    print("SQL练习6：使用窗口函数计算累计成交额")
    print("="*60)
    print("""
SQL:
SELECT ts_code, trade_date, amount,
       SUM(amount) OVER (PARTITION BY ts_code ORDER BY trade_date) as cumulative_amount
FROM etf_daily
WHERE ts_code = '510300.SH'
ORDER BY trade_date
LIMIT 10
""")
    cursor.execute("""
        SELECT ts_code, trade_date, amount,
               SUM(amount) OVER (PARTITION BY ts_code ORDER BY trade_date) as cumulative_amount
        FROM etf_daily
        WHERE ts_code = '510300.SH'
        ORDER BY trade_date
        LIMIT 10
    """)
    print("\n结果:")
    results = cursor.fetchall()
    for row in results:
        print(f"  日期: {row[1]}, 当日成交额: {row[2]:,.2f}, 累计成交额: {row[3]:,.2f}")
    print("\n说明：使用窗口函数进行累计计算")

    print("\n" + "="*60)
    print("SQL练习7：计算每只ETF的日均成交额（使用AVG聚合）")
    print("="*60)
    print("""
SQL:
SELECT ts_code, AVG(amount) as avg_amount
FROM etf_daily
GROUP BY ts_code
ORDER BY avg_amount DESC
""")
    cursor.execute("""
        SELECT ts_code, AVG(amount) as avg_amount
        FROM etf_daily
        GROUP BY ts_code
        ORDER BY avg_amount DESC
        LIMIT 10
    """)
    print("\n结果:")
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]}: 日均成交额 {row[1]:,.2f}")
    print("\n说明：使用AVG函数计算平均值")

    print("\n" + "="*60)
    print("SQL练习8：使用RANK窗口函数排名")
    print("="*60)
    print("""
SQL:
SELECT ts_code, total_amount,
       RANK() OVER (ORDER BY total_amount DESC) as rank
FROM (
    SELECT ts_code, SUM(amount) as total_amount
    FROM etf_daily
    GROUP BY ts_code
)
""")
    cursor.execute("""
        SELECT ts_code, total_amount,
               RANK() OVER (ORDER BY total_amount DESC) as rank
        FROM (
            SELECT ts_code, SUM(amount) as total_amount
            FROM etf_daily
            GROUP BY ts_code
        )
        LIMIT 10
    """)
    print("\n结果:")
    results = cursor.fetchall()
    for row in results:
        print(f"  排名 {row[2]}: {row[0]}, 总成交额 {row[1]:,.2f}")
    print("\n说明：使用RANK窗口函数进行排名")

    print("\n" + "="*60)
    print("SQL练习9：多表连接查询")
    print("="*60)
    print("""
SQL:
SELECT b.ts_code, b.name, b.market, d.trade_date, d.close, d.amount
FROM etf_basic b
JOIN etf_daily d ON b.ts_code = d.ts_code
WHERE d.trade_date >= '2025-01-01'
ORDER BY d.amount DESC
LIMIT 10
""")
    cursor.execute("""
        SELECT b.ts_code, b.name, b.market, d.trade_date, d.close, d.amount
        FROM etf_basic b
        JOIN etf_daily d ON b.ts_code = d.ts_code
        WHERE d.trade_date >= '2025-01-01'
        ORDER BY d.amount DESC
        LIMIT 10
    """)
    print("\n结果:")
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]} ({row[1]}), 日期: {row[3]}, 收盘价: {row[4]:.2f}, 成交额: {row[5]:,.2f}")
    print("\n说明：多表连接，关联查询")

    print("\n" + "="*60)
    print("SQL练习10：复杂条件查询与排序")
    print("="*60)
    print("""
SQL:
SELECT b.ts_code, b.name, b.market,
       COUNT(d.trade_date) as trade_days,
       AVG(d.amount) as avg_amount,
       MAX(d.close) as max_price,
       MIN(d.close) as min_price
FROM etf_basic b
JOIN etf_daily d ON b.ts_code = d.ts_code
WHERE d.trade_date >= '2025-01-01'
GROUP BY b.ts_code
HAVING AVG(d.amount) > 1000000
ORDER BY avg_amount DESC
""")
    cursor.execute("""
        SELECT b.ts_code, b.name, b.market,
               COUNT(d.trade_date) as trade_days,
               AVG(d.amount) as avg_amount,
               MAX(d.close) as max_price,
               MIN(d.close) as min_price
        FROM etf_basic b
        JOIN etf_daily d ON b.ts_code = d.ts_code
        WHERE d.trade_date >= '2025-01-01'
        GROUP BY b.ts_code
        HAVING AVG(d.amount) > 1000000
        ORDER BY avg_amount DESC
    """)
    print("\n结果:")
    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]} ({row[1]}): 交易天数={row[3]}, 日均成交额={row[4]:,.2f}, 最高价={row[5]:.2f}, 最低价={row[6]:.2f}")
    print("\n说明：综合使用WHERE, GROUP BY, HAVING, ORDER BY")

    conn.close()
