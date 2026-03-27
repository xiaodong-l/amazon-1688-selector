"""
节假日支持模块 (v2.4.0 Phase 1)

功能：
1. 美国节假日支持 (New Year, Thanksgiving, Christmas, etc.)
2. 中国节假日支持 (春节，国庆，清明，端午，中秋)
3. 购物节支持 (Prime Day, Black Friday, Double 11, 618)
4. 自定义节假日配置

使用示例：
```python
from .holidays import get_country_holidays, get_shopping_holidays, create_holidays_df

# 获取美国节假日
us_holidays = get_country_holidays("US", years=[2025, 2026])

# 获取购物节
shopping_holidays = get_shopping_holidays(years=[2025, 2026])

# 创建 Prophet 格式的节假日 DataFrame
holidays_df = create_holidays_df(country="US", include_shopping=True)
```

作者：GongBu ShangShu
版本：v2.4.0 Phase 1
"""
import pandas as pd
from typing import List, Dict, Optional, Union
from datetime import datetime, date
import calendar

import holidays as py_holidays

from loguru import logger


# ==================== 国家节假日 ====================

def get_country_holidays(
    country: str,
    years: Optional[Union[int, List[int]]] = None,
) -> pd.DataFrame:
    """
    获取指定国家的法定节假日
    
    Args:
        country: 国家代码 ('US', 'CN', 'GB', 'DE', 'FR', 'JP', etc.)
        years: 年份 (单个年份或年份列表)，默认当前年 + 未来 2 年
        
    Returns:
        Prophet 格式节假日 DataFrame (lower, upper, holiday)
        
    Example:
        >>> df = get_country_holidays("US", years=[2025, 2026])
        >>> print(df.head())
    """
    # 默认年份：当前年 + 未来 2 年
    if years is None:
        current_year = datetime.now().year
        years = [current_year, current_year + 1, current_year + 2]
    elif isinstance(years, int):
        years = [years]
    
    logger.info(f"获取 {country} 节假日，年份：{years}")
    
    # 创建节假日对象
    try:
        country_holidays = py_holidays.country_holidays(
            country=country,
            years=years,
            language="zh_CN" if country == "CN" else "en_US",
        )
    except Exception as e:
        logger.warning(f"无法获取 {country} 节假日：{e}")
        return pd.DataFrame(columns=["lower", "upper", "holiday"])
    
    # 转换为 DataFrame
    holidays_list = []
    for day, name in country_holidays.items():
        holidays_list.append({
            "lower": day,
            "upper": day,
            "holiday": name,
        })
    
    df = pd.DataFrame(holidays_list)
    logger.info(f"✅ 获取 {country} {len(df)} 个节假日")
    
    return df


def get_us_holidays(years: Optional[Union[int, List[int]]] = None) -> pd.DataFrame:
    """获取美国节假日"""
    return get_country_holidays("US", years)


def get_cn_holidays(years: Optional[Union[int, List[int]]] = None) -> pd.DataFrame:
    """获取中国节假日"""
    return get_country_holidays("CN", years)


# ==================== 购物节 ====================

