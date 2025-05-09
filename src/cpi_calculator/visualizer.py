import pandas as pd
from matplotlib import pyplot as plt
from alibabacloud_quickbi_public20220101.client import Client as QuickBIClient

class ReportGenerator:
    @staticmethod
    def generate(data: pd.DataFrame, output_path: str, plot_engine: str):
        if plot_engine == 'quickbi':
            ReportGenerator._generate_quickbi_report(data)
        else:
            ReportGenerator._generate_local_report(data, output_path)

    @staticmethod
    def _generate_quickbi_report(data: pd.DataFrame):
        """推送数据到Quick BI"""
        # 实现API调用逻辑
        pass

    @staticmethod
    def _generate_local_report(data: pd.DataFrame, output_path: str):
        """使用matplotlib生成本地报告"""
        plt.figure(figsize=(12, 6))
        data.plot(x='date', y='cpi_index')
        plt.title('CPI趋势分析')
        plt.savefig(output_path)
