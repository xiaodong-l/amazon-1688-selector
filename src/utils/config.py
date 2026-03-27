"""
项目配置管理 (增强版)

统一所有配置项，支持环境变量覆盖
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any
from dataclasses import dataclass, field

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


# ==================== 数据库配置 ====================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "amazon_selector"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}


# ==================== 亚马逊配置 ====================
AMAZON_CONFIG = {
    # SP-API 配置
    "sp_api_id": os.getenv("AMAZON_SP_API_ID", ""),
    "sp_api_secret": os.getenv("AMAZON_SP_API_SECRET", ""),
    "sp_api_region": os.getenv("AMAZON_SP_API_REGION", "us-east-1"),
    
    # Rainforest API 配置
    "rainforest_api_key": os.getenv("RAINFOREST_API_KEY", ""),
    "rainforest_base_url": "https://api.rainforestapi.com/request",
    
    # 采集配置
    "request_delay": float(os.getenv("AMAZON_REQUEST_DELAY", 1.0)),
    "max_retries": int(os.getenv("AMAZON_MAX_RETRIES", 3)),
    "proxy_pool": os.getenv("AMAZON_PROXY_POOL", "").split(",") if os.getenv("AMAZON_PROXY_POOL") else [],
}


# ==================== 1688 配置 ====================
ALIBABA_CONFIG = {
    "request_delay": float(os.getenv("ALIBABA_REQUEST_DELAY", 1.0)),
    "max_retries": int(os.getenv("ALIBABA_MAX_RETRIES", 3)),
    "proxy_pool": os.getenv("ALIBABA_PROXY_POOL", "").split(",") if os.getenv("ALIBABA_PROXY_POOL") else [],
    "top_n_suppliers": int(os.getenv("TOP_N_SUPPLIERS", 10)),
}


# ==================== 分析阈值配置 ====================
ANALYSIS_THRESHOLDS = {
    # 评论数阈值
    "ratings_high": 10000,      # 高评论数 (成熟产品)
    "ratings_medium": 1000,     # 中评论数
    "ratings_low": 100,         # 低评论数 (新产品)
    "ratings_few": 50,          # 极少评论 (风险)
    
    # 评分阈值
    "rating_excellent": 4.5,    # 优秀评分
    "rating_good": 4.0,         # 良好评分
    "rating_average": 3.5,      # 平均评分 (低于此有风险)
    
    # 价格阈值 (USD)
    "price_low": 10,            # 低价产品
    "price_medium": 25,         # 中价产品
    "price_high": 50,           # 高价产品
    "price_premium": 100,       # 高端产品
    
    # 增长率阈值
    "growth_suspicious": 80,    # 可疑增长 (可能刷单)
    "growth_high": 60,          # 高增长
    "growth_moderate": 20,      # 中等增长
    
    # 风险阈值
    "risk_high": 50,            # 高风险
    "risk_medium": 30,          # 中风险
    "risk_low": 15,             # 低风险
    
    # 置信度阈值
    "confidence_high": 0.9,     # 高置信度
    "confidence_medium": 0.7,   # 中置信度
    "confidence_low": 0.5,      # 低置信度
}


# ==================== 分析权重配置 ====================
ANALYSIS_WEIGHTS = {
    # 基础指标权重 (65%)
    "sales_growth": 0.30,
    "review_growth": 0.20,
    "bsr_improvement": 0.15,
    
    # 增强指标权重 (35%)
    "profit_margin": 0.15,
    "market_saturation": 0.10,
    "growth_sustainability": 0.05,
    "risk_score": 0.05,  # 反向扣分
}


# ==================== 类目利润率配置 ====================
CATEGORY_MARGINS = {
    "electronics": 0.25,   # 电子产品
    "accessories": 0.35,   # 配件
    "home": 0.30,          # 家居
    "fashion": 0.40,       # 服饰
    "sports": 0.30,        # 运动
    "beauty": 0.45,        # 美妆
    "toys": 0.35,          # 玩具
    "books": 0.20,         # 图书
    "food": 0.25,          # 食品
    "pet": 0.35,           # 宠物用品
    "office": 0.30,        # 办公用品
    "garden": 0.35,        # 园艺
    "automotive": 0.30,    # 汽车用品
    "baby": 0.35,          # 婴儿用品
    "health": 0.40,        # 健康
    "default": 0.30,       # 默认
}


# ==================== 季节性因子配置 ====================
SEASONAL_FACTORS = {
    1: 0.85,   # 1 月 (淡季)
    2: 0.90,   # 2 月
    3: 0.95,   # 3 月
    4: 1.00,   # 4 月
    5: 1.05,   # 5 月
    6: 1.10,   # 6 月
    7: 0.95,   # 7 月
    8: 0.95,   # 8 月
    9: 1.05,   # 9 月 (开学季)
    10: 1.10,  # 10 月
    11: 1.30,  # 11 月 (黑五/网一)
    12: 1.40,  # 12 月 (圣诞季)
}


# ==================== 分析配置 (兼容旧版) ====================
ANALYSIS_CONFIG = {
    "top_n_products": int(os.getenv("TOP_N_PRODUCTS", 20)),
    "top_n_suppliers": int(os.getenv("TOP_N_SUPPLIERS", 10)),
    
    # 兼容旧版权重 (已迁移到 ANALYSIS_WEIGHTS)
    "weight_sales_growth": ANALYSIS_WEIGHTS["sales_growth"],
    "weight_review_growth": ANALYSIS_WEIGHTS["review_growth"],
    "weight_bsr_improvement": ANALYSIS_WEIGHTS["bsr_improvement"],
    
    # 引用其他配置
    "thresholds": ANALYSIS_THRESHOLDS,
    "weights": ANALYSIS_WEIGHTS,
    "category_margins": CATEGORY_MARGINS,
    "seasonal_factors": SEASONAL_FACTORS,
}


# ==================== 日志配置 ====================
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {module} | {message}",
}


# ==================== 缓存配置 ====================
CACHE_CONFIG = {
    "enabled": os.getenv("CACHE_ENABLED", "true").lower() == "true",
    "ttl_seconds": int(os.getenv("CACHE_TTL", 3600)),  # 默认 1 小时
    "max_size": int(os.getenv("CACHE_MAX_SIZE", 1000)),  # 最大缓存条目
}


# ==================== 可视化配置 ====================
VISUALIZATION_CONFIG = {
    "default_top_n": 20,
    "chart_dpi": 150,
    "chart_format": "png",
    "interactive_format": "html",
    "chinese_fonts": ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC'],
    "default_figsize": (14, 8),
}


# ==================== 性能配置 ====================
PERFORMANCE_CONFIG = {
    "batch_size": 100,
    "max_workers": 4,
    "request_timeout": 30,
    "retry_delay": 1.0,
}


# ==================== 验证配置完整性 ====================
def validate_config() -> bool:
    """验证配置项是否完整"""
    required_keys = [
        "top_n_products",
        "weight_sales_growth",
        "weight_review_growth",
        "weight_bsr_improvement",
    ]
    
    for key in required_keys:
        if key not in ANALYSIS_CONFIG:
            raise ValueError(f"缺少必需配置项：{key}")
    
    # 验证权重总和 (基础 + 增强应该接近 1.0)
    total_weight = sum(ANALYSIS_WEIGHTS.values())
    if abs(total_weight - 1.0) > 0.01:
        print(f"⚠️ 警告：权重总和为 {total_weight:.2f}, 建议调整为 1.0")
    
    return True


# 初始化时验证配置
validate_config()