def get_shopping_holidays(
    years: Optional[Union[int, List[int]]] = None,
    regions: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    获取主要购物节假日
    
    Args:
        years: 年份列表
        regions: 区域列表 ('US', 'CN', 'GLOBAL')，默认全部
        
    Returns:
        Prophet 格式节假日 DataFrame
        
    支持的购物节:
        - 美国：Prime Day, Black Friday, Cyber Monday
        - 中国：618, Double 11 (双 11), Double 12 (双 12)
        - 全球：Black Friday
    """
    # 默认年份
    if years is None:
        current_year = datetime.now().year
        years = [current_year, current_year + 1, current_year + 2]
    elif isinstance(years, int):
        years = [years]
    
    # 默认区域
    if regions is None:
        regions = ["US", "CN", "GLOBAL"]
    
    logger.info(f"获取购物节，年份：{years}, 区域：{regions}")
    
    holidays_list = []
    
    for year in years:
        # 美国购物节
        if "US" in regions or "GLOBAL" in regions:
            # Amazon Prime Day (通常 7 月中旬，具体日期每年不同)
            prime_day = _estimate_prime_day(year)
            if prime_day:
                holidays_list.append({
                    "lower": prime_day,
                    "upper": prime_day,
                    "holiday": "Amazon Prime Day",
                })
            
            # Black Friday (11 月第 4 个星期五)
            black_friday = _get_black_friday(year)
            holidays_list.append({
                "lower": black_friday,
                "upper": black_friday,
                "holiday": "Black Friday",
            })
            
            # Cyber Monday (Black Friday 后的星期一)
            cyber_monday = black_friday + pd.Timedelta(days=3)
            holidays_list.append({
                "lower": cyber_monday,
                "upper": cyber_monday,
                "holiday": "Cyber Monday",
            })
        
        # 中国购物节
        if "CN" in regions or "GLOBAL" in regions:
            # 618 年中大促 (6 月 18 日，通常前后一周)
            holidays_list.append({
                "lower": date(year, 6, 11),
                "upper": date(year, 6, 18),
                "holiday": "618 Shopping Festival",
            })
            
            # Double 11 / 双 11 (11 月 11 日)
            holidays_list.append({
                "lower": date(year, 11, 1),
                "upper": date(year, 11, 11),
                "holiday": "Double 11 (Singles Day)",
            })
            
            # Double 12 / 双 12 (12 月 12 日)
            holidays_list.append({
                "lower": date(year, 12, 12),
                "upper": date(year, 12, 12),
                "holiday": "Double 12",
            })
    
    df = pd.DataFrame(holidays_list)
    logger.info(f"✅ 获取 {len(df)} 个购物节")
    
    return df


def _estimate_prime_day(year: int) -> Optional[date]:
    """
    估算 Amazon Prime Day 日期
    
    Prime Day 通常在 7 月中旬的星期二或星期三
    实际日期由 Amazon 每年公布，这里使用估算
    
    Args:
        year: 年份
        
    Returns:
        估算的 Prime Day 日期
    """
    # 历史数据：Prime Day 通常在 7 月第 2 或第 3 周的星期二
    # 2023: July 11-12 (Tuesday-Wednesday)
    # 2024: July 16-17 (Tuesday-Wednesday)
    # 2025: 预计 July 15-16
    
    # 找到 7 月第 3 个星期二
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_days = cal.monthdayscalendar(year, 7)  # 7 月
    
    # 第 3 个星期二 (索引 1)
    if len(month_days) >= 3:
        tuesday_week3 = month_days[2][1]  # 第 3 周的星期二
        if tuesday_week3 > 0:
            return date(year, 7, tuesday_week3)
    
    # 备用：7 月 15 日
    return date(year, 7, 15)


def _get_black_friday(year: int) -> date:
    """
    计算 Black Friday 日期 (11 月第 4 个星期五)
    
    Args:
        year: 年份
        
    Returns:
        Black Friday 日期
    """
    # 感恩节是 11 月第 4 个星期四
    # Black Friday 是感恩节后的星期五
    
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    month_days = cal.monthdayscalendar(year, 11)  # 11 月
    
    # 第 4 个星期四 (索引 3)
    if len(month_days) >= 4:
        thursday_week4 = month_days[3][3]  # 第 4 周的星期四
        if thursday_week4 > 0:
            # Black Friday 是第二天
            thanksgiving = date(year, 11, thursday_week4)
            return thanksgiving + pd.Timedelta(days=1)
    
    # 备用：11 月 24 日左右
    return date(year, 11, 24)


# ==================== 中国特定节假日 ====================

def get_chinese_traditional_holidays(
    years: Optional[Union[int, List[int]]] = None,
) -> pd.DataFrame:
    """
    获取中国传统节假日 (农历)
    
    包括：春节，清明，端午，中秋等
    
    Args:
        years: 年份列表
        
    Returns:
        Prophet 格式节假日 DataFrame
    """
    if years is None:
        current_year = datetime.now().year
        years = [current_year, current_year + 1, current_year + 2]
    elif isinstance(years, int):
        years = [years]
    
    logger.info(f"获取中国传统节假日，年份：{years}")
    
    # 使用 Python holidays 库获取中国节假日 (包含农历节日)
    return get_country_holidays("CN", years)


def get_spring_festival_dates(years: Optional[Union[int, List[int]]] = None) -> List[date]:
    """
    获取春节日期 (农历正月初一)
    
    Args:
        years: 年份列表
        
    Returns:
        春节日期列表
    """
    if years is None:
        current_year = datetime.now().year
        years = [current_year, current_year + 1, current_year + 2]
    elif isinstance(years, int):
        years = [years]
    
    # 春节日期 (2025-2027)
    spring_festival_dates = {
        2025: date(2025, 1, 29),
        2026: date(2026, 2, 17),
        2027: date(2027, 2, 6),
        2028: date(2028, 1, 26),
        2029: date(2029, 2, 13),
        2030: date(2030, 2, 3),
    }
    
    result = []
    for year in years:
        if year in spring_festival_dates:
            result.append(spring_festival_dates[year])
        else:
            # 估算：农历正月初一通常在 1 月 21 日 -2 月 20 日之间
            # 这里使用一个简单的估算
            cn_holidays = get_country_holidays("CN", [year])
            for idx, row in cn_holidays.iterrows():
                if "Spring" in str(row["holiday"]) or "春节" in str(row["holiday"]):
                    result.append(row["lower"])
                    break
    
    return result


# ==================== 便捷函数 ====================

def create_holidays_df(
    country: Optional[str] = "US",
    include_shopping: bool = True,
    years: Optional[Union[int, List[int]]] = None,
    custom_holidays: Optional[List[Dict]] = None,
) -> pd.DataFrame:
    """
    创建综合节假日 DataFrame (用于 Prophet)
    
    Args:
        country: 国家代码，None 表示不添加国家节假日
        include_shopping: 是否包含购物节
        years: 年份列表
        custom_holidays: 自定义节假日列表
            格式：[{"lower": "2025-01-01", "upper": "2025-01-01", "holiday": "Custom"}]
        
    Returns:
        Prophet 格式节假日 DataFrame
    """
    all_holidays = []
    
    # 添加国家节假日
    if country:
        country_df = get_country_holidays(country, years)
        all_holidays.append(country_df)
    
    # 添加购物节
    if include_shopping:
        shopping_df = get_shopping_holidays(years)
        all_holidays.append(shopping_df)
    
    # 添加自定义节假日
    if custom_holidays:
        custom_df = pd.DataFrame(custom_holidays)
        all_holidays.append(custom_df)
    
    # 合并
    if all_holidays:
        result_df = pd.concat(all_holidays, ignore_index=True)
        logger.info(f"✅ 创建综合节假日 DataFrame: {len(result_df)} 个节假日")
        return result_df
    else:
        return pd.DataFrame(columns=["lower", "upper", "holiday"])


def get_holiday_names(country: str = "US") -> List[str]:
    """
    获取指定国家的所有节假日名称
    
    Args:
        country: 国家代码
        
    Returns:
        节假日名称列表
    """
    df = get_country_holidays(country)
    return df["holiday"].unique().tolist()


# ==================== 节假日效应分析 ====================

def analyze_holiday_impact(
    sales_data: pd.DataFrame,
    holidays_df: pd.DataFrame,
    date_column: str = "date",
    value_column: str = "sales",
) -> Dict[str, float]:
    """
    分析节假日对销售的影响
    
    Args:
        sales_data: 销售数据 DataFrame
        holidays_df: 节假日 DataFrame
        date_column: 日期列名
        value_column: 销售值列名
        
    Returns:
        节假日影响字典 {holiday_name: impact_percentage}
    """
    logger.info("分析节假日影响...")
    
    # 准备数据
    data = sales_data.copy()
    data[date_column] = pd.to_datetime(data[date_column])
    
    impacts = {}
    
    for holiday_name in holidays_df["holiday"].unique():
        holiday_rows = holidays_df[holidays_df["holiday"] == holiday_name]
        
        holiday_sales = []
        normal_sales = []
        
        for _, holiday in holiday_rows.iterrows():
            holiday_date = pd.to_datetime(holiday["lower"])
            
            # 节假日当天及前后 3 天的销售
            mask = (data[date_column] >= holiday_date - pd.Timedelta(days=3)) & \
                   (data[date_column] <= holiday_date + pd.Timedelta(days=3))
            holiday_sales.extend(data.loc[mask, value_column].tolist())
            
            # 同期非节假日销售 (前后 2-4 周)
            normal_mask = ((data[date_column] >= holiday_date - pd.Timedelta(weeks=4)) & \
                          (data[date_column] < holiday_date - pd.Timedelta(weeks=2))) | \
                         ((data[date_column] > holiday_date + pd.Timedelta(weeks=2)) & \
                          (data[date_column] <= holiday_date + pd.Timedelta(weeks=4)))
            normal_sales.extend(data.loc[normal_mask, value_column].tolist())
        
        if holiday_sales and normal_sales:
            avg_holiday = sum(holiday_sales) / len(holiday_sales)
            avg_normal = sum(normal_sales) / len(normal_sales)
            
            if avg_normal > 0:
                impact = ((avg_holiday - avg_normal) / avg_normal) * 100
                impacts[holiday_name] = impact
    
    logger.info(f"✅ 分析完成：{len(impacts)} 个节假日")
    return impacts


# ==================== 主函数测试 ====================

if __name__ == "__main__":
    logger.info("=== Holidays 模块测试 ===")
    
    # 测试美国节假日
    us_holidays = get_country_holidays("US", years=[2025, 2026])
    logger.info(f"美国节假日：{len(us_holidays)} 个")
    logger.info(us_holidays.head())
    
    # 测试中国节假日
    cn_holidays = get_country_holidays("CN", years=[2025, 2026])
    logger.info(f"中国节假日：{len(cn_holidays)} 个")
    logger.info(cn_holidays.head())
    
    # 测试购物节
    shopping_holidays = get_shopping_holidays(years=[2025, 2026])
    logger.info(f"购物节：{len(shopping_holidays)} 个")
    logger.info(shopping_holidays)
    
    # 测试综合节假日
    all_holidays = create_holidays_df(country="US", include_shopping=True, years=[2025, 2026])
    logger.info(f"综合节假日：{len(all_holidays)} 个")
    logger.info(all_holidays.head(10))
    
    logger.info("✅ Holidays 模块测试完成")
