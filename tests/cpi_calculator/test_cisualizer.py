# tests/test_visualizer.py
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call
from pathlib import Path

# 需要导入被测试模块
from cpi_calculator.visualizer import ReportGenerator


@pytest.fixture
def sample_data():
    """创建示例CPI数据"""
    return pd.DataFrame({
        'date': ['2023-01-01', '2023-02-01', '2023-03-01'],
        'cpi_index': [100.0, 101.5, 102.3]
    })


@pytest.fixture
def mock_quickbi_client():
    """创建模拟的QuickBI客户端"""
    with patch('alibabacloud_quickbi_public20220101.client.Client') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_plt():
    """创建模拟的matplotlib.pyplot模块"""
    with patch('matplotlib.pyplot') as mock_plt:
        mock_plt.figure = MagicMock()
        mock_plt.plot = MagicMock()
        mock_plt.title = MagicMock()
        mock_plt.savefig = MagicMock()
        mock_plt.close = MagicMock()
        yield mock_plt


def test_generate_with_quickbi_engine(sample_data):
    """测试QuickBI引擎选择"""
    mock_generate_quickbi = MagicMock()
    mock_generate_local = MagicMock()

    # 替换私有方法
    ReportGenerator._generate_quickbi_report = mock_generate_quickbi
    ReportGenerator._generate_local_report = mock_generate_local

    # 测试QuickBI引擎
    ReportGenerator.generate(sample_data, "output.html", "quickbi")

    # 验证调用
    mock_generate_quickbi.assert_called_once_with(sample_data)
    mock_generate_local.assert_not_called()


def test_generate_with_matplotlib_engine(sample_data):
    """测试Matplotlib引擎选择"""
    mock_generate_quickbi = MagicMock()
    mock_generate_local = MagicMock()

    # 替换私有方法
    ReportGenerator._generate_quickbi_report = mock_generate_quickbi
    ReportGenerator._generate_local_report = mock_generate_local

    # 测试Matplotlib引擎
    ReportGenerator.generate(sample_data, "output.html", "matplotlib")

    # 验证调用
    mock_generate_local.assert_called_once_with(sample_data, "output.html")
    mock_generate_quickbi.assert_not_called()


def test_invalid_engine_selection(sample_data):
    """测试无效引擎选择"""
    with pytest.raises(ValueError) as exc_info:
        ReportGenerator.generate(sample_data, "output.html", "invalid_engine")

    assert "不支持的绘图引擎" in str(exc_info.value)


def test_generate_quickbi_report_success(sample_data, mock_quickbi_client):
    """测试QuickBI报告生成成功"""
    # 设置API返回值
    mock_quickbi_client.put_data.return_value = MagicMock(status_code=200)

    # 执行方法
    ReportGenerator._generate_quickbi_report(sample_data)

    # 验证API调用
    mock_quickbi_client.put_data.assert_called_once()
    # 可以添加更多验证，如数据格式验证


def test_generate_quickbi_report_api_error(sample_data, mock_quickbi_client):
    """测试QuickBI API错误处理"""
    # 模拟API失败
    mock_quickbi_client.put_data.side_effect = Exception("API Error")

    # 验证异常处理
    with pytest.raises(Exception) as exc_info:
        ReportGenerator._generate_quickbi_report(sample_data)

    assert "QuickBI报告生成失败" in str(exc_info.value)


def test_generate_local_report_success(sample_data, mock_plt):
    """测试本地报告生成成功"""
    output_path = "test_report.png"

    # 执行方法
    ReportGenerator._generate_local_report(sample_data, output_path)

    # 验证matplotlib调用
    mock_plt.figure.assert_called_once_with(figsize=(12, 6))
    mock_plt.plot.assert_called_once()
    mock_plt.title.assert_called_once_with('CPI趋势分析')
    mock_plt.savefig.assert_called_once_with(output_path)
    mock_plt.close.assert_called_once_with("all")


def test_generate_local_report_file_writing(tmpdir, sample_data):
    """测试本地报告文件写入"""
    output_path = tmpdir.join("test_report.png")

    # 执行方法
    ReportGenerator._generate_local_report(sample_data, str(output_path))

    # 验证文件存在
    assert output_path.exists()

    # 验证文件大小（非零）
    assert output_path.size() > 0


def test_generate_local_report_invalid_path(sample_data):
    """测试无效输出路径处理"""
    # 尝试写入受限制的路径
    with pytest.raises(Exception) as exc_info:
        ReportGenerator._generate_local_report(sample_data, "/restricted/path/report.png")

    assert "报告保存失败" in str(exc_info.value)


def test_empty_data_handling():
    """测试空数据处理"""
    empty_data = pd.DataFrame()

    # 测试QuickBI
    with pytest.raises(Exception) as exc_info:
        ReportGenerator._generate_quickbi_report(empty_data)
    assert "数据为空" in str(exc_info.value)

    # 测试本地报告
    with pytest.raises(Exception) as exc_info:
        ReportGenerator._generate_local_report(empty_data, "output.html")
    assert "数据为空" in str(exc_info.value)


def test_invalid_data_format():
    """测试无效数据格式处理"""
    invalid_data = pd.DataFrame({
        'date': ['2023-01-01', '2023-02-01'],
        'invalid_column': ['a', 'b']  # 缺少必要字段
    })

    # 测试QuickBI
    with pytest.raises(Exception) as exc_info:
        ReportGenerator._generate_quickbi_report(invalid_data)
    assert "数据格式不正确" in str(exc_info.value)

    # 测试本地报告
    with pytest.raises(Exception) as exc_info:
        ReportGenerator._generate_local_report(invalid_data, "output.html")
    assert "数据格式不正确" in str(exc_info.value)
