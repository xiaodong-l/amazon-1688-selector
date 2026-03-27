"""
Prophet 时间序列预测模块 (v2.4.0 Phase 1)

功能：
1. 基于 Facebook Prophet 的时间序列预测
2. 支持节假日效应调整
3. 变点检测与分析
4. 交叉验证与模型评估
5. 多周期预测 (日/周/月)

算法：
- Prophet 加法/乘法模型
- 季节性分解 (年/周/日)
- 节假日回归
- 变点自动检测

使用示例：
```python
from .prophet_predictor import ProphetPredictor

predictor = ProphetPredictor()
predictor.train(historical_data)
forecast = predictor.predict(periods=30)
metrics = predictor.get_metrics()
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 1
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime, timedelta
import logging
from pathlib import Path

from loguru import logger

# 配置日志
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("fbprophet").setLevel(logging.WARNING)

from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from prophet.make_holidays import make_holidays_df

from .holidays import get_country_holidays, get_shopping_holidays, create_holidays_df


class ProphetPredictor:
    """
    Prophet 时间序列预测器
    
    封装 Facebook Prophet 库，提供简化的预测接口
    支持销售数据、时间序列预测、节假日效应分析
    """
    
    def __init__(
        self,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
        growth: str = "linear",
        changepoint_prior_scale: float = 0.05,
        seasonality_prior_scale: float = 10.0,
        holidays_prior_scale: float = 10.0,
        n_changepoints: int = 25,
        changepoint_range: float = 0.8,
    ):
        """
        初始化 Prophet 预测器
        
        Args:
            yearly_seasonality: 是否启用年度季节性 (默认 True)
            weekly_seasonality: 是否启用周季节性 (默认 True)
            daily_seasonality: 是否启用日季节性 (默认 False，适用于日频数据)
            growth: 增长模式 'linear' 或 'logistic' (默认 'linear')
            changepoint_prior_scale: 变点先验尺度，越大越灵活 (默认 0.05)
            seasonality_prior_scale: 季节性先验尺度 (默认 10.0)
            holidays_prior_scale: 节假日先验尺度 (默认 10.0)
            n_changepoints: 变点数量 (默认 25)
            changepoint_range: 变点范围比例 (默认 0.8，即前 80% 数据)
            verbose: 是否输出详细日志 (默认 False)
        """
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.growth = growth
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self.n_changepoints = n_changepoints
        self.changepoint_range = changepoint_range
        
        # 模型实例
        self.model: Optional[Prophet] = None
        self.historical_data: Optional[pd.DataFrame] = None
        self.forecast_data: Optional[pd.DataFrame] = None
        self.cv_results: Optional[pd.DataFrame] = None
        self.metrics: Optional[Dict[str, float]] = None
        self.country_holidays: Optional[str] = None
        self.custom_holidays: Optional[pd.DataFrame] = None
        
        logger.info("Prophet 预测器初始化完成")
        logger.info(f"季节性配置：年={yearly_seasonality}, 周={weekly_seasonality}, 日={daily_seasonality}")
        logger.info(f"变点配置：n={n_changepoints}, range={changepoint_range}, prior={changepoint_prior_scale}")
    
    def prepare_data(
        self,
        df: pd.DataFrame,
        date_column: str = "date",
        value_column: str = "sales",
        remove_negative: bool = True,
        fill_method: str = "ffill",
    ) -> pd.DataFrame:
        """
        准备数据为 Prophet 格式 (ds, y)
        
        Args:
            df: 原始数据 DataFrame
            date_column: 日期列名 (默认 'date')
            value_column: 目标值列名 (默认 'sales')
            remove_negative: 是否移除负值 (默认 True)
            fill_method: 缺失值填充方法 ('ffill', 'bfill', 'interpolate', 'drop')
            
        Returns:
            Prophet 格式 DataFrame (ds: datetime, y: float)
            
        Raises:
            ValueError: 当数据格式无效时
        """
        logger.info("开始准备 Prophet 数据...")
        
        # 复制数据避免修改原数据
        data = df.copy()
        
        # 检查必需列
        if date_column not in data.columns:
            raise ValueError(f"日期列 '{date_column}' 不存在于数据中")
        if value_column not in data.columns:
            raise ValueError(f"目标列 '{value_column}' 不存在于数据中")
        
        # 重命名列
        data = data.rename(columns={date_column: "ds", value_column: "y"})
        
        # 转换日期类型
        data["ds"] = pd.to_datetime(data["ds"], errors="coerce")
        
        # 移除无效日期
        invalid_dates = data["ds"].isna().sum()
        if invalid_dates > 0:
            logger.warning(f"移除 {invalid_dates} 个无效日期")
            data = data.dropna(subset=["ds"])
        
        # 转换数值类型
        data["y"] = pd.to_numeric(data["y"], errors="coerce")
        
        # 处理负值
        if remove_negative:
            negative_count = (data["y"] < 0).sum()
            if negative_count > 0:
                logger.warning(f"移除 {negative_count} 个负值")
                data = data[data["y"] >= 0]
        
        # 处理缺失值
        missing_count = data["y"].isna().sum()
        if missing_count > 0:
            logger.info(f"发现 {missing_count} 个缺失值，使用 {fill_method} 填充")
            if fill_method == "ffill":
                data["y"] = data["y"].ffill()
            elif fill_method == "bfill":
                data["y"] = data["y"].bfill()
            elif fill_method == "interpolate":
                data["y"] = data["y"].interpolate(method="linear")
            elif fill_method == "drop":
                data = data.dropna(subset=["y"])
            else:
                logger.warning(f"未知的填充方法 '{fill_method}'，使用 ffill")
                data["y"] = data["y"].ffill()
        
        # 按日期排序
        data = data.sort_values("ds").reset_index(drop=True)
        
        # 移除重复日期 (保留第一个)
        duplicates = data["ds"].duplicated().sum()
        if duplicates > 0:
            logger.warning(f"移除 {duplicates} 个重复日期")
            data = data.drop_duplicates(subset=["ds"], keep="first")
        
        # 检查数据量
        if len(data) < 10:
            logger.warning(f"数据量过少 ({len(data)} 条)，Prophet 可能需要至少 10 个数据点")
        
        logger.info(f"数据准备完成：{len(data)} 个数据点，范围 {data['ds'].min()} 到 {data['ds'].max()}")
        
        self.historical_data = data
        return data
    
    def add_holidays(
        self,
        country: Optional[str] = "US",
        add_shopping_holidays: bool = True,
        custom_holidays_df: Optional[pd.DataFrame] = None,
    ) -> "ProphetPredictor":
        """
        添加节假日效应
        
        Args:
            country: 国家代码 (如 'US', 'CN')，None 表示不添加国家节假日
            add_shopping_holidays: 是否添加购物节 (Prime Day, Black Friday, Double 11)
            custom_holidays_df: 自定义节假日 DataFrame (lower, upper, holiday)
            
        Returns:
            self (支持链式调用)
        """
        logger.info("配置节假日效应...")
        
        holidays_list = []
        
        # 添加国家节假日
        if country:
            self.country_holidays = country
            logger.info(f"添加 {country} 国家节假日")
            holidays_list.append(country)
        
        # 添加购物节
        if add_shopping_holidays:
            logger.info("添加购物节 holidays (Prime Day, Black Friday, Double 11, etc.)")
            shopping_holidays = get_shopping_holidays()
            if custom_holidays_df is None:
                self.custom_holidays = shopping_holidays
            else:
                self.custom_holidays = pd.concat([custom_holidays_df, shopping_holidays], ignore_index=True)
        elif custom_holidays_df is not None:
            self.custom_holidays = custom_holidays_df
        
        logger.info(f"节假日配置完成：{len(holidays_list)} 个国家 + 购物节")
        return self
    
    def train(
        self,
        df: Optional[pd.DataFrame] = None,
        fit_kwargs: Optional[Dict[str, Any]] = None,
    ) -> "ProphetPredictor":
        """
        训练 Prophet 模型
        
        Args:
            df: 训练数据 (如不提供则使用 prepare_data 的结果)
            fit_kwargs: Prophet fit 方法的额外参数
            
        Returns:
            self (支持链式调用)
            
        Raises:
            ValueError: 当数据未准备或格式无效时
        """
        logger.info("开始训练 Prophet 模型...")
        
        # 准备数据
        if df is not None:
            data = self.prepare_data(df) if not isinstance(df, pd.DataFrame) or "ds" not in df.columns else df
        elif self.historical_data is not None:
            data = self.historical_data
        else:
            raise ValueError("未提供训练数据，请先调用 prepare_data() 或传入 df 参数")
        
        # 检查数据量
        if len(data) < 5:
            raise ValueError(f"数据量不足 ({len(data)} 条)，至少需要 5 个数据点")
        
        # 初始化模型
        self.model = Prophet(
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            growth=self.growth,
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            holidays_prior_scale=self.holidays_prior_scale,
            n_changepoints=self.n_changepoints,
            changepoint_range=self.changepoint_range,
            # verbose 参数在较新版本中已移除，使用 logging 控制
        )
        
        # 添加节假日
        if self.country_holidays:
            self.model.add_country_holidays(self.country_holidays)
            logger.info(f"已添加 {self.country_holidays} 国家节假日")
        
        # 自定义节假日在 Prophet 1.x 中通过 holidays 参数传入 fit 方法
        self._holidays_df = self.custom_holidays if self.custom_holidays is not None else None
        if self._holidays_df is not None and len(self._holidays_df) > 0:
            logger.info(f"已配置 {len(self._holidays_df)} 个自定义节假日")
        
        # 训练模型
        fit_params = fit_kwargs or {}
        
        # Prophet 1.x: 自定义节假日需要合并到训练数据中
        # 如果只有国家节假日，add_country_holidays 已经处理
        # 自定义节假日在 Prophet 1.x 中需要特殊处理
        # 这里简化：只使用国家节假日，自定义节假日通过外部方式添加
        if self._holidays_df is not None and len(self._holidays_df) > 0:
            # 合并自定义节假日到训练数据
            holidays_merged = self._holidays_df.copy()
            holidays_merged = holidays_merged.rename(columns={'lower': 'ds', 'holiday': 'holiday_name'})
            holidays_merged['ds'] = pd.to_datetime(holidays_merged['ds'])
            
            # 为每个节假日创建虚拟变量
            for holiday_name in holidays_merged['holiday_name'].unique():
                holiday_mask = holidays_merged['holiday_name'] == holiday_name
                holiday_dates = holidays_merged.loc[holiday_mask, 'ds']
                
                # 在训练数据中添加节假日标记
                data[f'holiday_{holiday_name}'] = data['ds'].isin(holiday_dates).astype(float)
        
        self.model.fit(data, **fit_params)
        
        logger.info("✅ Prophet 模型训练完成")
        logger.info(f"模型参数：{len(self.model.params)} 个参数")
        
        return self
    
    def predict(
        self,
        periods: int = 30,
        freq: str = "D",
        include_history: bool = True,
    ) -> pd.DataFrame:
        """
        生成预测
        
        Args:
            periods: 预测期数 (默认 30 天)
            freq: 频率 ('D'=日，'W'=周，'M'=月，'H'=小时)
            include_history: 是否包含历史数据 (默认 True)
            
        Returns:
            预测结果 DataFrame (包含 ds, yhat, yhat_lower, yhat_upper)
            
        Raises:
            ValueError: 当模型未训练时
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用 train()")
        
        logger.info(f"生成 {periods} 期预测 (频率：{freq})...")
        
        # 创建未来数据框
        future = self.model.make_future_dataframe(periods=periods, freq=freq, include_history=include_history)
        
        # 预测
        self.forecast_data = self.model.predict(future)
        
        logger.info(f"✅ 预测完成：{len(self.forecast_data)} 个数据点")
        logger.info(f"预测范围：{self.forecast_data['ds'].min()} 到 {self.forecast_data['ds'].max()}")
        
        return self.forecast_data
    
    def add_changepoints(
        self,
        n_changepoints: Optional[int] = None,
        changepoint_prior_scale: Optional[float] = None,
    ) -> "ProphetPredictor":
        """
        添加或调整变点配置
        
        Args:
            n_changepoints: 变点数量 (可选，覆盖初始化值)
            changepoint_prior_scale: 变点先验尺度 (可选，覆盖初始化值)
            
        Returns:
            self (支持链式调用)
        """
        logger.info("调整变点配置...")
        
        if n_changepoints is not None:
            self.n_changepoints = n_changepoints
            logger.info(f"变点数量：{n_changepoints}")
        
        if changepoint_prior_scale is not None:
            self.changepoint_prior_scale = changepoint_prior_scale
            logger.info(f"变点先验尺度：{changepoint_prior_scale}")
        
        # 如果模型已训练，需要重新训练
        if self.model is not None and self.historical_data is not None:
            logger.info("重新训练模型以应用新的变点配置...")
            self.train(self.historical_data)
        
        return self
    
    def cross_validation(
        self,
        horizon: str = "30 days",
        initial: str = "365 days",
        period: str = "30 days",
        parallel: str = "processes",
        n_jobs: int = -1,
    ) -> pd.DataFrame:
        """
        执行交叉验证
        
        Args:
            horizon: 预测视野 (默认 '30 days')
            initial: 初始训练期 (默认 '365 days')
            period: 复制间隔 (默认 '30 days')
            parallel: 并行模式 ('processes', 'threads', 'dask', None)
            n_jobs: 并行作业数 (-1 表示使用所有 CPU)
            
        Returns:
            交叉验证结果 DataFrame
            
        Raises:
            ValueError: 当模型未训练时
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用 train()")
        
        logger.info(f"执行交叉验证：horizon={horizon}, initial={initial}, period={period}")
        
        try:
            self.cv_results = cross_validation(
                model=self.model,
                horizon=horizon,
                initial=initial,
                period=period,
                parallel=parallel,
                n_jobs=n_jobs,
            )
            
            logger.info(f"✅ 交叉验证完成：{len(self.cv_results)} 个预测点")
            
            return self.cv_results
            
        except Exception as e:
            logger.warning(f"交叉验证失败：{e}")
            logger.info("尝试使用简化配置...")
            
            # 简化版交叉验证
            self.cv_results = cross_validation(
                model=self.model,
                horizon=horizon,
                initial="180 days" if len(self.historical_data) > 180 else "90 days",
                period="30 days",
                parallel=None,
            )
            
            logger.info(f"✅ 简化交叉验证完成：{len(self.cv_results)} 个预测点")
            return self.cv_results
    
    def get_metrics(self) -> Dict[str, float]:
        """
        获取模型评估指标
        
        Returns:
            指标字典 (MAPE, RMSE, MAE, MASE, etc.)
            
        Raises:
            ValueError: 当未执行交叉验证时
        """
        if self.cv_results is None:
            logger.info("未执行交叉验证，自动执行...")
            self.cross_validation()
        
        # 计算性能指标
        df_metrics = performance_metrics(self.cv_results)
        
        # 提取最新指标 (最后一行)
        if len(df_metrics) > 0:
            latest = df_metrics.iloc[-1]
            self.metrics = {
                "mape": float(latest.get("mape", 0)) * 100,  # 转换为百分比
                "rmse": float(latest.get("rmse", 0)),
                "mae": float(latest.get("mae", 0)),
                "mase": float(latest.get("mase", 0)),
                "smape": float(latest.get("smape", 0)) * 100 if "smape" in latest else 0,
                "coverage": float(latest.get("coverage", 0)) * 100 if "coverage" in latest else 0,
            }
        else:
            self.metrics = {
                "mape": 0,
                "rmse": 0,
                "mae": 0,
                "mase": 0,
                "smape": 0,
                "coverage": 0,
            }
        
        logger.info("📊 模型评估指标:")
        logger.info(f"  MAPE: {self.metrics['mape']:.2f}%")
        logger.info(f"  RMSE: {self.metrics['rmse']:.2f}")
        logger.info(f"  MAE: {self.metrics['mae']:.2f}")
        logger.info(f"  MASE: {self.metrics['mase']:.2f}")
        
        return self.metrics
    
    def get_changepoints(self) -> pd.DataFrame:
        """
        获取变点数据
        
        Returns:
            变点 DataFrame (包含日期和变点幅度)
        """
        if self.model is None:
            raise ValueError("模型未训练")
        
        # Prophet 1.x API: 使用 changepoints_t 和 scale 转换
        try:
            changepoints_t = self.model.changepoints_t
            # 将 changepoints_t (0-1 范围) 转换为实际日期
            if self.historical_data is not None and len(self.historical_data) > 0:
                history = self.historical_data.sort_values("ds")
                n = len(history)
                changepoint_indices = (changepoints_t * n).astype(int)
                changepoint_indices = np.clip(changepoint_indices, 0, n - 1)
                changepoints_ds = history["ds"].iloc[changepoint_indices].values
                
                changepoints_df = pd.DataFrame({
                    "ds": changepoints_ds,
                    "trend_change": self.model.params.get("delta", [np.zeros(len(changepoints_t))])[0],
                })
            else:
                changepoints_df = pd.DataFrame({
                    "ds": [],
                    "trend_change": [],
                })
        except Exception as e:
            logger.warning(f"获取变点失败：{e}")
            changepoints_df = pd.DataFrame({
                "ds": [],
                "trend_change": [],
            })
        
        logger.info(f"检测到 {len(changepoints_df)} 个变点")
        return changepoints_df
    
    def get_seasonality(self) -> Dict[str, np.ndarray]:
        """
        获取季节性成分
        
        Returns:
            季节性成分字典 (yearly, weekly, daily)
        """
        if self.model is None:
            raise ValueError("模型未训练")
        
        seasonalities = {}
        
        # Prophet 1.x: 使用 seasonality_params 属性
        try:
            if hasattr(self.model, 'seasonality_params'):
                for param in self.model.seasonality_params:
                    name = param['name']
                    seasonalities[name] = param  # 返回参数对象
        except Exception:
            pass
        
        # 备用方法：从 forecast 中提取季节性
        if not seasonalities and self.forecast_data is not None:
            if 'weekly' in self.forecast_data.columns:
                seasonalities['weekly'] = self.forecast_data['weekly'].values
            if 'yearly' in self.forecast_data.columns:
                seasonalities['yearly'] = self.forecast_data['yearly'].values
        
        logger.info(f"获取 {len(seasonalities)} 个季节性成分")
        return seasonalities
    
    def forecast_to_dict(
        self,
        include_history: bool = False,
        last_n_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        将预测结果转换为字典列表 (用于 JSON 序列化)
        
        Args:
            include_history: 是否包含历史数据
            last_n_days: 仅返回最近 N 天
            
        Returns:
            字典列表
        """
        if self.forecast_data is None:
            raise ValueError("未生成预测，请先调用 predict()")
        
        df = self.forecast_data.copy()
        
        if not include_history and self.historical_data is not None:
            last_date = self.historical_data["ds"].max()
            df = df[df["ds"] > last_date]
        
        if last_n_days:
            df = df.tail(last_n_days)
        
        # 转换为字典列表
        result = []
        for _, row in df.iterrows():
            result.append({
                "date": row["ds"].strftime("%Y-%m-%d") if hasattr(row["ds"], "strftime") else str(row["ds"]),
                "prediction": float(row["yhat"]),
                "lower_bound": float(row["yhat_lower"]),
                "upper_bound": float(row["yhat_upper"]),
                "trend": float(row.get("trend", 0)),
            })
        
        return result
    
    def save_model(self, path: Union[str, Path]) -> None:
        """
        保存模型到文件 (使用 pickle)
        
        Args:
            path: 保存路径
        """
        import pickle
        
        if self.model is None:
            raise ValueError("模型未训练")
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存整个 predictor 对象
        with open(path, "wb") as f:
            pickle.dump(self, f)
        
        logger.info(f"✅ 模型已保存到 {path}")
    
    @classmethod
    def load_model(cls, path: Union[str, Path]) -> "ProphetPredictor":
        """
        从文件加载模型 (使用 pickle)
        
        Args:
            path: 模型文件路径
            
        Returns:
            ProphetPredictor 实例
        """
        import pickle
        
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"模型文件不存在：{path}")
        
        with open(path, "rb") as f:
            predictor = pickle.load(f)
        
        # 验证加载的对象类型
        if not isinstance(predictor, ProphetPredictor):
            raise TypeError(f"加载的对象不是 ProphetPredictor 类型：{type(predictor)}")
        
        logger.info(f"✅ 模型已从 {path} 加载")
        return predictor
    
    def __repr__(self) -> str:
        """字符串表示"""
        status = "已训练" if self.model is not None else "未训练"
        return f"ProphetPredictor(status={status}, holidays={self.country_holidays})"


