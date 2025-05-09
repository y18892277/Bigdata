from sqlalchemy import Column, Integer, String, Decimal, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True, nullable=False, comment='分类ID（国家标准分类编码）')
    name = Column(String(50), nullable=False, comment='分类名称')
    weight = Column(Decimal(8,4), comment='CPI计算权重')
    hierarchy = Column(Integer, nullable=False, comment='分类层级（1=一级分类，2=二级分类，3=三级分类）')
    parent_id = Column(Integer, ForeignKey('category.id', ondelete='SET NULL'), comment='父分类ID')

    # 自引用关系
    parent = relationship('Category', remote_side=[id], back_populates='children')
    children = relationship('Category', back_populates='parent')

class Price(Base):
    __tablename__ = 'price'
    __table_args__ = (
        CheckConstraint('price >= 0', name='price_non_negative'),
    )

    date = Column(Date, primary_key=True, nullable=False, comment='价格日期')
    product_id = Column(Integer, primary_key=True, nullable=False, comment='商品ID')
    category_id = Column(Integer, ForeignKey('category.id', ondelete='CASCADE'), nullable=False, comment='分类ID')
    name = Column(String(50), comment='商品名称')
    price = Column(Decimal(12,2), comment='商品价格（元）')

    # 关系定义
    category = relationship('Category', back_populates='prices')

# 添加反向关系
Category.prices = relationship('Price', back_populates='category')