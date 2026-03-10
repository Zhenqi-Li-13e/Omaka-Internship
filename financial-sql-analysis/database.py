"""
数据库模块 - 数据库初始化和连接管理
"""

import sqlite3
from config import DB_PATH


def get_connection():
    """获取数据库连接"""
    return sqlite3.connect(DB_PATH)


def init_database():
    """初始化数据库，创建表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建交易日历表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_calendar (
            cal_date DATE PRIMARY KEY,
            is_trading_day INTEGER DEFAULT 1,
            pretrade_date DATE,
            remark TEXT
        )
    """)

    # 创建ETF基本信息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etf_basic (
            ts_code TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            list_date DATE,
            delist_date DATE,
            type TEXT,
            asset_size REAL
        )
    """)

    # 创建ETF日线行情表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etf_daily (
            ts_code TEXT,
            trade_date DATE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            vol REAL,
            amount REAL,
            PRIMARY KEY (ts_code, trade_date)
        )
    """)

    # 创建股票基本信息表（额外练习用）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_basic (
            ts_code TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            market TEXT,
            list_date DATE
        )
    """)

    conn.commit()
    print("数据库表结构初始化完成！")
    return conn


def close_connection(conn):
    """关闭数据库连接"""
    if conn:
        conn.close()
