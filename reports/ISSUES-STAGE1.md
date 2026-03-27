# 阶段 1 代码问题清单

**生成日期:** 2026-03-27  
**优先级说明:**  
- 🔴 Critical: 必须立即修复，阻碍发布  
- 🟠 Major: 应该修复，影响功能或安全  
- 🟡 Minor: 建议修复，改进代码质量  

---

## 🟠 Major 问题 (3 个)

### M1: 软删除未自动过滤

**文件:** `src/db/repositories/product_repo.py`  
**行号:** 所有查询方法 (约 10 处)  
**影响:** 查询可能返回已软删除的记录，导致业务逻辑错误

**当前代码:**
```python
async def get_by_asin(self, asin: str) -> Optional[Product]:
    stmt = select(Product).where(Product.asin == asin)
    # ❌ 缺少：.where(Product.is_deleted == False)
```

**修复方案:**
```python
# 方案 1: 在每个查询中添加过滤
async def get_by_asin(self, asin: str) -> Optional[Product]:
    stmt = select(Product).where(
        Product.asin == asin,
        Product.is_deleted == False
    )

# 方案 2: 创建基类方法 (推荐)
class ProductRepository:
    def _active_products(self):
        return select(Product).where(Product.is_deleted == False)
    
    async def get_by_asin(self, asin: str) -> Optional[Product]:
        stmt = self._active_products().where(Product.asin == asin)
```

**优先级:** 🟠 Major  
**预计修复时间:** 30 分钟

---

### M2: get_trend() 属性访问不安全

**文件:** `src/db/repositories/history_repo.py`  
**行号:** 272  
**影响:** 可能抛出 `AttributeError` 导致趋势分析失败

**当前代码:**
```python
current_value = getattr(records[-1], value_column.key) if hasattr(records[-1], value_column.key) else None
```

**问题:** `value_column.key` 可能不是实际的属性名

**修复方案:**
```python
# 方案 1: 直接映射 metric 到属性名
metric_to_attr = {
    'price': 'price',
    'bsr': 'bsr',
    'rating': 'rating',
}
attr_name = metric_to_attr.get(metric, 'price')
current_value = getattr(records[-1], attr_name, None)

# 方案 2: 使用字典访问 (如果模型支持)
current_value = records[-1].to_dict().get(metric)
```

**优先级:** 🟠 Major  
**预计修复时间:** 15 分钟

---

### M3: reset_db() 未捕获异常

**文件:** `src/db/connection.py`  
**行号:** 247  
**影响:** 异常时全局状态不一致，可能导致后续操作失败

**当前代码:**
```python
async def reset_db_async(test_mode: bool = False):
    global _async_engine, _AsyncSessionFactory
    await drop_db_async(test_mode)
    await init_db_async(test_mode)
    # ❌ 如果 init_db_async 失败，_async_engine 可能处于不一致状态
```

**修复方案:**
```python
async def reset_db_async(test_mode: bool = False):
    global _async_engine, _AsyncSessionFactory
    
    try:
        await drop_db_async(test_mode)
        await init_db_async(test_mode)
    except Exception as e:
        logger.error(f"Reset failed: {e}")
        # 重置全局状态，避免不一致
        _async_engine = None
        _AsyncSessionFactory = None
        raise
```

**优先级:** 🟠 Major  
**预计修复时间:** 10 分钟

---

## 🟡 Minor 问题 (5 个)

### m1: 全局变量未文档化

**文件:** `src/db/connection.py`  
**行号:** 13-18  
**影响:** 代码可读性降低，新开发者可能不理解全局状态

**当前代码:**
```python
# Global engine and session factory (sync)
_engine = None
_SessionFactory = None
_Session = None

# Global async engine and session factory
_async_engine = None
_AsyncSessionFactory = None
```

**修复方案:**
```python
# Module-level global state (singleton pattern)
# These are intentionally module-private (prefixed with _)
# and should only be accessed via getter functions

_engine = None  # Cached synchronous database engine
_SessionFactory = None  # Cached synchronous session factory
_Session = None  # Cached scoped session

_async_engine = None  # Cached asynchronous database engine
_AsyncSessionFactory = None  # Cached asynchronous session factory
```

**优先级:** 🟡 Minor  
**预计修复时间:** 5 分钟

---

### m2: 缺少连接池健康检查

**文件:** `src/db/connection.py`  
**行号:** 77, 158  
**影响:** 可能使用失效的连接，导致偶发性查询失败

