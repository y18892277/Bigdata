# CPI计算器项目逻辑梳理

## 整体架构
本项目基于电商平台公开数据构建日频消费者价格指数，采用云服务进行数据管理与计算，实现高效、可复用的指数计算系统。整体架构分为三个核心模块：

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  数据加载     │   │  指数计算   │    │  可视化输出  │
│(OSS+CH引擎)   │─> │    (链式)    │─> │(QuickBI/本地) │
└──────────────┘   └──────────────┘   ────────────── ┘
```


## 模块交互流程
```
1. 配置加载
   └─ dynaconf从settings.yml读取环境配置
2. 数据加载
   └─ OSSDataLoader通过CH引擎加载价格数据和分类映射
3. 指数计算
   └─ ChainIndexCalculator/FixedBaseCalculator执行计算
4. 结果输出
   └─ ReportGenerator生成可视化报告
```


## 核心模块解析

### 1. 配置管理 (config.py)
- 使用Dynaconf实现多环境配置管理
- 支持环境变量覆盖（前缀`CPI_`）
- 配置层级：
  ```yaml
  default: 基础配置
  ├── prod: 生产环境
  └── dev: 开发环境
  ```


### 2. 数据加载 (loader.py)
- **OSSDataLoader** 实现：
  - 通过ClickHouse外部表查询OSS数据
  - 加载价格数据（支持日期范围筛选）
  - 加载分类映射表（CSV格式）

- 存在问题：
  ```python
  # 查询存在SQL注入风险
  query = f"WHERE date BETWEEN '{start_date}' AND '{end_date}'"
  # 建议改为参数化查询
  query = "WHERE date BETWEEN %(start)s AND %(end)s"
  self.ch_client.execute(query, {"start": start_date, "end": end_date})
  ```


### 3. 指数计算 (calculator.py)
- **CPICalculator** 核心流程：
  ```
  compute()
  ├─ _validate_input()       # 数据校验
  ├─ _get_leaf_categories()  # 识别末级分类
  ├─ _prepare_price_comparison()  # 准备价格对比
  ├─ _merge_product_info()   # 合并商品信息
  ├─ _calculate_category_index()  # 分类指数计算
  └─ _calculate_weighted_cpi()    # 加权计算总指数
  ```


- 存在问题：
  ```python
  # 返回值类型不匹配
  def compute(...) -> float:  # 返回单个数值
  # 但主程序期望DataFrame
  result_df = calculator.compute(...)  # 类型不匹配
  ```


### 4. 可视化输出 (visualizer.py)
- **ReportGenerator** 实现：
  - QuickBI模式：待实现API调用逻辑
  - 本地模式：使用matplotlib生成图表

- 存在问题：
  ```python
  # QuickBI方法未实现
  def _generate_quickbi_report(): 
      pass  # 需要补充API调用逻辑
  
  # 本地报告缺少异常处理
  def _generate_local_report():
      plt.savefig(output_path)  # 未处理文件写入失败情况
  ```


## 数据流分析
```
OSS存储
├─ products_price.csv  # 价格数据
└─ meta/category_mapping.csv  # 分类映射

ClickHouse引擎
├─ 外部表指向OSS CSV文件
└─ 提供SQL查询接口

内存数据流
Price DataFrame ─→ Category DataFrame ─→ Result DataFrame ─→ Report
[product_id,date,price,sales_volume]    [id,parent,weight]    [date,cpi_index]
```


## 配置项映射
| 模块         | 配置项                          | 用途说明                   |
|--------------|---------------------------------|--------------------------|
| 数据加载     | OSS.ENDPOINT/BUCKET             | OSS连接信息               |
|              | DATABASE.HOST/PORT              | ClickHouse连接信息         |
| 指数计算     | ALGORITHM                       | 算法类型(chain/fixed)      |
|              | ALGORITHM.base_date             | 定基算法基期               |
| 可视化输出   | OUTPUT.REPORT                   | 报告输出路径               |
|              | OUTPUT.PLOT_ENGINE              | 渲染引擎(quickbi/matplotlib)|

