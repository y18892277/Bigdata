# -*- coding: utf-8 -*-
"""
CPI 计算器主程序 - 实现数据加载、计算、可视化全流程
"""
import logging
from config import settings
from loader import SecureOSSDataLoader
from calculator import CPICalculator
from visualizer import Visualizer

# 初始化日志
LOGGER = logging.getLogger(__name__)

def main():
    try:
        # 1. 初始化配置
        LOGGER.info("CPI 计算器启动，运行模式：%s", settings.ENV_FOR_DYNACONF)

        # 2. 数据加载
        loader = SecureOSSDataLoader(
            oss_conf={
                'endpoint': settings.OSS.ENDPOINT,
                'bucket': settings.OSS.BUCKET,
                'sts_role_arn': settings.OSS.get('STS_ROLE_ARN', '')
            },
            ch_conf={
                'host': settings.DATABASE.HOST,
                'port': settings.DATABASE.PORT,
                'user': settings.DATABASE.USER,
                'password': settings.DATABASE.get('PASSWORD', '')
            }
        )

        # 加载价格数据和分类映射
        start_date = '2023-01-01'
        end_date = '2025-01-31'
        price_data = loader.load_price_data(start_date, end_date)
        category_mapping = loader.load_category_mapping()

        # 3. 核心计算
        calculator = CPICalculator(db_config=settings.DATABASE)
        cpi_result = calculator.compute_cpi(price_data, category_mapping, start_date, end_date)

        # 4. 结果输出
        LOGGER.debug("生成可视化报告...")
        visualizer = Visualizer(engine=settings.OUTPUT.PLOT_ENGINE)
        output_path = settings.OUTPUT.REPORT.format(date=end_date)
        visualizer.plot_cpi_trend(cpi_result, output_path)

        LOGGER.info("处理成功 | 报告路径: %s | 可视化引擎: %s",
                    output_path, settings.OUTPUT.PLOT_ENGINE)

    except Exception as e:
        LOGGER.exception("流程异常终止")
        raise


if __name__ == '__main__':
    main()
