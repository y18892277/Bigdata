"""
Generator for generating product price.
"""
import random
import datetime

class Product:
    def __init__(self, id, weight, price):
        self.id = id
        self.weight = weight
        self.price = price

def weighted_random_choice(products, k):
    weights = [p.weight for p in products]
    return random.choices(products, weights, k=k)

def generate_daily_products(product_pool, previous_day_products):
    # 抽取120个商品
    daily_products = weighted_random_choice(product_pool, 120)

    # 每天变化1%-2%
    num_changes = random.randint(1, 2)
    for _ in range(num_changes):
        index_to_replace = random.randint(0, 119)
        daily_products[index_to_replace] = weighted_random_choice(product_pool, 1)[0]

    return daily_products

def adjust_prices(products):
    for product in products:
        # 随机决定是否调整价格
        if random.random() < 0.02:  # 假设每月有2%的概率调整价格
            product.price *= random.uniform(0.9, 1.1)  # 价格变化范围在90%到110%之间

# 示例使用
product_pool = [Product(i, random.randint(1, 10), random.uniform(10, 100)) for i in range(1000)]
previous_day_products = []

for day in range(30):
    daily_products = generate_daily_products(product_pool, previous_day_products)
    previous_day_products = daily_products
    if day % 45 == 0:  # 每隔1.5个月调整价格
        adjust_prices(product_pool)
    # 处理大促期间的价格调整
    if day in [100, 200]:  # 假设大促在第100天和第200天
        adjust_prices(product_pool)

