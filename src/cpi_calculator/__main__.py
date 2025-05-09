# -*- coding: utf-8 -*-
"""
CPI 计算器主程序 - 实现数据加载、计算、可视化全流程
"""
from config import settings
from loader import OSSDataLoader
from calculator import ChainIndexCalculator, FixedBaseCalculator
from visualizer import ReportGenerator


def _initialize_loader(config: dict) -> OSSDataLoader:
    """初始化数据加载器"""
    return OSSDataLoader(
        endpoint=config['oss']['endpoint'],
        bucket_name=config['oss']['bucket'],
        ch_conn=config['clickhouse']
    )


def _create_calculator(config: dict):
    """创建计算器实例"""
    algorithm_config = config['algorithm']
    if algorithm_config['type'] == 'chain':
        return ChainIndexCalculator()
    else:
        return FixedBaseCalculator(
            base_date=algorithm_config['base_date'],
            weight_scheme=algorithm_config.get('weight_scheme', 'official')
        )


def main():
    try:
        # 1. 初始化配置
        LOGGER.info("CPI 计算器启动，运行模式：%s", settings.ENV_FOR_DYNACONF)

        # 2. 数据加载
        loader = OSSDataLoader(
            endpoint=settings.OSS.ENDPOINT,
            bucket_name=settings.OSS.BUCKET,
            ch_conn={
                'host': settings.DATABASE.HOST,
                'port': settings.DATABASE.PORT,
                'user': settings.DATABASE.USER,
                'password': settings.DATABASE.get('PASSWORD', '')
            }
        )

        # 3. 核心计算
        if settings.ALGORITHM == 'chain':
            calculator = ChainIndexCalculator()
        else:
            calculator = FixedBaseCalculator(base_date='2023-01-01')

        # 4. 结果输出
        LOGGER.debug("生成可视化报告...")
        ReportGenerator.generate(
            result_df,
            output_path=config['output']['report'],
            plot_engine=config['output']['plot_engine'],
            oss_upload_config=config['oss'] if config['output']['upload_oss'] else None
        )

        LOGGER.info("处理成功 | 报告路径: %s | 可视化引擎: %s",
                    config['output']['report'],
                    config['output']['plot_engine'])

    except Exception as e:
        LOGGER.exception("流程异常终止")
        raise


if __name__ == '__main__':
    main()
