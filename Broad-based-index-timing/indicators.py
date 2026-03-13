"""
技术指标计算模块
计算移动平均线、动量指标、波动率指标
"""

import pandas as pd
import numpy as np


def calculate_ma(data: pd.DataFrame, window: int, price_col: str = 'close') -> pd.Series:
    """
    计算移动平均线

    Parameters:
    -----------
    data : pd.DataFrame
        包含价格数据的DataFrame
    window : int
        移动平均窗口期
    price_col : str
        价格列名，默认为 'close'

    Returns:
    --------
    pd.Series
        移动平均线序列
    """
    return data[price_col].rolling(window=window).mean()


def calculate_ema(data: pd.DataFrame, window: int, price_col: str = 'close') -> pd.Series:
    """
    计算指数移动平均线

    Parameters:
    -----------
    data : pd.DataFrame
        包含价格数据的DataFrame
    window : int
        EMA窗口期
    price_col : str
        价格列名，默认为 'close'

    Returns:
    --------
    pd.Series
        EMA序列
    """
    return data[price_col].ewm(span=window, adjust=False).mean()


def calculate_momentum(data: pd.DataFrame, period: int, price_col: str = 'close') -> pd.Series:
    """
    计算动量指标 (收益率)

    Parameters:
    -----------
    data : pd.DataFrame
        包含价格数据的DataFrame
    period : int
        动量窗口期
    price_col : str
        价格列名，默认为 'close'

    Returns:
    --------
    pd.Series
        动量指标序列 (收益率)
    """
    # 计算period日收益率
    return data[price_col].pct_change(period)


def calculate_dynamic_vol_threshold(volatility: pd.Series, rolling_window: int = 250,
                                     quantile: float = 0.5) -> pd.Series:
    """
    计算动态波动率阈值（滚动分位数）

    Parameters:
    -----------
    volatility : pd.Series
        波动率序列
    rolling_window : int
        滚动窗口期，默认250
    quantile : float
        分位数，默认0.5（中位数）

    Returns:
    --------
    pd.Series
        动态波动率阈值序列
    """
    return volatility.rolling(rolling_window).quantile(quantile)


def calculate_volatility(data: pd.DataFrame, period: int, price_col: str = 'close') -> pd.Series:
    """
    计算波动率指标 (年化波动率)

    Parameters:
    -----------
    data : pd.DataFrame
        包含价格数据的DataFrame
    period : int
        波动率计算窗口期
    price_col : str
        价格列名，默认为 'close'

    Returns:
    --------
    pd.Series
        年化波动率序列
    """
    # 计算日收益率
    daily_returns = data[price_col].pct_change()

    # 计算滚动波动率 (标准差)
    rolling_std = daily_returns.rolling(window=period).std()

    # 年化波动率 (假设一年252个交易日)
    annualized_volatility = rolling_std * np.sqrt(252)

    return annualized_volatility


def calculate_rolling_sharpe(data: pd.DataFrame, period: int = 20,
                              price_col: str = 'close', risk_free_rate: float = 0.0) -> pd.Series:
    """
    计算滚动Sharpe Ratio

    Parameters:
    -----------
    data : pd.DataFrame
        包含价格数据的DataFrame
    period : int
        滚动窗口期
    price_col : str
        价格列名
    risk_free_rate : float
        年化无风险利率

    Returns:
    --------
    pd.Series
        滚动Sharpe Ratio
    """
    # 计算日收益率
    daily_returns = data[price_col].pct_change()

    # 计算滚动均值和标准差
    rolling_mean = daily_returns.rolling(window=period).mean()
    rolling_std = daily_returns.rolling(window=period).std()

    # 年化
    annualized_mean = rolling_mean * 252
    annualized_std = rolling_std * np.sqrt(252)

    # Sharpe Ratio
    sharpe = (annualized_mean - risk_free_rate) / annualized_std

    return sharpe


def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    计算平均真实波幅 (Average True Range, ATR)

    Parameters:
    -----------
    data : pd.DataFrame
        包含OHLC数据的DataFrame
    period : int
        ATR窗口期

    Returns:
    --------
    pd.Series
        ATR序列
    """
    high = data['high']
    low = data['low']
    close = data['close']

    # 计算真实波幅 (True Range)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # 计算ATR
    atr = tr.rolling(window=period).mean()

    return atr


def calculate_rsi(data: pd.DataFrame, period: int = 14, price_col: str = 'close') -> pd.Series:
    """
    计算相对强弱指标 (RSI)

    Parameters:
    -----------
    data : pd.DataFrame
        包含价格数据的DataFrame
    period : int
        RSI窗口期
    price_col : str
        价格列名

    Returns:
    --------
    pd.Series
        RSI序列
    """
    # 计算价格变动
    delta = data[price_col].diff()

    # 分离涨跌
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)

    # 计算平均涨跌
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # 计算RS
    rs = avg_gain / avg_loss

    # 计算RSI
    rsi = 100 - (100 / (1 + rs))

    return rsi


def add_all_indicators(data: pd.DataFrame, ma_short: int = 20, ma_long: int = 60,
                       momentum_window: int = 120, volatility_window: int = 20) -> pd.DataFrame:
    """
    添加所有技术指标到数据中

    Parameters:
    -----------
    data : pd.DataFrame
        包含价格数据的DataFrame
    ma_short : int
        短期均线窗口
    ma_long : int
        长期均线窗口
    momentum_window : int
        动量窗口
    volatility_window : int
        波动率窗口

    Returns:
    --------
    pd.DataFrame
        添加了所有指标的DataFrame
    """
    df = data.copy()

    # 移动平均线
    df[f'ma_{ma_short}'] = calculate_ma(df, ma_short)
    df[f'ma_{ma_long}'] = calculate_ma(df, ma_long)

    # 动量指标
    df[f'momentum_{momentum_window}'] = calculate_momentum(df, momentum_window)

    # 波动率指标
    df[f'volatility_{volatility_window}'] = calculate_volatility(df, volatility_window)

    return df


# 测试代码
if __name__ == '__main__':
    # 创建测试数据
    dates = pd.date_range('2020-01-01', periods=200, freq='D')
    test_data = pd.DataFrame({
        'close': np.random.randn(200).cumsum() + 100,
        'open': np.random.randn(200).cumsum() + 100,
        'high': np.random.randn(200).cumsum() + 102,
        'low': np.random.randn(200).cumsum() + 98,
        'volume': np.random.randint(1000000, 10000000, 200)
    }, index=dates)

    # 测试指标计算
    ma20 = calculate_ma(test_data, 20)
    ma60 = calculate_ma(test_data, 60)
    momentum = calculate_momentum(test_data, 120)
    volatility = calculate_volatility(test_data, 20)

    print("MA20:", ma20.dropna().head())
    print("MA60:", ma60.dropna().head())
    print("Momentum:", momentum.dropna().head())
    print("Volatility:", volatility.dropna().head())
