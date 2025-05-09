import clickhouse_driver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .schemas import Category, Price
from .config import settings

class CPICalculator:
    def __init__(self, db_config):
        self.db_config = db_config
        self.clickhouse_client = self._connect_clickhouse()
        self.sqlalchemy_engine = self._connect_sqlalchemy()
        self.Session = sessionmaker(bind=self.sqlalchemy_engine)

    def _connect_clickhouse(self):
        """连接到 ClickHouse 数据库"""
        return clickhouse_driver.Client(
            host=self.db_config['CLICKHOUSE_HOST'],
            port=self.db_config['CLICKHOUSE_PORT'],
            user=self.db_config['CLICKHOUSE_USER'],
            password=self.db_config['CLICKHOUSE_PASSWORD']
        )

    def _connect_sqlalchemy(self):
        """连接到 SQLAlchemy 引擎"""
        return create_engine(self.db_config['SQLALCHEMY_DATABASE_URI'])

    def compute_cpi(self, start_date, end_date):
        """计算指定日期范围内的消费者价格指数 (CPI)"""
        # 使用 ClickHouse SQL 查询计算 CPI
        sql_query = f"""
        WITH 
        -- 获取所有叶子类别的ID和权重（没有子类别的类别）
        leaf_categories AS (
            SELECT id, weight
            FROM category
            WHERE NOT EXISTS (
                SELECT 1 
                FROM category c2 
                WHERE c2.parent = category.id
            )
        ),
        -- 获取基期和报告期的价格（假设基期为上月，报告期为本月）
        price_data AS (
            SELECT 
                product_id,
                MAX(CASE WHEN date = '{start_date}' THEN price END) AS base_price,
                MAX(CASE WHEN date = '{end_date}' THEN price END) AS report_price
            FROM price
            WHERE date IN ('{start_date}', '{end_date}')  -- 替换为实际日期
            GROUP BY product_id
        ),
        -- 计算每个叶子类别的价格指数
        category_cpi AS (
            SELECT 
                p.category_id,
                EXP(AVG(LN(pd.report_price / pd.base_price))) AS price_index  -- 几何平均数
            FROM product p
            JOIN price_data pd ON p.id = pd.product_id
            JOIN leaf_categories lc ON p.category_id = lc.id
            WHERE pd.base_price > 0  -- 确保分母不为零
              AND pd.report_price IS NOT NULL
            GROUP BY p.category_id
        )
        -- 计算加权CPI
        SELECT 
            SUM(cc.price_index * lc.weight) AS CPI
        FROM category_cpi cc
        JOIN leaf_categories lc ON cc.category_id = lc.id;
        """
        
        result = self._execute_clickhouse_query(sql_query)
        return result[0][0] if result else None

    def _execute_clickhouse_query(self, query):
        """执行 ClickHouse 查询"""
        return self.clickhouse_client.execute(query)

# 示例用法
if __name__ == "__main__":
    calculator = CPICalculator(settings.DATABASE)
    start_date = '2023-01-01'
    end_date = '2023-01-31'
    cpi = calculator.compute_cpi(start_date, end_date)
    print(f"计算得到的 CPI: {cpi}")