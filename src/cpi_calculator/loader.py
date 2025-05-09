from clickhouse_driver import Client
from aliyun.oss import OssClient
import pandas as pd

class OSSDataLoader:
    def __init__(self, endpoint: str, bucket_name: str, ch_conn: dict):
        """
        :param ch_conn: ClickHouse连接配置字典
           示例: {'host': '127.0.0.1', 'port': 9000, 'user': 'admin', 'password': ''}
        """
        self.oss_client = OssClient(endpoint, bucket_name)
        self.ch_client = Client(**ch_conn)

    def load_price_data(self) -> pd.DataFrame:
        """从OSS加载价格数据"""
        # 通过ClickHouse外部表查询
        query = """
        SELECT product_id, date, price, sales_volume 
        FROM oss.products_price
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        """
        return self.ch_client.query_dataframe(query)

    def load_category_mapping(self) -> pd.DataFrame:
        """加载商品分类映射表"""
        return self.oss_client.get_object_as_df('meta/category_mapping.csv')
