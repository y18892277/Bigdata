import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
from pathlib import Path
import logging


class Visualizer:
    """轻量级可视化生成器"""

    def __init__(self, engine='matplotlib'):
        """
        :param engine: 绘图引擎 (matplotlib/plotly)
        """
        self.engine = engine.lower()
        self.logger = logging.getLogger(__name__)

    def plot_cpi_trend(self, cpi_df: pd.DataFrame, output_path: str) -> None:
        """
        生成CPI趋势图
        :param cpi_df: 必须包含字段 [date, cpi_index]
        :param output_path: 支持格式 .html/.png
        """
        self._validate_data(cpi_df, ['date', 'cpi_index'])

        if self.engine == 'plotly':
            self._plotly_trend(cpi_df, output_path)
        else:
            self._matplotlib_trend(cpi_df, output_path)

        self.logger.info(f"图表已保存至: {output_path}")


