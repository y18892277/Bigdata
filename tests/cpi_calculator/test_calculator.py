# tests/test_calculator.py
import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from calculator import CPICalculator
from logging import LoggerAdapter
from unittest.mock import MagicMock


@pytest.fixture
def sample_price_data():
    """创建示例价格数据"""
    return pd.DataFrame({
        'product_id': [1, 2, 3, 1, 2, 3],
        'date': [
            '2023-01-01', '2023-01-01', '2023-01-01',
            '2023-02-01', '2023-02-01', '2023-02-01'
        ],
        'price': [10.0, 20.0, 30.0, 11.0, 22.0, 30.0]
    })


@pytest.fixture
def sample_category_data():
    """创建示例分类数据"""
    return pd.DataFrame({
        'id': ['food', 'clothing', 'electronics', 'fruits', 'vegetables'],
        'parent': ['', '', '', 'food', 'food'],
        'weight': [0.3, 0.2, 0.5, 0.1, 0.2]
    })


@pytest.fixture
def mock_logger():
    """创建模拟日志记录器"""
    logger = MagicMock(spec=LoggerAdapter)
    return logger


def test_initialization(mock_logger):
    """测试初始化逻辑"""
    calculator = CPICalculator(base_date='2023-01-01', logger=mock_logger)
    assert calculator.base_date == '2023-01-01'
    assert calculator.report_date is None
    assert calculator.logger == mock_logger

    calculator_with_report = CPICalculator(
        base_date='2023-01-01',
        report_date='2023-02-01',
        logger=mock_logger
    )
    assert calculator_with_report.report_date == '2023-02-01'


def test_compute_normal_flow(sample_price_data, sample_category_data):
    """测试完整计算流程"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 执行计算
    result = calculator.compute(sample_price_data, sample_category_data)

    # 验证结果范围合理性
    assert isinstance(result, float)
    assert 100 <= result <= 120  # 根据样本数据，预期涨幅在10%左右


def test_missing_columns_validation():
    """测试数据校验 - 缺少必要字段"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 测试价格数据缺少字段
    with pytest.raises(ValueError) as exc_info:
        calculator._validate_input(
            pd.DataFrame({'product_id': [1]}),
            pd.DataFrame({'id': ['food'], 'parent': [''], 'weight': [0.5]})
        )
    assert "价格数据缺少必要字段" in str(exc_info.value)

    # 测试分类数据缺少字段
    with pytest.raises(ValueError) as exc_info:
        calculator._validate_input(
            pd.DataFrame({'product_id': [1], 'date': ['2023-01-01'], 'price': [10.0]}),
            pd.DataFrame({'id': ['food']})
        )
    assert "分类数据缺少必要字段" in str(exc_info.value)


def test_get_leaf_categories(sample_category_data):
    """测试末级分类识别"""
    calculator = CPICalculator(base_date='2023-01-01')

    leaf_cats = calculator._get_leaf_categories(sample_category_data)

    # 验证末级分类数量
    assert len(leaf_cats) == 3  # electronics, fruits, vegetables

    # 验证返回字段
    assert set(leaf_cats.columns) == {'id', 'weight'}

    # 验证权重准确性
    assert leaf_cats[leaf_cats['id'] == 'electronics']['weight'].values[0] == 0.5


def test_prepare_price_comparison(sample_price_data):
    """测试价格对比数据准备"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 自动确定报告期
    price_compare = calculator._prepare_price_comparison(sample_price_data)
    assert calculator.report_date == '2023-02-01'

    # 验证数据透视效果
    assert len(price_compare) == 3  # 3个商品
    assert set(price_compare.columns) == {'product_id', 'base_price', 'report_price'}

    # 验证价格准确性
    assert price_compare[price_compare['product_id'] == 1]['base_price'].values[0] == 10.0
    assert price_compare[price_compare['product_id'] == 1]['report_price'].values[0] == 11.0


def test_merge_product_info(sample_price_data, sample_category_data):
    """测试商品信息合并"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 准备测试数据
    price_compare = calculator._prepare_price_comparison(sample_price_data)
    merged = calculator._merge_product_info(price_compare, sample_category_data)

    # 验证合并效果
    assert len(merged) == 3  # 3个商品
    assert 'category_id' in merged.columns

    # 验证分类映射（假设商品1和2属于food，3属于electronics）
    assert merged[merged['product_id'] == 1]['category_id'].values[0] == 'food'
    assert merged[merged['product_id'] == 3]['category_id'].values[0] == 'electronics'


def test_calculate_category_index(sample_price_data, sample_category_data):
    """测试分类指数计算"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 准备测试数据
    price_compare = calculator._prepare_price_comparison(sample_price_data)
    merged = calculator._merge_product_info(price_compare, sample_category_data)
    leaf_cats = calculator._get_leaf_categories(sample_category_data)

    # 计算分类指数
    category_index = calculator._calculate_category_index(merged, leaf_cats)

    # 验证结果结构
    assert len(category_index) == 3  # 3个末级分类
    assert set(category_index.columns) == {'category_id', 'price_ratio'}

    # 验证计算准确性（food类包含商品1和2）
    food_index = category_index[category_index['category_id'] == 'food']['price_ratio'].values[0]
    expected_ratio = np.exp(np.log([1.1, 1.1]).mean())  # (10%涨幅的几何平均)
    assert np.isclose(food_index, expected_ratio)


def test_calculate_weighted_cpi(sample_price_data, sample_category_data):
    """测试加权CPI计算"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 准备测试数据
    price_compare = calculator._prepare_price_comparison(sample_price_data)
    merged = calculator._merge_product_info(price_compare, sample_category_data)
    leaf_cats = calculator._get_leaf_categories(sample_category_data)
    category_index = calculator._calculate_category_index(merged, leaf_cats)

    # 计算加权CPI
    final_cpi = calculator._calculate_weighted_cpi(category_index, leaf_cats)

    # 验证结果范围合理性
    assert isinstance(final_cpi, float)
    assert 100 <= final_cpi <= 120  # 根据样本数据，预期涨幅在10%左右


def test_invalid_price_ratios(sample_price_data, sample_category_data):
    """测试无效价格比率处理"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 修改价格数据包含无效值
    invalid_price_df = sample_price_data.copy()
    invalid_price_df.loc[0, 'price'] = 0  # 制造零值
    invalid_price_df.loc[2, 'price'] = -10  # 制造负值

    # 执行计算
    result = calculator.compute(invalid_price_df, sample_category_data)

    # 验证结果合理性（应忽略无效值）
    assert isinstance(result, float)
    assert result > 0  # 确保不会出现零或负值


def test_no_matching_categories(sample_price_data):
    """测试无匹配分类的情况"""
    calculator = CPICalculator(base_date='2023-01-01')

    # 创建无匹配的分类数据
    no_match_category = pd.DataFrame({
        'id': ['electronics'],
        'parent': [''],
        'weight': [1.0]
    })

    # 执行计算（应返回0）
    result = calculator.compute(sample_price_data, no_match_category)
    assert result == 0.0


def test_from_config():
    """测试工厂方法"""
    config = {
        'calculation': {
            'base_date': '2023-01-01',
            'report_date': '2023-02-01'
        }
    }

    calculator = CPICalculator.from_config(config)
    assert calculator.base_date == '2023-01-01'
    assert calculator.report_date == '2023-02-01'
