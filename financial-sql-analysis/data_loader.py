"""
数据加载模块 - 交易日历和ETF数据加载
使用AKShare获取真实数据
"""

import akshare as ak
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH, START_DATE, END_DATE, MAX_ETF_COUNT


def load_trade_calendar():
    """使用akshare获取真实的交易日历数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 清空表
    cursor.execute("DELETE FROM trade_calendar")

    try:
        print("正在从AKShare获取真实交易日历...")
        # 使用akshare获取交易日历
        df = ak.tool_trade_date_hist_sina()

        # 筛选2024年以后的交易日
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df[df['trade_date'] >= '2024-01-01']
        df = df[df['trade_date'] <= '2026-03-10']

        all_trade_dates = sorted(df['trade_date'].dt.strftime('%Y-%m-%d').tolist())

        print(f"共获取 {len(all_trade_dates)} 个交易日")

        # 插入数据，计算前一个交易日
        for i, date_str in enumerate(all_trade_dates):
            pretrade = None
            if i > 0:
                pretrade = all_trade_dates[i - 1]

            cursor.execute("""
                INSERT OR IGNORE INTO trade_calendar (cal_date, is_trading_day, pretrade_date, remark)
                VALUES (?, 1, ?, ?)
            """, (date_str, pretrade, '交易日'))

        conn.commit()
        count = cursor.execute('SELECT COUNT(*) FROM trade_calendar').fetchone()[0]
        print(f"交易日历表已创建，共 {count} 个交易日（真实数据）")

    except Exception as e:
        print(f"AKShare API调用失败（交易日历）: {e}")
        print("将使用备用方法生成交易日历...")
        generate_fallback_calendar(conn, cursor)

    count = cursor.execute('SELECT COUNT(*) FROM trade_calendar').fetchone()[0]
    conn.close()
    return count


def generate_fallback_calendar(conn, cursor):
    """备用方法：生成交易日历（当AKShare不可用时）"""
    # 简单节假日（2024-2025年）
    holidays = [
        # 2024年节假日
        '2024-01-01', '2024-02-10', '2024-02-11', '2024-02-12', '2024-02-13', '2024-02-14', '2024-02-15', '2024-02-16', '2024-02-17',
        '2024-04-04', '2024-04-05', '2024-04-06',
        '2024-05-01', '2024-05-02', '2024-05-03',
        '2024-06-10',
        '2024-09-15', '2024-09-16', '2024-09-17',
        '2024-10-01', '2024-10-02', '2024-10-03', '2024-10-04', '2024-10-05', '2024-10-06', '2024-10-07',
        # 2025年节假日
        '2025-01-01', '2025-01-28', '2025-01-29', '2025-01-30', '2025-01-31', '2025-02-01', '2025-02-02', '2025-02-03', '2025-02-04',
        '2025-04-04', '2025-04-05', '2025-04-06',
        '2025-05-01', '2025-05-02', '2025-05-03',
        '2025-05-31',
        '2025-10-01', '2025-10-02', '2025-10-03', '2025-10-04', '2025-10-05', '2025-10-06', '2025-10-07', '2025-10-08',
    ]

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 3, 10)

    current = start_date
    all_trade_dates = []
    while current <= end_date:
        date_str = current.strftime('%Y-%m-%d')
        is_weekend = current.weekday() >= 5
        is_holiday = date_str in holidays

        if not is_weekend and not is_holiday:
            all_trade_dates.append(date_str)

        current += timedelta(days=1)

    # 插入数据
    for i, date_str in enumerate(all_trade_dates):
        pretrade = None
        if i > 0:
            pretrade = all_trade_dates[i - 1]

        cursor.execute("""
            INSERT OR IGNORE INTO trade_calendar (cal_date, is_trading_day, pretrade_date, remark)
            VALUES (?, 1, ?, ?)
        """, (date_str, pretrade, '交易日（备用）'))

    conn.commit()
    count = cursor.execute('SELECT COUNT(*) FROM trade_calendar').fetchone()[0]
    print(f"备用交易日历表已创建，共 {count} 个交易日")


def load_etf_data():
    """使用akshare获取ETF数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("正在从AKShare获取ETF列表...")

        # 使用akshare的fund_etf_spot_em获取ETF实时行情列表
        etf_df = ak.fund_etf_spot_em()
        print(f"获取到 {len(etf_df)} 只ETF")

        # 限制数量
        if len(etf_df) > MAX_ETF_COUNT:
            etf_df = etf_df.head(MAX_ETF_COUNT)

        # 处理ETF代码，添加交易所后缀
        # 上交所: 510xxx, 511xxx, 512xxx, 513xxx, 588xxx
        # 深交所: 159xxx
        def add_exchange_suffix(code):
            code = str(code).strip()
            if code.startswith(('510', '511', '512', '513', '515', '516', '517', '518', '588')):
                return code + '.SH'
            elif code.startswith(('159', '160')):
                return code + '.SZ'
            return code

        etf_df['ts_code'] = etf_df['代码'].apply(add_exchange_suffix)

        # 清空表
        cursor.execute("DELETE FROM etf_basic")

        # 插入ETF基本信息
        for _, row in etf_df.iterrows():
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO etf_basic
                    (ts_code, name, market, list_date, delist_date, type, asset_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['ts_code'],
                    row['名称'],
                    'SH' if row['ts_code'].endswith('.SH') else 'SZ',
                    None, None, 'ETF', row.get('总市值', 0) or 0
                ))
            except Exception as e:
                print(f"插入失败: {e}")
                pass

        conn.commit()
        print(f"ETF基本信息表已创建，共 {cursor.execute('SELECT COUNT(*) FROM etf_basic').fetchone()[0]} 条记录")

        # 获取ETF日线行情
        print("正在获取ETF日线行情...")
        cursor.execute("DELETE FROM etf_daily")

        # 获取所有ETF代码
        etf_codes = [row[0] for row in cursor.execute("SELECT ts_code FROM etf_basic").fetchall()]

        # 使用akshare获取每只ETF的历史数据
        for i, code in enumerate(etf_codes):
            try:
                # 转换代码格式: 510300.SH -> 510300
                symbol = code.replace('.SH', '').replace('.SZ', '')

                # 获取历史数据 - 使用 fund_etf_hist_em
                df = ak.fund_etf_hist_em(
                    symbol=symbol,
                    period='daily',
                    start_date=START_DATE,
                    end_date=END_DATE
                )

                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        trade_date = row['日期']
                        if hasattr(trade_date, 'strftime'):
                            trade_date = trade_date.strftime('%Y-%m-%d')
                        cursor.execute("""
                            INSERT OR IGNORE INTO etf_daily
                            (ts_code, trade_date, open, high, low, close, vol, amount)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            code,
                            trade_date,
                            row['开盘'],
                            row['最高'],
                            row['最低'],
                            row['收盘'],
                            row['成交量'],
                            row['成交额']
                        ))

                if (i + 1) % 10 == 0:
                    print(f"已处理 {i+1}/{len(etf_codes)} 只ETF")

            except Exception as e:
                print(f"获取 {code} 数据失败: {e}")
                continue

        conn.commit()
        print(f"ETF日线行情表已创建，共 {cursor.execute('SELECT COUNT(*) FROM etf_daily').fetchone()[0]} 条记录")

    except Exception as e:
        print(f"AKShare API调用失败: {e}")
        raise Exception("请检查AKShare配置或网络连接")

    conn.close()
