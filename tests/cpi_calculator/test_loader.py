# tests/test_data_loader.py
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from clickhouse_driver import Client as ClickHouseClient
from aliyun.oss import OssClient


# 需要先导入要测试的模块
from cpi_calculator.data_loader import OSSDataLoader


@pytest.fixture
def mock_ch_client():
    """创建模拟的ClickHouse客户端"""
    client = MagicMock(spec=ClickHouseClient)
    return client


@pytest.fixture
def mock_oss_client():
    """创建模拟的OSS客户端"""
    oss = MagicMock(spec=OssClient)
    return oss


@pytest.fixture
def sample_price_data():
    """创建示例价格数据"""
    return pd.DataFrame({
        'product_id': [1, 2, 3],
        'date': ['2023-01-01', '2023-01-01', '2023-01-02'],
        'price': [10.0, 20.0, 30.0],
        'sales_volume': [100, 200, 150]
    })


@pytest.fixture
def sample_category_data():
    """创建示例分类数据"""
    return pd.DataFrame({
        'product_id': [1, 2, 3],
        'category': ['food', 'clothing', 'electronics']
    })


def test_initialization(mock_oss_client, mock_ch_client):
    """测试初始化逻辑"""
    # 模拟依赖注入
    endpoint = "oss-test"
    bucket = "test-bucket"
    ch_conn = {
        'host': 'localhost',
        'port': 9000,
        'user': 'admin',
        'password': ''
    }

    loader = OSSDataLoader(endpoint, bucket, ch_conn)

    # 验证OSS客户端初始化
    assert isinstance(loader.oss_client, MagicMock)
    assert loader.oss_client._mock_new_parent._mock_name == 'OssClient'

    # 验证ClickHouse客户端初始化
    assert isinstance(loader.ch_client, MagicMock)
    assert loader.ch_client._mock_new_parent._mock_name == 'ClickHouseClient'


@patch('cpi_calculator.data_loader.ClickHouseClient')
def test_clickhouse_connection_error(mock_ch_class):
    """测试ClickHouse连接失败"""
    mock_ch_class.side_effect = Exception("Connection failed")

    ch_conn = {
        'host': 'localhost',
        'port': 9000,
        'user': 'admin',
        'password': ''
    }

    with pytest.raises(Exception) as exc_info:
        OSSDataLoader("oss-test", "test-bucket", ch_conn)

    assert "初始化ClickHouse连接失败" in str(exc_info.value)


def test_load_price_data_success(mock_ch_client, sample_price_data):
    """测试成功加载价格数据"""
    # 设置模拟返回值
    mock_ch_client.query_dataframe.return_value = sample_price_data

    # 创建测试实例
    loader = MagicMock(spec=OSSDataLoader)
    loader.ch_client = mock_ch_client

    # 执行方法
    result = OSSDataLoader.load_price_data(loader)

    # 验证结果
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert all(col in result.columns for col in ['product_id', 'date', 'price', 'sales_volume'])


def test_load_price_data_query_error(mock_ch_client):
    """测试ClickHouse查询失败"""
    # 模拟查询异常
    mock_ch_client.query_dataframe.side_effect = Exception("Query failed")

    # 创建测试实例
    loader = MagicMock(spec=OSSDataLoader)
    loader.ch_client = mock_ch_client

    # 验证异常处理
    with pytest.raises(Exception) as exc_info:
        OSSDataLoader.load_price_data(loader)

    assert "价格数据查询失败" in str(exc_info.value)


def test_load_category_mapping_success(mock_oss_client, sample_category_data):
    """测试成功加载分类映射"""
    # 模拟OSS读取
    mock_oss_client.get_object_as_df.return_value = sample_category_data

    # 创建测试实例
    loader = MagicMock(spec=OSSDataLoader)
    loader.oss_client = mock_oss_client

    # 执行方法
    result = OSSDataLoader.load_category_mapping(loader)

    # 验证结果
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    assert all(col in result.columns for col in ['product_id', 'category'])


def test_load_category_mapping_oss_error(mock_oss_client):
    """测试OSS读取失败"""
    # 模拟OSS异常
    mock_oss_client.get_object_as_df.side_effect = Exception("OSS read failed")

    # 创建测试实例
    loader = MagicMock(spec=OSSDataLoader)
    loader.oss_client = mock_oss_client

    # 验证异常处理
    with pytest.raises(Exception) as exc_info:
        OSSDataLoader.load_category_mapping(loader)

    assert "分类映射读取失败" in str(exc_info.value)


def test_query_parameter_interpolation(mock_ch_client, sample_price_data):
    """测试查询参数插值"""
    # 设置模拟返回值
    mock_ch_client.query_dataframe.return_value = sample_price_data

    # 创建测试实例
    loader = MagicMock(spec=OSSDataLoader)
    loader.ch_client = mock_ch_client

    # 修改方法以测试日期范围
    def custom_load_price_data(self, start_date='2023-01-01', end_date='2023-01-31'):
        query = """
        SELECT product_id, date, price, sales_volume 
        FROM oss.products_price
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        """
        return self.ch_client.query_dataframe(query)

    # 替换方法
    loader.load_price_data = custom_load_price_data.__get__(loader)

    # 执行方法
    result = loader.load_price_data(start_date='2023-01-01', end_date='2023-01-31')

    # 验证查询是否正确插值
    mock_ch_client.query_dataframe.assert_called_once_with(
        "\n        SELECT product_id, date, price, sales_volume \n        FROM oss.products_price\n        WHERE date BETWEEN '{start_date}' AND '{end_date}'\n        "
    )


def test_empty_result_handling(mock_ch_client):
    """测试空结果处理"""
    # 模拟空数据
    mock_ch_client.query_dataframe.return_value = pd.DataFrame()

    # 创建测试实例
    loader = MagicMock(spec=OSSDataLoader)
    loader.ch_client = mock_ch_client

    # 执行方法
    result = OSSDataLoader.load_price_data(loader)

    # 验证返回空DataFrame
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
