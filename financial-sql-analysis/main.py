"""
主程序入口 - SQL金融数据分析练习

模块说明：
- config.py: 配置模块
- database.py: 数据库初始化和连接管理
- data_loader.py: 交易日历和ETF数据加载
- sql_exercises.py: 10个SQL练习
- top20_query.py: 核心任务：Top20 ETF查询
"""

from database import init_database, get_connection, close_connection
from data_loader import load_trade_calendar, load_etf_data
from sql_exercises import run_sql_exercises
from top20_query import top20_etf_by_avg_amount


def main():
    """主函数"""
    print("="*60)
    print("SQL金融数据分析练习")
    print("="*60)

    # 1. 初始化数据库
    print("\n【步骤1】初始化数据库...")
    conn = init_database()
    close_connection(conn)
    print("数据库初始化完成！")

    # 2. 生成交易日历
    print("\n【步骤2】生成交易日历表...")
    load_trade_calendar()

    # 3. 获取ETF数据
    print("\n【步骤3】获取ETF数据...")
    load_etf_data()

    # 4. 执行10个SQL练习
    print("\n【步骤4】执行SQL练习...")
    run_sql_exercises()

    # 5. 核心任务：Top20 ETF查询
    print("\n【步骤5】执行核心任务...")
    top20_etf_by_avg_amount()

    print("\n" + "="*60)
    print("所有任务完成！")
    print("="*60)


if __name__ == "__main__":
    main()
