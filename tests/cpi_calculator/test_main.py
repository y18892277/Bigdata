# tests/test_main.py
import pytest
import pandas as pd
from unittest.mock import MagicMock, call


@pytest.fixture
def mock_config():
    return {
        'mode': 'test',
        'oss': {'endpoint': 'oss-test', 'bucket': 'test-bucket'},
        'clickhouse': {'host': 'localhost', 'port': 9000},
        'algorithm': {
            'type': 'chain',
            'base_date': '2023-01-01',
            'weight_scheme': 'official'
        },
        'output': {
            'report': './report.html',
            'plot_engine': 'matplotlib',
            'upload_oss': True
        }
    }


@pytest.fixture
def mock_data():
    return {
        'price_df': pd.DataFrame({'product_id': [1], 'price': [10.0], 'date': ['2023-01-01']}),
        'category_df': pd.DataFrame({'product_id': [1], 'category': ['food'], 'weight': [0.5]}),
        'result_df': pd.DataFrame({'date': ['2023-01-01'], 'cpi_index': [100.0]})
    }


def test_main_success_flow(mocker, mock_config, mock_data):
    """测试主流程正确执行序列"""
    # Mock 依赖链
    mock_load = mocker.patch('cpi_calculator.__main__.load_config', return_value=mock_config)
    mock_loader = mocker.patch('cpi_calculator.__main__.OSSDataLoader', autospec=True)()

    # 配置数据加载器返回值
    mock_loader.load_price_data.return_value = mock_data['price_df']
    mock_loader.load_category_mapping.return_value = mock_data['category_df']

    # 配置计算器
    mock_calculator = mocker.patch('cpi_calculator.__main__.ChainIndexCalculator', autospec=True)()
    mock_calculator.compute.return_value = mock_data['result_df']

    # 配置报告生成
    mock_report = mocker.patch('cpi_calculator.__main__.ReportGenerator.generate')

    # 执行测试
    from cpi_calculator.__main__ import main
    main()

    # 验证调用链
    mock_load.assert_called_once_with('config.yaml')

    # 验证OSSDataLoader初始化
    assert mock_loader.call_args.kwargs == {
        'endpoint': 'oss-test',
        'bucket_name': 'test-bucket',
        'ch_conn': {'host': 'localhost', 'port': 9000}
    }

    # 验证计算器创建
    if mock_config['algorithm']['type'] == 'chain':
        mock_calculator.assert_called_once_with()
    else:
        mock_calculator.assert_called_once_with(
            base_date='2023-01-01',
            weight_scheme='official'
        )

    # 验证计算调用
    mock_calculator.compute.assert_called_once_with(
        price_data=mock_data['price_df'],
        category_map=mock_data['category_df'],
        price_change_formula=mock_config['algorithm'].get('formula', 'geometric_mean')
    )

    # 验证报告生成
    mock_report.assert_called_once_with(
        mock_data['result_df'],
        output_path='./report.html',
        plot_engine='matplotlib',
        oss_upload_config=mock_config['oss']
    )


def test_main_exception_handling(mocker, mock_config):
    """测试异常处理与日志记录"""
    mocker.patch('cpi_calculator.__main__.load_config', side_effect=FileNotFoundError)
    mock_logger = mocker.patch('cpi_calculator.__main__.LOGGER')

    from cpi_calculator.__main__ import main
    with pytest.raises(FileNotFoundError):
        main()

    mock_logger.exception.assert_called_once_with("主流程异常终止")


@pytest.mark.parametrize("algorithm_type, expected_class", [
    ('chain', 'ChainIndexCalculator'),
    ('fixed', 'FixedBaseCalculator')
])
def test_algorithm_selection(mocker, mock_config, algorithm_type, expected_class):
    """参数化测试算法选择逻辑"""
    # 更新配置中的算法类型
    mock_config['algorithm']['type'] = algorithm_type

    # Mock 配置加载
    mocker.patch('cpi_calculator.__main__.load_config', return_value=mock_config)

    # Mock 对应的计算器类
    mock_calc = mocker.patch(f'cpi_calculator.__main__.{expected_class}')

    # 执行测试
    from cpi_calculator.__main__ import main
    main()

    # 验证调用
    if algorithm_type == 'fixed':
        mock_calc.assert_called_once_with(
            base_date='2023-01-01',
            weight_scheme='official'
        )
    else:
        mock_calc.assert_called_once_with()
