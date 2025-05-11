import random
from datetime import datetime, timedelta
import csv

class Product:
    def __init__(self, id, weight, price):
        self.id = id
        self.weight = weight
        self.price = price
        self.last_price_date = datetime.now()  # 记录最近一次调价时间

    def __repr__(self):
        return f"Product(id={self.id}, price={self.price:.2f}, weight={self.weight})"


class PriceGenerator:
    def __init__(self, product_pool, daily_change_ratio=0.015, price_change_interval=(45, 75), promotion_dates=None):
        """
        初始化价格生成器

        :param product_pool: 商品池（包含Product对象的列表）
        :param daily_change_ratio: 每天变化商品的比例（默认1.5%）
        :param price_change_interval: 价格平均变化间隔（天数，默认45~75天）
        :param promotion_dates: 大促日期列表（datetime.date 或 datetime.datetime）
        """
        self.product_pool = product_pool
        self.daily_change_ratio = daily_change_ratio
        self.price_change_interval = price_change_interval
        self.promotion_dates = promotion_dates or []

    def weighted_random_choice(self, products, k):
        """
        根据权重从商品池中随机选择k个商品

        :param products: 商品池（列表）
        :param k: 需要抽取的商品数量
        :return: 抽取后的商品列表
        """
        weights = [p.weight for p in products]
        return random.choices(products, weights=weights, k=k)

    def produce_init(self):
        """
        初始生成某一天的商品池子集（120个）

        :return: 当天的商品列表
        """
        return self.weighted_random_choice(self.product_pool, k=120)

    def adjust_products(self, daily_products):
        """
        每天调整商品池，变化率为1%-2%

        :param daily_products: 当前商品列表
        :return: 调整后的商品列表
        """
        num_changes = max(1, int(len(daily_products) * self.daily_change_ratio))
        for _ in range(num_changes):
            idx = random.randint(0, len(daily_products) - 1)
            daily_products[idx] = self.weighted_random_choice(self.product_pool, 1)[0]
        return daily_products

    def adjust_prices(self, products, current_date):
        """
        调整商品价格，平均1.5到2.5个月变动一次。大促时额外增加变化。

        :param products: 当前商品列表
        :param current_date: 当前日期
        :return: 更新价格后的商品列表
        """
        avg_days = random.randint(*self.price_change_interval)

        for product in products:
            days_since_last_price = (current_date - product.last_price_date).days

            if days_since_last_price >= avg_days or current_date.date() in self.promotion_dates:
                change_ratio = random.uniform(-0.1, 0.1)  # ±10%浮动
                product.price *= (1 + change_ratio)
                product.last_price_date = current_date

        return products

    def export_to_csv(self, daily_data, filename='daily_prices.csv'):
        """
        将每日商品数据导出为 CSV 文件（使用内置 csv 模块）

        :param daily_data: price_generator 返回的数据
        :param filename: 输出文件名
        """
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Product ID', 'Price', 'Weight'])

            for day in daily_data:
                date = day['date']
                for product in day['products']:
                    writer.writerow([date, product.id, round(product.price, 2), product.weight])

def price_generator(product_pool, start_date=None, days=30, promotion_dates=None):
    """
    价格生成器主函数，模拟每日生成过程

    :param product_pool: 商品池（包含Product对象的列表）
    :param start_date: 开始日期（datetime.date 或 datetime.datetime）
    :param days: 模拟天数
    :param promotion_dates: 大促日期列表
    :return: 包含每日商品数据的字典列表
    """
    generator = PriceGenerator(product_pool, promotion_dates=promotion_dates)

    start_date = start_date or datetime.now()
    current_date = start_date
    daily_data = []

    daily_products = generator.produce_init()

    for _ in range(days):
        daily_products = generator.adjust_products(daily_products)
        daily_products = generator.adjust_prices(daily_products, current_date)

        daily_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'products': daily_products.copy()  # 使用 copy 避免引用问题
        })

        current_date += timedelta(days=1)

    # 如果指定了输出文件，则调用类方法导出

    generator.export_to_csv(daily_data)

    return daily_data
