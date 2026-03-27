"""
通用工具函数

目的：消除代码重复，提供统一的辅助功能
"""
from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime
import hashlib
import json


def parse_price(price_data: Any, default_symbol: str = '$') -> Tuple[Optional[float], str]:
    """
    统一解析价格数据
    
    Args:
        price_data: 价格数据 (dict/float/str/None)
        default_symbol: 默认货币符号
        
    Returns:
        (数值，格式化字符串)
        
    Examples:
        >>> parse_price({"value": 29.99, "symbol": "$"})
        (29.99, '$29.99')
        >>> parse_price(19.99)
        (19.99, '$19.99')
        >>> parse_price(None)
        (None, 'N/A')
    """
    if isinstance(price_data, dict):
        value = price_data.get('value')
        symbol = price_data.get('symbol', default_symbol)
        if value is not None:
            try:
                value = float(value)
                return value, f"{symbol}{value:.2f}"
            except (ValueError, TypeError):
                return None, "N/A"
        return None, "N/A"
    elif isinstance(price_data, (int, float)):
        try:
            value = float(price_data)
            return value, f"{default_symbol}{value:.2f}"
        except (ValueError, TypeError):
            return None, "N/A"
    elif isinstance(price_data, str):
        # 尝试解析字符串价格
        try:
            # 移除货币符号
            cleaned = price_data.replace('$', '').replace('¥', '').replace('€', '').strip()
            value = float(cleaned)
            return value, price_data
        except (ValueError, TypeError):
            return None, price_data if price_data else "N/A"
    return None, "N/A"


def safe_get(data: Dict, *keys, default: Any = None) -> Any:
    """
    安全获取嵌套字典的值
    
    Args:
        data: 字典
        *keys: 键路径
        default: 默认值
        
    Returns:
        值或默认值
        
    Examples:
        >>> safe_get({"a": {"b": {"c": 1}}}, "a", "b", "c")
        1
        >>> safe_get({"a": None}, "a", "b", default=0)
        0
    """
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default


def calculate_data_hash(data: Any, length: int = 12) -> str:
    """
    生成数据指纹 (用于缓存)
    
    Args:
        data: 任意数据
        length: 哈希长度
        
    Returns:
        哈希字符串
    """
    try:
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(json_str.encode()).hexdigest()[:length]
    except Exception:
        # 如果无法序列化，使用时间戳
        return hashlib.md5(str(datetime.now()).encode()).hexdigest()[:length]


def normalize_score(value: float, min_val: float = 0, max_val: float = 100) -> float:
    """
    将值标准化到指定范围
    
    Args:
        value: 原始值
        min_val: 最小值
        max_val: 最大值
        
    Returns:
        标准化后的值
    """
    return min(max_val, max(min_val, value))


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    格式化百分比
    
    Args:
        value: 值 (0-100)
        decimals: 小数位数
        
    Returns:
        格式化字符串
    """
    return f"{value:.{decimals}f}/100"


def truncate_text(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """
    截断文本
    
    Args:
        text: 原文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length - len(suffix)] + suffix


def batch_process(items: List[Any], batch_size: int = 100):
    """
    分批处理迭代器
    
    Args:
        items: 项目列表
        batch_size: 每批大小
        
    Yields:
        批次列表
        
    Examples:
        >>> for batch in batch_process(range(250), 100):
        ...     print(len(batch))
        100
        100
        50
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def merge_dicts(*dicts: Dict, overwrite: bool = True) -> Dict:
    """
    合并多个字典
    
    Args:
        *dicts: 要合并的字典
        overwrite: 是否覆盖已存在的键
        
    Returns:
        合并后的字典
    """
    result = {}
    for d in dicts:
        if not d:
            continue
        for key, value in d.items():
            if overwrite or key not in result:
                result[key] = value
    return result


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    安全除法
    
    Args:
        numerator: 被除数
        denominator: 除数
        default: 除数为 0 时的默认值
        
    Returns:
        商或默认值
    """
    if denominator == 0:
        return default
    return numerator / denominator


# 测试
if __name__ == "__main__":
    # 测试 parse_price
    assert parse_price({"value": 29.99, "symbol": "$"}) == (29.99, '$29.99')
    assert parse_price(19.99) == (19.99, '$19.99')
    assert parse_price(None) == (None, 'N/A')
    assert parse_price("$25.00") == (25.0, '$25.00')
    
    # 测试 safe_get
    assert safe_get({"a": {"b": 1}}, "a", "b") == 1
    assert safe_get({"a": None}, "a", "b", default=0) == 0
    
    # 测试 normalize_score
    assert normalize_score(150) == 100
    assert normalize_score(-10) == 0
    assert normalize_score(50) == 50
    
    # 测试 truncate_text
    assert truncate_text("Hello World", 5) == "He..."
    assert truncate_text("Hi", 10) == "Hi"
    
    print("✅ 所有工具函数测试通过!")