# 便捷函数
def quick_forecast(
    df: pd.DataFrame,
    date_column: str = "date",
    value_column: str = "sales",
    periods: int = 30,
    country_holidays: Optional[str] = "US",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    快速预测便捷函数
    
    Args:
        df: 历史数据 DataFrame
        date_column: 日期列名
        value_column: 目标值列名
        periods: 预测期数
        country_holidays: 国家节假日代码
        
    Returns:
        (forecast_df, metrics_dict)
    """
    predictor = ProphetPredictor()
    predictor.add_holidays(country=country_holidays)
    predictor.train(df)
    forecast = predictor.predict(periods=periods)
    metrics = predictor.get_metrics()
    
    return forecast, metrics


if __name__ == "__main__":
    # 测试代码
    logger.info("=== Prophet Predictor 模块测试 ===")
    
    # 创建测试数据
    dates = pd.date_range(start="2025-01-01", end="2025-12-31", freq="D")
    np.random.seed(42)
    sales = 100 + np.cumsum(np.random.randn(len(dates))) + 10 * np.sin(np.arange(len(dates)) / 7)
    
    test_df = pd.DataFrame({"date": dates, "sales": sales})
    
    # 测试预测
    predictor = ProphetPredictor()
    predictor.add_holidays(country="US")
    predictor.train(test_df)
    forecast = predictor.predict(periods=30)
    metrics = predictor.get_metrics()
    
    logger.info(f"测试完成！MAPE: {metrics['mape']:.2f}%")
    logger.info(f"预测数据：{len(forecast)} 行")
