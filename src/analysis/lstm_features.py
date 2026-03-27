"""
LSTM 特征工程模块 (v2.4 Phase 2)

为 LSTM 模型创建和准备特征数据

功能:
- 滞后特征 (lag features)
- 滚动统计特征 (rolling statistics)
- 时间特征 (temporal features)
- 价格特征 (price features)
- 目标变量创建

Author: OpenClaw Imperial - Gongbu Shangshu
Version: 2.4.0 Phase 2
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def create_features(
    df: pd.DataFrame,
    target_col: str = "sales",
    price_col: Optional[str] = None,
    date_col: str = "date",
) -> pd.DataFrame:
    """
    创建 LSTM 模型特征
    
    特征类型:
    1. 滞后特征 (Lag Features)
       - lag_1: 昨天销量
       - lag_7: 上周同天销量
       - lag_30: 上月同天销量
    
    2. 滚动统计特征 (Rolling Statistics)
       - rolling_mean_7: 7 天移动平均
       - rolling_mean_30: 30 天移动平均
       - rolling_std_7: 7 天标准差
       - rolling_std_30: 30 天标准差
       - rolling_min_7: 7 天最小值
       - rolling_max_7: 7 天最大值
    
    3. 时间特征 (Temporal Features)
       - month: 月份 (1-12)
       - day_of_week: 星期几 (0-6)
       - day_of_month: 日期 (1-31)
       - is_weekend: 是否周末
       - is_month_start: 是否月初
       - is_month_end: 是否月末
       - quarter: 季度
    
    4. 价格特征 (Price Features, 如果提供价格列)
       - price_change_pct: 价格变化百分比
       - price_rolling_mean_7: 7 天平均价格
    
    Args:
        df: 输入 DataFrame
        target_col: 目标列名 (销量)
        price_col: 价格列名 (可选)
        date_col: 日期列名
        
    Returns:
        包含所有特征的 DataFrame
    """
    logger.info(f"开始创建特征，原始数据：{len(df)} 行")
    
    # 创建副本避免修改原数据
    features_df = df.copy()
    
    # 确保日期列是 datetime 类型
    if date_col in features_df.columns:
        features_df[date_col] = pd.to_datetime(features_df[date_col])
        features_df = features_df.set_index(date_col)
    elif not isinstance(features_df.index, pd.DatetimeIndex):
        # 如果没有日期列，创建默认日期索引
        features_df.index = pd.date_range(
            end=datetime.now(),
            periods=len(features_df),
            freq="D",
        )
    
    # ========== 1. 滞后特征 ==========
    lag_periods = [1, 7, 30]
    for lag in lag_periods:
        features_df[f"lag_{lag}"] = features_df[target_col].shift(lag)
    
    logger.info(f"✓ 滞后特征创建完成：lag_1, lag_7, lag_30")
    
    # ========== 2. 滚动统计特征 ==========
    # 移动平均
    for window in [7, 30]:
        features_df[f"rolling_mean_{window}"] = (
            features_df[target_col]
            .rolling(window=window, min_periods=1)
            .mean()
        )
        features_df[f"rolling_std_{window}"] = (
            features_df[target_col]
            .rolling(window=window, min_periods=1)
            .std()
        )
    
    # 滚动最小/最大值
    features_df["rolling_min_7"] = (
        features_df[target_col]
        .rolling(window=7, min_periods=1)
        .min()
    )
    features_df["rolling_max_7"] = (
        features_df[target_col]
        .rolling(window=7, min_periods=1)
        .max()
    )
    
    # 滚动增长率
    features_df["rolling_growth_7"] = (
        features_df[target_col]
        / features_df[target_col].shift(7)
        - 1
    )
    
    logger.info(f"✓ 滚动统计特征创建完成")
    
    # ========== 3. 时间特征 ==========
    # 基本时间特征
    features_df["month"] = features_df.index.month
    features_df["day_of_week"] = features_df.index.dayofweek
    features_df["day_of_month"] = features_df.index.day
    features_df["quarter"] = features_df.index.quarter
    features_df["day_of_year"] = features_df.index.dayofyear
    features_df["week_of_year"] = features_df.index.isocalendar().week.astype(int)
    
    # 布尔特征
    features_df["is_weekend"] = (features_df.index.dayofweek >= 5).astype(int)
    features_df["is_month_start"] = features_df.index.is_month_start.astype(int)
    features_df["is_month_end"] = features_df.index.is_month_end.astype(int)
    features_df["is_quarter_start"] = features_df.index.is_quarter_start.astype(int)
    features_df["is_quarter_end"] = features_df.index.is_quarter_end.astype(int)
    
    # 周期性编码 (正弦/余弦编码，更适合神经网络)
    # 月份周期性编码
    features_df["month_sin"] = np.sin(2 * np.pi * features_df["month"] / 12)
    features_df["month_cos"] = np.cos(2 * np.pi * features_df["month"] / 12)
    
    # 星期周期性编码
    features_df["dow_sin"] = np.sin(2 * np.pi * features_df["day_of_week"] / 7)
    features_df["dow_cos"] = np.cos(2 * np.pi * features_df["day_of_week"] / 7)
    
    # 日期周期性编码
    features_df["dom_sin"] = np.sin(2 * np.pi * features_df["day_of_month"] / 31)
    features_df["dom_cos"] = np.cos(2 * np.pi * features_df["day_of_month"] / 31)
    
    logger.info(f"✓ 时间特征创建完成")
    
    # ========== 4. 价格特征 (如果提供) ==========
    if price_col and price_col in df.columns:
        # 价格变化百分比
        features_df["price_change_pct"] = features_df[price_col].pct_change()
        
        # 价格滚动统计
        features_df["price_rolling_mean_7"] = (
            features_df[price_col]
            .rolling(window=7, min_periods=1)
            .mean()
        )
        features_df["price_rolling_std_7"] = (
            features_df[price_col]
            .rolling(window=7, min_periods=1)
            .std()
        )
        
        # 价格滞后
        features_df["price_lag_1"] = features_df[price_col].shift(1)
        features_df["price_lag_7"] = features_df[price_col].shift(7)
        
        # 相对价格 (当前价格 vs 平均价格)
        features_df["price_relative"] = (
            features_df[price_col] / features_df["price_rolling_mean_7"]
        )
        
        logger.info(f"✓ 价格特征创建完成")
    
    # ========== 5. 销量衍生特征 ==========
    # 销量变化
    features_df["sales_change"] = features_df[target_col].diff()
    features_df["sales_change_pct"] = features_df[target_col].pct_change()
    
    # 销量加速度
    features_df["sales_acceleration"] = features_df["sales_change"].diff()
    
    # EMA (指数移动平均)
    features_df["ema_7"] = features_df[target_col].ewm(span=7, adjust=False).mean()
    features_df["ema_30"] = features_df[target_col].ewm(span=30, adjust=False).mean()
    
    logger.info(f"✓ 销量衍生特征创建完成")
    
    # 重置索引 (如果需要)
    if date_col in df.columns:
        features_df = features_df.reset_index()
    
    # 填充 NaN 值
    # 使用向前填充，然后用 0 填充剩余的
    features_df = features_df.fillna(method="ffill").fillna(0)
    
    # 处理无穷大值
    features_df = features_df.replace([np.inf, -np.inf], 0)
    
    logger.info(
        f"✅ 特征工程完成：共 {len(features_df.columns)} 个特征，"
        f"{len(features_df)} 行数据"
    )
    
    return features_df


def create_target(
    df: pd.DataFrame,
    target_col: str = "sales",
    horizon: int = 30,
    method: str = "mean",
) -> pd.Series:
    """
    创建目标变量 (未来 N 天的某种统计值)
    
    Args:
        df: 输入 DataFrame
        target_col: 目标列名
        horizon: 预测范围 (未来 N 天)
        method: 聚合方法
            - 'mean': 未来 N 天平均值
            - 'sum': 未来 N 天总和
            - 'max': 未来 N 天最大值
            - 'min': 未来 N 天最小值
            - 'last': 第 N 天的值
            
    Returns:
        目标变量 Series
    """
    logger.info(f"创建目标变量：horizon={horizon}, method={method}")
    
    if method == "mean":
        target = (
            df[target_col]
            .rolling(window=horizon, min_periods=1)
            .mean()
            .shift(-horizon)
        )
    elif method == "sum":
        target = (
            df[target_col]
            .rolling(window=horizon, min_periods=1)
            .sum()
            .shift(-horizon)
        )
    elif method == "max":
        target = (
            df[target_col]
            .rolling(window=horizon, min_periods=1)
            .max()
            .shift(-horizon)
        )
    elif method == "min":
        target = (
            df[target_col]
            .rolling(window=horizon, min_periods=1)
            .min()
            .shift(-horizon)
        )
    elif method == "last":
        target = df[target_col].shift(-horizon)
    else:
        raise ValueError(f"未知的方法：{method}")
    
    # 填充最后的 NaN 值 (使用最后的有效值)
    target = target.fillna(method="ffill").fillna(df[target_col].iloc[-1])
    
    logger.info(f"✅ 目标变量创建完成")
    return target


def select_features(
    df: pd.DataFrame,
    feature_cols: Optional[List[str]] = None,
    exclude_cols: Optional[List[str]] = None,
    target_col: str = "sales",
) -> List[str]:
    """
    选择用于 LSTM 模型的特征列
    
    Args:
        df: 输入 DataFrame
        feature_cols: 指定的特征列列表 (可选)
        exclude_cols: 要排除的列列表 (可选)
        target_col: 目标列名
        
    Returns:
        选中的特征列列表
    """
    if feature_cols:
        # 使用指定的特征列
        selected = [col for col in feature_cols if col in df.columns]
    else:
        # 自动选择特征列
        # 排除非特征列
        default_exclude = [
            target_col,
            "date",
            "asin",
            "title",
            "category",
        ]
        
        if exclude_cols:
            default_exclude.extend(exclude_cols)
        
        selected = [
            col for col in df.columns
            if col not in default_exclude
            and df[col].dtype in [np.int64, np.float64, np.int32, np.float32, int, float]
        ]
    
    logger.info(f"选中 {len(selected)} 个特征列")
    return selected


def prepare_lstm_data(
    df: pd.DataFrame,
    target_col: str = "sales",
    feature_cols: Optional[List[str]] = None,
    lookback: int = 60,
    forecast_horizon: int = 30,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> Dict[str, Any]:
    """
    准备 LSTM 训练数据 (一站式函数)
    
    Args:
        df: 输入 DataFrame (应已包含特征)
        target_col: 目标列名
        feature_cols: 特征列列表
        lookback: 回溯窗口
        forecast_horizon: 预测范围
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        
    Returns:
        包含以下键的字典:
        - X_train, X_val, X_test: 特征集
        - y_train, y_val, y_test: 目标集
        - feature_cols: 使用的特征列
        - scaler: 拟合的 scaler (用于反归一化)
    """
    from sklearn.preprocessing import MinMaxScaler
    
    logger.info("开始准备 LSTM 训练数据")
    
    # 选择特征
    if feature_cols is None:
        feature_cols = select_features(df, target_col=target_col)
    
    # 提取特征和目标
    X = df[feature_cols].values
    y = df[target_col].values
    
    # 归一化
    scaler_X = MinMaxScaler(feature_range=(0, 1))
    scaler_y = MinMaxScaler(feature_range=(0, 1))
    
    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).flatten()
    
    # 创建序列
    X_seq, y_seq = [], []
    
    for i in range(len(X_scaled) - lookback - forecast_horizon + 1):
        X_seq.append(X_scaled[i:i + lookback])
        y_seq.append(y_scaled[i + lookback:i + lookback + forecast_horizon].mean())
    
    X_seq = np.array(X_seq)
    y_seq = np.array(y_seq)
    
    # 划分数据集
    n_samples = len(X_seq)
    train_end = int(n_samples * train_ratio)
    val_end = int(n_samples * (train_ratio + val_ratio))
    
    X_train = X_seq[:train_end]
    X_val = X_seq[train_end:val_end]
    X_test = X_seq[val_end:]
    
    y_train = y_seq[:train_end]
    y_val = y_seq[train_end:val_end]
    y_test = y_seq[val_end:]
    
    logger.info(
        f"✅ 数据准备完成:\n"
        f"  训练集：{len(X_train)} 样本\n"
        f"  验证集：{len(X_val)} 样本\n"
        f"  测试集：{len(X_test)} 样本\n"
        f"  特征数：{X_seq.shape[1]} x {X_seq.shape[2]}"
    )
    
    return {
        "X_train": X_train,
        "X_val": X_val,
        "X_test": X_test,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
        "feature_cols": feature_cols,
        "scaler_X": scaler_X,
        "scaler_y": scaler_y,
    }


def get_feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    获取特征统计摘要
    
    Args:
        df: 输入 DataFrame
        
    Returns:
        特征统计摘要 DataFrame
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    summary = df[numeric_cols].describe().T
    summary["null_count"] = df[numeric_cols].isnull().sum()
    summary["null_pct"] = (df[numeric_cols].isnull().sum() / len(df) * 100).round(2)
    summary["dtype"] = df[numeric_cols].dtypes
    
    return summary


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    # 生成模拟数据
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=365, freq="D")
    
    df = pd.DataFrame({
        "date": dates,
        "sales": np.random.randn(365).cumsum() + 100,
        "price": np.random.uniform(10, 20, 365),
    })
    
    # 创建特征
    features_df = create_features(df, target_col="sales", price_col="price")
    
    print("\n" + "=" * 50)
    print("特征工程测试结果")
    print("=" * 50)
    print(f"原始列数：{len(df.columns)}")
    print(f"特征列数：{len(features_df.columns)}")
    print(f"\n特征列名:")
    for col in features_df.columns:
        print(f"  - {col}")
    print("=" * 50)
    
    # 创建目标
    target = create_target(features_df, target_col="sales", horizon=30)
    print(f"\n目标变量统计:")
    print(target.describe())
    print("=" * 50)
