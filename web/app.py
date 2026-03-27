"""
亚马逊选品系统 - Web 前端

使用 Flask 提供简单的 Web 界面
展示选品结果和供应商匹配

运行：python web/app.py
访问：http://localhost:5000
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request
from loguru import logger

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.amazon.collector import AmazonCollector
from src.analysis.trend_analyzer import TrendAnalyzer
from src._1688.supplier_finder import SupplierFinder
from src.utils.config import DATA_DIR

app = Flask(__name__, template_folder='templates')
logger.remove()
logger.add(sys.stdout, level="INFO")


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/products', methods=['GET'])
def get_products():
    """获取已采集的商品数据"""
    try:
        # 查找最新的 Top20 结果文件
        import glob
        result_files = sorted(DATA_DIR.glob("top*_report_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        
        if not result_files:
            return jsonify({
                "success": True,
                "products": [],
                "count": 0,
            })
        
        # 查找对应的 CSV 文件
        csv_pattern = str(result_files[0]).replace('_report_', '_').replace('.md', '.csv')
        csv_files = glob.glob(csv_pattern)
        
        if csv_files:
            import pandas as pd
            df = pd.read_csv(csv_files[0])
            products = df.to_dict('records')
            
            # 添加商品链接
            for p in products:
                if 'asin' in p and p['asin']:
                    p['link'] = f"https://www.amazon.com/dp/{p['asin']}"
            
            return jsonify({
                "success": True,
                "products": products,
                "count": len(products),
            })
        else:
            return jsonify({
                "success": True,
                "products": [],
                "count": 0,
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


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 亚马逊选品系统 - Web 服务启动")
    print("="*60)
    print("\n访问地址：http://localhost:5000")
    print("API 文档：http://localhost:5000/api/results")
    print("\n按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
