import random
from src.data_generator.price_generator import Product,PriceGenerator
from datetime import datetime, timedelta


def test_product_initialization():
    p = Product(1, weight=3, price=50.0)
    assert p.id == 1
    assert p.weight == 3
    assert p.price == 50.0


def test_weighted_random_choice_returns_k_items():
    product_pool = [Product(i, weight=i % 5 + 1, price=100.0) for i in range(100)]

    # 创建 PriceGenerator 实例
    generator = PriceGenerator(product_pool)

    # 调用实例方法
    selected = generator.weighted_random_choice(product_pool, 10)

    assert len(selected) == 10


def test_produce_init_returns_120_items():
    product_pool = [Product(i, weight=1, price=100.0) for i in range(100)]
    generator = PriceGenerator(product_pool)
    daily_products = generator.produce_init()
    assert len(daily_products) == 120


def test_adjust_products_changes_products_daily():
    product_pool = [Product(i, weight=1, price=100.0) for i in range(100)]
    generator = PriceGenerator(product_pool)

    daily_products = generator.produce_init()
    dp1 = generator.adjust_products(daily_products.copy())
    dp2 = generator.adjust_products(dp1.copy())

    assert dp1 != dp2  # 至少有一个商品不同


def test_generate_daily_products_changes_products_daily():
    product_pool = [Product(i, weight=1, price=100.0) for i in range(100)]
    generator = PriceGenerator(product_pool)

    daily_products = generator.produce_init()
    dp1 = generator.adjust_products(daily_products.copy())
    dp2 = generator.adjust_products(dp1.copy())

    assert dp1 != dp2  # 至少有一个商品不同

def test_adjust_prices_does_not_crash():
    product_pool = [Product(i, weight=1, price=100.0) for i in range(100)]
    generator = PriceGenerator(product_pool)

    # 假设当前日期为今天
    current_date = datetime.now()

    try:
        updated_products = generator.adjust_prices(product_pool, current_date)
        assert isinstance(updated_products, list)  # 确保返回的是商品列表
    except Exception as e:
        assert False, f"adjust_prices raised an exception: {e}"


def test_adjust_prices_actually_changes_price(capsys):
    # 强制触发价格调整逻辑
    original_random = random.random
    random.random = lambda: 0.01  # 确保随机数小于0.02，触发调价逻辑

    product = Product(1, weight=1, price=100.0)
    product.last_price_date = datetime.now() - timedelta(days=100)  # 强制让上次调价时间超过 avg_days
    generator = PriceGenerator(product_pool=[product])

    current_date = datetime.now()
    generator.adjust_prices([product], current_date)

    assert product.price != 100.0

    # 恢复原始 random.random
    random.random = original_random
