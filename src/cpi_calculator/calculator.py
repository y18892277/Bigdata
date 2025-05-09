# calculator.py
import numpy as np
import pandas as pd
from typing import Optional
from logging import LoggerAdapter


class CPICalculator:
    """基于 SQL 逻辑重构的 CPI 计算核心类"""

    def __init__(self,
                 base_date: str,
                 report_date: Optional[str] = None,
                 logger: Optional[LoggerAdapter] = None):
        """
        :param base_date: 基期日期 (格式: 'YYYY-MM-DD')
        :param report_date: 报告期日期，默认为最新可用日期
        :param logger: 日志记录器
        """
        self.base_date = base_date
        self.report_date = report_date
        self.logger = logger or logging.getLogger(__name__)

    def compute(self,
                price_df: pd.DataFrame,
                category_df: pd.DataFrame) -> float:
        """
        执行完整 CPI 计算流程
        :param price_df: 价格数据，需包含字段 [product_id, date, price]
        :param category_df: 分类数据，需包含层级关系 [id, parent, weight]
        :return: 计算得到的 CPI 值
        """
        self._validate_input(price_df, category_df)

        # 步骤分解
        leaf_cats = self._get_leaf_categories(category_df)
        price_compare = self._prepare_price_comparison(price_df)
        merged_data = self._merge_product_info(price_compare, category_df)
        category_index = self._calculate_category_index(merged_data, leaf_cats)
        final_cpi = self._calculate_weighted_cpi(category_index, leaf_cats)

        self.logger.info(f"CPI 计算完成: {final_cpi:.4f}")
        return final_cpi

    def _validate_input(self,
                        price_df: pd.DataFrame,
                        category_df: pd.DataFrame) -> None:
        """数据校验"""
        required_price_cols = {'product_id', 'date', 'price'}
        if not required_price_cols.issubset(price_df.columns):
            missing = required_price_cols - set(price_df.columns)
            raise ValueError(f"价格数据缺少必要字段: {missing}")

        required_cat_cols = {'id', 'parent', 'weight'}
        if not required_cat_cols.issubset(category_df.columns):
            missing = required_cat_cols - set(category_df.columns)
            raise ValueError(f"分类数据缺少必要字段: {missing}")

    def _get_leaf_categories(self,
                             category_df: pd.DataFrame) -> pd.DataFrame:
        """识别末级分类（无子类的类别）"""
        has_children = category_df['id'].isin(category_df['parent'])
        leaf_cats = category_df[~has_children].copy()

        self.logger.debug(f"识别到末级分类数量: {len(leaf_cats)}")
        return leaf_cats[['id', 'weight']]

    def _prepare_price_comparison(self,
                                  price_df: pd.DataFrame) -> pd.DataFrame:
        """准备基期与报告期价格对比数据"""
        # 自动确定报告期
        if not self.report_date:
            self.report_date = price_df['date'].max()
            self.logger.info(f"自动设置报告期为: {self.report_date}")

        # 筛选目标日期
        mask = price_df['date'].isin([self.base_date, self.report_date])
        filtered = price_df[mask].copy()

        # 数据透视
        pivot_df = filtered.pivot(
            index='product_id',
            columns='date',
            values='price'
        ).reset_index()

        # 列名标准化
        pivot_df.columns = ['product_id', 'base_price', 'report_price']

        return pivot_df.dropna(subset=['base_price', 'report_price'])

    def _merge_product_info(self,
                            price_compare: pd.DataFrame,
                            category_df: pd.DataFrame) -> pd.DataFrame:
        """合并商品分类信息"""
        # 假设存在 product 表，包含 [product_id, category_id]
        # 此处简化为直接使用传入的分类映射
        merged = price_compare.merge(
            category_df[['id', 'parent']].rename(columns={'id': 'category_id'}),
            left_on='product_id',
            right_on='category_id',
            how='inner'
        )
        return merged.dropna(subset=['category_id'])

    def _calculate_category_index(self,
                                  merged_data: pd.DataFrame,
                                  leaf_cats: pd.DataFrame) -> pd.DataFrame:
        """计算各分类价格指数（几何平均）"""
        # 过滤仅末级分类
        valid_cats = merged_data['category_id'].isin(leaf_cats['id'])
        filtered = merged_data[valid_cats].copy()

        # 计算价格比率
        filtered['price_ratio'] = filtered['report_price'] / filtered['base_price']
        filtered = filtered[filtered['price_ratio'] > 0]

        # 分组计算几何平均
        grouped = filtered.groupby('category_id')['price_ratio']
        category_index = np.exp(np.log(grouped.transform('mean')))

        return category_index.reset_index()

    def _calculate_weighted_cpi(self,
                                category_index: pd.DataFrame,
                                leaf_cats: pd.DataFrame) -> float:
        """计算加权 CPI"""
        merged = category_index.merge(
            leaf_cats,
            left_on='category_id',
            right_on='id',
            how='inner'
        )
        merged['weighted_index'] = merged['price_ratio'] * merged['weight']
        return merged['weighted_index'].sum()

    @classmethod
    def from_config(cls, config: dict):
        """工厂方法 - 从配置创建实例"""
        return cls(
            base_date=config['calculation']['base_date'],
            report_date=config['calculation'].get('report_date'),
            logger=logging.getLogger(cls.__name__)
        )