**当前代码:**
```python
_engine = create_engine(
    db_url,
    poolclass=QueuePool,
    pool_size=pool_size,
    max_overflow=max_overflow,
    # ❌ 缺少 pool_pre_ping
)
```

**修复方案:**
```python
_engine = create_engine(
    db_url,
    poolclass=QueuePool,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=True,    # ✅ 检测失效连接
    pool_recycle=3600,     # ✅ 1 小时后回收连接
)
```

**优先级:** 🟡 Minor  
**预计修复时间:** 5 分钟

---

### m3: get_all() 未默认预加载关联数据

**文件:** `src/db/repositories/product_repo.py`  
**行号:** 149  
**影响:** 可能导致 N+1 查询问题

**当前代码:**
```python
async def get_all(self, page: int = 1, page_size: int = 50) -> List[Product]:
    stmt = select(Product).offset(offset).limit(page_size)
    # ❌ 未预加载 images 和 features
```

**修复方案:**
```python
async def get_all(
    self,
    page: int = 1,
    page_size: int = 50,
    load_relations: bool = False,  # ✅ 新增参数
) -> List[Product]:
    if load_relations:
        stmt = select(Product).options(
            selectinload(Product.images),
            selectinload(Product.features),
        )
    else:
        stmt = select(Product)
```

**优先级:** 🟡 Minor  
**预计修复时间:** 10 分钟

---

### m4: 大数据集流式处理缺失

**文件:** `src/db/repositories/history_repo.py`  
**行号:** 272 (`get_trend`)  
**影响:** 大数据集可能占用大量内存

**当前代码:**
```python
async def get_trend(self, asin: str, days: int = 30, metric: str = 'price') -> Dict[str, Any]:
    # 一次性加载所有数据
    result = await self.session.execute(stmt)
    records = list(result.scalars().all())  # ❌ 可能很大
```

**修复方案:**
```python
# 方案 1: 使用 yield 流式返回 (适合超大集合)
async def get_trend_streaming(self, asin: str, days: int = 30):
    async for record in await self.session.stream(stmt):
        yield record

# 方案 2: 限制最大记录数
async def get_trend(self, asin: str, days: int = 30, metric: str = 'price', limit: int = 10000):
    stmt = stmt.limit(limit)  # ✅ 防止过大
```

**优先级:** 🟡 Minor  
**预计修复时间:** 20 分钟

---

### m5: 边界条件测试不足

**文件:** `tests/db/`  
**影响:** 极端情况未覆盖，可能存在隐藏 bug

**缺失的测试:**
- ❌ 极大数值 (price=999999.99)
- ❌ 超长字符串 (title=10000 chars)
- ❌ 特殊字符 (emoji, Unicode, SQL 特殊字符)
- ❌ 并发访问
- ❌ 连接池耗尽

**建议补充:**
```python
def test_product_with_extreme_values(self, db_session):
    """Test product with extreme values."""
    product = Product(
        asin="B000000007",
        title="A" * 10000,  # 超长标题
        price=999999.99,    # 极大价格
        title="Product with  emoji 🚀",  # Emoji
    )
    db_session.add(product)
    db_session.commit()
    # 验证能正常查询
```

**优先级:** 🟡 Minor  
**预计修复时间:** 2 小时

---

## 📊 问题统计

| 优先级 | 数量 | 预计修复时间 |
|--------|------|--------------|
| 🔴 Critical | 0 | 0 分钟 |
| 🟠 Major | 3 | 55 分钟 |
| 🟡 Minor | 5 | 2 小时 50 分钟 |
| **总计** | **8** | **约 3.75 小时** |

---

## 🎯 修复优先级建议

### 阶段 2 前必须修复 (Before Next Sprint)
1. M1: 软删除未自动过滤
2. M2: get_trend() 属性访问不安全
3. M3: reset_db() 未捕获异常

### 阶段 2 中修复 (During Next Sprint)
4. m2: 缺少连接池健康检查
5. m3: get_all() 未默认预加载关联数据

### 时间允许时修复 (Nice to Have)
6. m1: 全局变量未文档化
7. m4: 大数据集流式处理缺失
8. m5: 边界条件测试不足

---

## ✅ 修复验证清单

修复后应验证:
- [ ] 所有单元测试通过
- [ ] 软删除记录不出现在查询结果中
- [ ] 趋势分析不抛出异常
- [ ] reset_db 失败后全局状态正确重置
- [ ] 连接池配置生效 (检查日志)
- [ ] 大数据集查询内存占用正常

---

**文档生成:** 2026-03-27 06:51 UTC  
**审查人:** Gongbu Shangshu (工部尚书)
