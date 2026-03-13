"""
最大回撤控制模块

核心规则：
- 回撤 >= 20% + 连续2日：降至60%仓位
- 回撤 >= 25% + 连续2日：降至30%仓位
- 回撤 < 12%：恢复满仓
- 使用前一日净值计算回撤，避免Look Ahead Bias
"""

import pandas as pd


# 回撤控制参数
DD_THRESHOLD = 0.20          # 触发降仓的回撤阈值 (20%)
DD_EXTREME = 0.25            # 极端回撤阈值 (25%)
RECOVERY_THRESHOLD = 0.12    # 恢复满仓的回撤阈值 (12%)
FULL_POSITION = 1.0          # 满仓仓位
POSITION_REDUCED = 0.6       # 触发降仓后仓位 (60%)
POSITION_EXTREME = 0.3       # 极端降仓后仓位 (30%)
CONFIRM_DAYS = 2             # 反弹确认天数


class DrawdownController:
    """最大回撤控制器"""

    def __init__(self,
                 dd_threshold: float = DD_THRESHOLD,
                 dd_extreme: float = DD_EXTREME,
                 recovery_threshold: float = RECOVERY_THRESHOLD,
                 confirm_days: int = CONFIRM_DAYS):
        """
        初始化回撤控制器

        Parameters:
        -----------
        dd_threshold : float
            触发降仓的回撤阈值，默认20%
        dd_extreme : float
            极端回撤阈值，默认25%
        recovery_threshold : float
            恢复满仓的回撤阈值，默认12%
        confirm_days : int
            反弹确认天数，默认2天
        """
        self.dd_threshold = dd_threshold
        self.dd_extreme = dd_extreme
        self.recovery_threshold = recovery_threshold
        self.confirm_days = confirm_days
        self.peak_nav = None          # 历史最高净值
        self.is_reduced = False       # 是否已降仓
        self.dd_confirm_count = 0     # 回撤确认计数

    def calculate_drawdown(self, current_nav: float, prev_nav: float) -> float:
        """
        计算前一日的回撤（使用前一日净值，避免Look Ahead Bias）

        Parameters:
        -----------
        current_nav : float
            当日净值（用于更新peak）
        prev_nav : float
            前一日净值（用于计算回撤）

        Returns:
        --------
        float
            前一日的回撤（负数）
        """
        # 使用前一日净值更新历史最高（避免Look Ahead Bias）
        if self.peak_nav is None:
            self.peak_nav = prev_nav
        else:
            self.peak_nav = max(self.peak_nav, prev_nav)

        # 计算前一日回撤（用前一日净值与peak比较）
        if self.peak_nav > 0:
            drawdown = (prev_nav - self.peak_nav) / self.peak_nav
            return drawdown
        return 0.0

    def update_peak(self, current_nav: float) -> None:
        """
        更新历史最高净值

        Parameters:
        -----------
        current_nav : float
            当日净值
        """
        if self.peak_nav is None:
            self.peak_nav = current_nav
        else:
            self.peak_nav = max(self.peak_nav, current_nav)

    def get_target_position(self, current_nav: float, base_position: float) -> float:
        """
        根据回撤计算目标仓位（梯度降仓 + 反弹确认）

        Parameters:
        -----------
        current_nav : float
            当日净值
        base_position : float
            基础仓位（满仓时的仓位，如0.5表示每只ETF 50%）

        Returns:
        --------
        float
            调整后的目标仓位
        """
        # 用当日净值更新peak，计算当日回撤
        if self.peak_nav is None:
            self.peak_nav = current_nav
        else:
            self.peak_nav = max(self.peak_nav, current_nav)

        # 计算当前回撤
        if self.peak_nav > 0:
            current_drawdown = (current_nav - self.peak_nav) / self.peak_nav
        else:
            current_drawdown = 0.0

        # 核心逻辑：梯度降仓 + 反弹确认
        if current_drawdown <= -self.dd_threshold:
            # 回撤 >= 20%，进入确认流程
            self.dd_confirm_count += 1
            if self.dd_confirm_count >= self.confirm_days:
                # 连续2天回撤未修复，确认降仓
                self.is_reduced = True
                # 梯度降仓
                if current_drawdown <= -self.dd_extreme:
                    return base_position * POSITION_EXTREME  # 30%
                return base_position * POSITION_REDUCED      # 60%
            else:
                # 确认中，保持满仓
                return base_position
        else:
            # 回撤 < 阈值，重置确认计数
            self.dd_confirm_count = 0

        # 恢复逻辑
        if self.is_reduced and current_drawdown >= -self.recovery_threshold:
            self.is_reduced = False
            return base_position  # 100%仓位
        elif self.is_reduced:
            return base_position * POSITION_REDUCED
        else:
            return base_position  # 满仓

    def reset(self):
        """重置控制器状态"""
        self.peak_nav = None
        self.is_reduced = False
        self.dd_confirm_count = 0


