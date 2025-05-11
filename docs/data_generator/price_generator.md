# 价格生成器
输入：category，product pool
输出：每天category下的商品及商品的信息

## 生成程序的需求
从商品池每天抽取120个，抽取的结果每天变化1%-2%，被抽取的概率和权重相关。
商品的价格平均每1.5到2.5个月变化一次。大促的时间会额外增加变化。

## 类划分、函数划分
class PriceGenerator:
    def __init__(self, product_pool):
        self.product_pool = product_pool
    def weighted_random_choice(products, k)
    def produce_init(self)
    def adjuct_products(self)
    def adjuct_prices(self)

def price_generator(product_pool):
