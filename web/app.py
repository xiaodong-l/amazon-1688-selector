"""
亚马逊选品系统 - Web 前端

使用 Flask 提供简单的 Web 界面
展示选品结果和供应商匹配

运行：python web/app.py
访问：http://localhost:5000
"""
import asyncio
import json
import os
import glob
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request, send_from_directory
from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.amazon.collector import AmazonCollector
from src.analysis.trend_analyzer import TrendAnalyzer
from src._1688.supplier_finder import SupplierFinder
from src.utils.config import DATA_DIR

# Import authentication blueprints
from web.routes.auth import auth_bp
from web.middleware.auth import init_auth

# Version
VERSION = "2.4.0"

app = Flask(__name__, template_folder='templates')
logger.remove()
logger.add(sys.stdout, level="INFO")

# Register authentication blueprint
app.register_blueprint(auth_bp)

# Initialize authentication middleware
init_auth(app)


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/charts')
def charts_page():
    """可视化图表页面"""
    return render_template('charts.html')


@app.route('/api/products', methods=['GET'])
def get_products():
    """获取已采集的商品数据 (支持增强数据)"""
    try:
        # 优先查找增强数据 (JSON)
        enhanced_files = list(DATA_DIR.glob("top20_enhanced_*.json"))
        
        if enhanced_files:
            latest_enhanced = max(enhanced_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_enhanced, 'r', encoding='utf-8') as f:
                products = json.load(f)
            
            logger.info(f"使用增强数据：{latest_enhanced.name}")
        else:
            # 使用 CSV 基础数据
            import glob
            result_files = sorted(DATA_DIR.glob("top*_report_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
            
            if not result_files:
                return jsonify({
                    "success": True,
                    "products": [],
                    "count": 0,
                })
            
            csv_pattern = str(result_files[0]).replace('_report_', '_').replace('.md', '.csv')
            csv_files = glob.glob(csv_pattern)
            
            if csv_files:
                import pandas as pd
                df = pd.read_csv(csv_files[0])
                products = df.to_dict('records')
            else:
                products = []
        
        # 确保所有商品都有 link
        for p in products:
            if 'link' not in p and 'asin' in p:
                p['link'] = f"https://www.amazon.com/dp/{p['asin']}"
        
        return jsonify({
            "success": True,
            "products": products,
            "count": len(products),
            "data_source": "enhanced" if enhanced_files else "csv",
        })
            
    except Exception as e:
        logger.error(f"获取商品失败：{e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route('/api/suppliers', methods=['POST'])
def get_suppliers():
    """获取供应商匹配"""
    data = request.json
    asin = data.get('asin')
    title = data.get('title')
    
    if not title:
        return jsonify({
            "success": False,
            "error": "缺少商品标题",
        }), 400
    
    async def find_suppliers():
        finder = SupplierFinder()
        suppliers = await finder.find_suppliers(title, limit=10)
        
        # 评估
        evaluated = [finder.evaluate_supplier(s) for s in suppliers]
        
        return evaluated
    
    try:
        suppliers = asyncio.run(find_suppliers())
        
        return jsonify({
            "success": True,
            "count": len(suppliers),
            "suppliers": suppliers,
        })
    except Exception as e:
        logger.error(f"获取供应商失败：{e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route('/api/results')
def get_results():
    """获取最新结果"""
    # 查找最新的 CSV 文件
    csv_files = sorted(DATA_DIR.glob("top*_report_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    
    if not csv_files:
        return jsonify({
            "success": True,
            "count": 0,
            "files": [],
        })
    
    # 读取最新报告
    latest_report = csv_files[0]
    with open(latest_report, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return jsonify({
        "success": True,
        "count": 1,
        "report": content,
        "file": str(latest_report),
    })


@app.route('/api/run', methods=['POST'])
def run_full_workflow():
    """运行完整工作流"""
    data = request.json
    keywords = data.get('keywords', [
        "wireless earbuds",
        "phone case",
        "laptop stand",
        "usb c cable",
        "screen protector",
    ])
    include_suppliers = data.get('include_suppliers', True)
    
    async def run():
        from src.workflow import AmazonSelectorWorkflow
        
        workflow = AmazonSelectorWorkflow(include_suppliers=include_suppliers)
        result = await workflow.run(keywords=keywords)
        
        return result
    
    try:
        result = asyncio.run(run())
        
        return jsonify({
            "success": True,
            "message": "工作流执行完成",
            "result": {
                "total_products": result["total_products"],
                "top_products_count": len(result["top_products"]),
                "csv_file": result["csv_file"],
                "report_file": result["report_file"],
            },
        })
    except Exception as e:
        logger.error(f"工作流执行失败：{e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route('/api/charts', methods=['GET'])
def get_charts():
    """获取可视化图表列表"""
    try:
        import glob
        
        # 查找图表文件
        chart_files = []
        chart_types = {
            'trend_bar': '趋势评分柱状图',
            'price_dist': '价格分布图',
            'scatter': '评分 - 销量散点图',
            'radar': '雷达图',
            'heatmap': '相关性热力图',
            'dashboard': '综合仪表板'
        }
        
        for chart_type, chart_name in chart_types.items():
            pattern = str(DATA_DIR / "charts" / f"{chart_type}_*.png")
            files = glob.glob(pattern)
            if files:
                latest = max(files, key=lambda f: os.path.getmtime(f))
                chart_files.append({
                    "type": chart_type,
                    "name": chart_name,
                    "url": f"/static/charts/{os.path.basename(latest)}",
                    "path": latest,
                    "created_at": datetime.fromtimestamp(os.path.getmtime(latest)).isoformat()
                })
            
            # 也查找 HTML 交互式图表
            pattern_html = str(DATA_DIR / "charts" / f"{chart_type}_*.html")
            files_html = glob.glob(pattern_html)
            if files_html:
                latest_html = max(files_html, key=lambda f: os.path.getmtime(f))
                chart_files.append({
                    "type": chart_type,
                    "name": chart_name + " (交互式)",
                    "url": f"/static/charts/{os.path.basename(latest_html)}",
                    "path": latest_html,
                    "created_at": datetime.fromtimestamp(os.path.getmtime(latest_html)).isoformat()
                })
        
        # 按时间排序
        chart_files.sort(key=lambda x: x['created_at'], reverse=True)
        
        # 获取商品数量
        product_count = 20  # 默认 Top20
        
        return jsonify({
            "success": True,
            "charts": chart_files,
            "product_count": product_count,
            "last_update": chart_files[0]['created_at'] if chart_files else None,
        })
    except Exception as e:
        logger.error(f"获取图表失败：{e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取分析配置信息 (v2.1 新增)"""
    try:
        from src.utils.config import (
            ANALYSIS_WEIGHTS,
            ANALYSIS_THRESHOLDS,
            CATEGORY_MARGINS,
            SEASONAL_FACTORS,
        )
        
        return jsonify({
            "success": True,
            "config": {
                "weights": ANALYSIS_WEIGHTS,
                "thresholds": {
                    "ratings_high": ANALYSIS_THRESHOLDS["ratings_high"],
                    "ratings_medium": ANALYSIS_THRESHOLDS["ratings_medium"],
                    "rating_excellent": ANALYSIS_THRESHOLDS["rating_excellent"],
                    "price_low": ANALYSIS_THRESHOLDS["price_low"],
                    "price_medium": ANALYSIS_THRESHOLDS["price_medium"],
                },
                "category_margins": CATEGORY_MARGINS,
                "seasonal_factors": SEASONAL_FACTORS,
            }
        })
    except Exception as e:
        logger.error(f"获取配置失败：{e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@app.route('/static/charts/<filename>')
def serve_chart(filename):
    """提供静态图表文件"""
    chart_dir = DATA_DIR / "charts"
    return send_from_directory(str(chart_dir), filename)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 亚马逊选品系统 - Web 服务启动")
    print("="*60)
    print("\n访问地址：http://localhost:5000")
    print("API 文档：http://localhost:5000/api/results")
    print("\n按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
