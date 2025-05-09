from clickhouse_driver import Client
from aliyun.oss import OssClient
from aliyun.sts import StsClient  # 阿里云STS SDK
import pandas as pd
import ssl

class SecureOSSDataLoader:
    def __init__(self, oss_conf: dict, ch_conf: dict):
        """
        :param oss_conf: {
            'endpoint': 'oss-cn-hangzhou-internal.aliyuncs.com',
            'bucket': 'your-bucket',
            'sts_role_arn': 'acs:ram::123456:role/cpi-reader'
        }
        :param ch_conf: ClickHouse连接配置
        """
        # 1. 获取临时安全凭证
        sts_client = StsClient()
        credentials = sts_client.assume_role(
            oss_conf['sts_role_arn'],
            'cpi-loader-session'
        )

        # 2. 初始化OSS客户端（带SSL加密）
        self.oss_client = OssClient(
            endpoint=oss_conf['endpoint'],
            bucket_name=oss_conf['bucket'],
            access_key_id=credentials.access_key_id,
            access_key_secret=credentials.access_key_secret,
            security_token=credentials.security_token,
            ssl_verify=ssl.CERT_REQUIRED
        )

        # 3. 初始化ClickHouse连接池
        self.ch_pool = Client(
            **ch_conf,
            # 启用连接池（默认5个连接）
            connections_min=3,
            connections_max=10
        )

        # 4. 预编译常用查询
        self._prepare_queries()

    def _prepare_queries(self):
        """预编译SQL模板提升性能"""
        self.price_query = self.ch_pool.compile(
            """
            SELECT product_id, date, price, sales_volume 
            FROM s3(
                'https://{bucket}.{endpoint}/data/prices.csv',
                'CSVWithNames',
                'AccessKeyId={ak}', 
                'AccessKeySecret={sk}'
            )
            WHERE date BETWEEN %(start)s AND %(end)s
            """
        )

    def load_price_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """安全加载价格数据"""
        # 使用预编译查询+参数化
        return self.ch_pool.query_dataframe(
            self.price_query,
            params={'start': start_date, 'end': end_date},
            # 自动转换日期类型
            types_check=True
        )

    def load_category_mapping(self) -> pd.DataFrame:
        """加载分类映射表"""
        # 使用OSS分块下载提升大文件性能
        return self.oss_client.get_object_as_df(
            'meta/category_mapping.csv',
            chunk_size=1024*1024  # 1MB分块
        )