def calculate_drawdown_series(nav: pd.Series) -> pd.DataFrame:
    """
    计算净值序列的回撤（向量化版本，用于回测后分析）

    Parameters:
    -----------
    nav : pd.Series
        净值序列

    Returns:
    --------
    pd.DataFrame
        包含净值、峰值、回撤的DataFrame
    """
    peak = nav.expanding().max()
    drawdown = (nav - peak) / peak

    return pd.DataFrame({
        'nav': nav,
        'peak': peak,
        'drawdown': drawdown
    })


# ========== 简洁的向量化接口 ==========

def apply_drawdown_control(positions_df: pd.DataFrame,
                           nav_series: pd.Series,
                           dd_threshold: float = DD_THRESHOLD,
                           dd_extreme: float = DD_EXTREME,
                           recovery_threshold: float = RECOVERY_THRESHOLD) -> pd.DataFrame:
    """
    对仓位数据应用回撤控制（向量化版本，含梯度降仓+反弹确认）

    注意：这是用于事后分析的版本。实时回测请使用 DrawdownController 类
    """
    dd_df = calculate_drawdown_series(nav_series)
    drawdowns = dd_df['drawdown']

    adjusted = positions_df.copy()
    is_reduced = False
    dd_confirm_count = 0

    for i in range(len(adjusted)):
        date = adjusted.index[i]
        current_dd = drawdowns.loc[date] if date in drawdowns.index else 0

        if current_dd <= -dd_threshold:
            dd_confirm_count += 1
            if dd_confirm_count >= 2 and not is_reduced:
                is_reduced = True
                # 梯度降仓
                if current_dd <= -dd_extreme:
                    adjusted.iloc[i] = adjusted.iloc[i] * POSITION_EXTREME
                else:
                    adjusted.iloc[i] = adjusted.iloc[i] * POSITION_REDUCED
            elif is_reduced:
                if current_dd <= -dd_extreme:
                    adjusted.iloc[i] = adjusted.iloc[i] * POSITION_EXTREME
                else:
                    adjusted.iloc[i] = adjusted.iloc[i] * POSITION_REDUCED
        else:
            dd_confirm_count = 0
            if is_reduced and current_dd >= -recovery_threshold:
                is_reduced = False

    return adjusted


if __name__ == '__main__':
    # 简单测试
    print("=" * 50)
    print("最大回撤控制测试")
    print("=" * 50)

    # 模拟净值走势
    nav = pd.Series([1.0, 1.02, 1.05, 1.08, 1.10, 1.05, 0.95, 0.88, 0.90, 0.92, 0.95, 1.00],
                    index=pd.date_range('2024-01-01', periods=12, freq='D'))

    print("\n模拟净值:")
    print(nav)

    # 计算回撤
    dd_df = calculate_drawdown_series(nav)
    print("\n回撤分析:")
    print(dd_df)

    # 测试控制器类
    print("\n" + "=" * 50)
    print("DrawdownController 测试")
    print("=" * 50)

    controller = DrawdownController(dd_threshold=0.20, recovery_threshold=0.12)

    # 模拟每日判断
    base_position = 0.5  # 每只ETF 50%

    nav_test = [1.0, 1.05, 1.10, 1.08, 1.02, 0.95, 0.90, 0.88, 0.92, 0.95, 1.00]

    print("\n日期序列回撤控制:")
    print(f"基础仓位: {base_position} (满仓)")
    print(f"降仓阈值: {DD_THRESHOLD*100}%, 极端: {DD_EXTREME*100}%")
    print(f"恢复阈值: {RECOVERY_THRESHOLD*100}%")
    print(f"反弹确认: {CONFIRM_DAYS}天")
    print("-" * 40)

    for i, nav_val in enumerate(nav_test):
        # 先计算前一日回撤
        if i > 0:
            prev_nav = nav_test[i-1]
            dd = controller.calculate_drawdown(nav_val, prev_nav)
            print(f"Day {i}: 前一日回撤 = {dd*100:.2f}%", end="")
        else:
            print(f"Day {i}: 初始", end="")

        # 获取当日目标仓位
        target = controller.get_target_position(nav_val, base_position)
        status = "【降仓】" if controller.is_reduced else "【满仓】"

        print(f" -> 目标仓位: {target*100:.0f}% {status}")
