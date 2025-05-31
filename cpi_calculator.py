import clickhouse_connect
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.font_manager as fm
import matplotlib

# --- 全局中文字体设置 ---
# 您可以尝试 'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'SimHei', 'Noto Sans CJDK SC' 等
# 请确保字体已经在您的系统中安装
PREFERRED_CHINESE_FONT = 'WenQuanYi Micro Hei' 
try:
    plt.rcParams['font.family'] = PREFERRED_CHINESE_FONT
    # 检查字体是否真的被 matplotlib 找到
    fm.findfont(fm.FontProperties(family=PREFERRED_CHINESE_FONT))
    print(f"已尝试将全局字体设置为: {PREFERRED_CHINESE_FONT}。如果图表仍有问题，请检查字体安装和名称。")
except Exception as e:
    print(f"警告: 设置字体 '{PREFERRED_CHINESE_FONT}' 失败或字体未找到: {e}")
    print("请确保您已在系统中安装了该字体，并且字体名称正确。")
    print("可以尝试在终端使用 `fc-list :lang=zh` 查看已安装的中文字体名称。")
plt.rcParams['axes.unicode_minus'] = False  # 解决中文环境下负号显示问题


# --- 用户配置区 ---
# 请在此处填写您的 ClickHouse 连接信息和表/列名
CLICKHOUSE_HOST = 'cc-bp1a4oj533508zbl9.clickhouse.ads.aliyuncs.com'  # ClickHouse 服务器地址 (阿里云VPC地址)
CLICKHOUSE_PORT = 8123         # ClickHouse HTTP 端口 (阿里云VPC HTTP端口)
CLICKHOUSE_USER = 'test'    # !!! 请替换为您的 ClickHouse 用户名 !!!
CLICKHOUSE_PASSWORD = 'CHYchen1106'       # !!! 请替换为您的 ClickHouse 密码 !!!
CLICKHOUSE_DATABASE = 'clickhouse_demo' # 请确认或替换为您的 ClickHouse 数据库名

# 表名配置
# 请根据您在 ClickHouse中的实际表名进行修改
TABLE_CATEGORIES = 'categories' # 商品分类信息表
TABLE_PRODUCTS = 'products'     # 商品信息表
TABLE_PRICES = 'daily_price'         # 商品每日价格与销量数据表

# 列名配置
# 请根据您的实际列名进行修改 (在对应的表中)
# 分类表 (TABLE_CATEGORIES)
COL_CATEGORY_ID = 'category_id'          # 分类ID列
COL_CATEGORY_NAME = 'category'        # 分类名称列

# 商品表 (TABLE_PRODUCTS)
COL_PRODUCT_ID_IN_PRODUCTS = 'product_id' # 商品ID列
COL_CATEGORY_ID_IN_PRODUCTS = 'category_id' # 商品表中关联分类的ID列
COL_PRODUCT_WEIGHT = 'weight'          # 商品权重列 (在 TABLE_PRODUCTS 中)

# 价格表 (TABLE_PRICES)
COL_PRODUCT_ID_IN_PRICES = 'product_id' # 价格表中的商品ID列
COL_EVENT_DATE = 'change_date'  # 日期列 (应为 Date 或 DateTime 类型)
COL_PRICE = 'price'            # 价格列 (应为数值类型)
COL_SALES_VOLUME = 'sales_volume' # 销量列 (应为数值类型) # !!! 注意：'daily_price' 表中当前没有此列, 此计算不再使用此列 !!!
# --- 用户配置区结束 ---

def get_clickhouse_client():
    """创建并返回一个 ClickHouse 客户端连接。"""
    try:
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            user=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DATABASE,
            secure=False, # 因为我们尝试HTTP端口8123，所以这里是False
            # verify=False # 如果使用自签名证书且需要跳过验证（不推荐生产环境），取消注释
        )
        client.ping() # 测试连接
        print(f"成功连接到 ClickHouse 服务器: {CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}，数据库: {CLICKHOUSE_DATABASE}")
        return client
    except Exception as e:
        print(f"连接 ClickHouse 失败: {e}")
        print("请检查脚本中的 CLICKHOUSE_* 配置变量是否正确。")
        return None

def calculate_product_weighted_price_per_category(client):
    """
    从 ClickHouse 查询数据，计算每日每类商品的商品权重加权平均价格。
    返回包含结果的列表，每个元素是一个字典。
    """
    if not client:
        return []

    query = f"""
    SELECT
        c.{COL_CATEGORY_NAME} AS category_name,
        toDate(p.{COL_EVENT_DATE}) AS day, -- 确保按天聚合
        sum(p.{COL_PRICE} * pr.{COL_PRODUCT_WEIGHT}) / sum(pr.{COL_PRODUCT_WEIGHT}) AS product_weighted_average_price,
        sum(pr.{COL_PRODUCT_WEIGHT}) as total_product_weight,
        countDistinct(p.{COL_PRODUCT_ID_IN_PRICES}) as distinct_products_sold
    FROM
        {TABLE_PRICES} AS p
    JOIN
        {TABLE_PRODUCTS} AS pr ON p.{COL_PRODUCT_ID_IN_PRICES} = pr.{COL_PRODUCT_ID_IN_PRODUCTS}
    JOIN
        {TABLE_CATEGORIES} AS c ON pr.{COL_CATEGORY_ID_IN_PRODUCTS} = c.{COL_CATEGORY_ID}
    WHERE
        pr.{COL_PRODUCT_WEIGHT} > 0 AND p.{COL_PRICE} IS NOT NULL
    GROUP BY
        c.{COL_CATEGORY_NAME}, day
    ORDER BY
        day ASC, c.{COL_CATEGORY_NAME} ASC
    """

    print("\n将执行以下查询:")
    print("----------------------------------------------------")
    print(query)
    print("----------------------------------------------------\n")

    try:
        result = client.query(query)
        print("查询成功执行！")
        if result.result_rows:
            # 将元组结果转换为字典列表，方便使用
            column_names = result.column_names
            data = [dict(zip(column_names, row)) for row in result.result_rows]
            return data
        else:
            print("查询没有返回任何数据。请检查您的数据表是否为空或查询条件是否正确。")
            return []
    except Exception as e:
        print(f"执行查询时出错: {e}")
        print("请检查您的表名、列名配置以及数据是否存在问题。")
        return []

def calculate_daily_overall_price_index(client):
    """
    从 ClickHouse 查询数据，计算每日的总体商品权重加权平均价格指数。
    返回包含结果的列表，每个元素是一个字典。
    """
    if not client:
        return []

    query = f"""
    SELECT
        toDate(p.{COL_EVENT_DATE}) AS day,
        sum(p.{COL_PRICE} * pr.{COL_PRODUCT_WEIGHT}) / sum(pr.{COL_PRODUCT_WEIGHT}) AS daily_overall_price_index,
        sum(pr.{COL_PRODUCT_WEIGHT}) as total_weight_for_day,
        countDistinct(p.{COL_PRODUCT_ID_IN_PRICES}) as distinct_products_for_day
    FROM
        {TABLE_PRICES} AS p
    JOIN
        {TABLE_PRODUCTS} AS pr ON p.{COL_PRODUCT_ID_IN_PRICES} = pr.{COL_PRODUCT_ID_IN_PRODUCTS}
    WHERE
        pr.{COL_PRODUCT_WEIGHT} > 0 AND p.{COL_PRICE} IS NOT NULL
    GROUP BY
        day
    ORDER BY
        day ASC
    """

    print("\n将执行以下查询计算每日总体价格指数:")
    print("----------------------------------------------------")
    print(query)
    print("----------------------------------------------------\n")

    try:
        result = client.query(query)
        print("每日总体价格指数查询成功执行！")
        if result.result_rows:
            column_names = result.column_names
            data = [dict(zip(column_names, row)) for row in result.result_rows]
            return data
        else:
            print("每日总体价格指数查询没有返回任何数据。")
            return []
    except Exception as e:
        print(f"执行每日总体价格指数查询时出错: {e}")
        return []

def plot_daily_index_trend(index_data, output_filename="daily_price_index_trend.png"):
    """
    根据每日价格指数数据绘制趋势图并保存。
    :param index_data: 包含每日指数数据的列表，每个元素是字典，需包含 'day' 和 'daily_overall_price_index'。
    :param output_filename: 输出图像文件名。
    """
    if not index_data:
        print("没有数据可供绘图。")
        return

    # 全局字体设置已移至脚本顶部，此处不再需要单独设置
    # font_names = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'sans-serif']
    # plt.rcParams['font.sans-serif'] = font_names
    # plt.rcParams['axes.unicode_minus'] = False

    # 提取日期和指数值
    # ClickHouse 的 Date 类型返回的是 datetime.date 对象，可以直接用于绘图
    days = [item['day'] for item in index_data]
    index_values = [item['daily_overall_price_index'] for item in index_data]

    # 绘图
    plt.figure(figsize=(12, 6))
    plt.plot(days, index_values, marker='o', linestyle='-')

    # 设置图表标题和标签
    plt.title('每日总体价格指数趋势', fontsize=16)
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('价格指数', fontsize=12)

    # 格式化X轴日期显示
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(days) // 10))) # 每隔几天显示一个刻度
    plt.gcf().autofmt_xdate() # 自动旋转日期标签以防重叠

    plt.grid(True)
    plt.tight_layout() # 调整布局以适应所有元素

    try:
        plt.savefig(output_filename)
        print(f"\n趋势图已保存到: {output_filename}")
    except Exception as e:
        print(f"保存趋势图时出错: {e}")

if __name__ == "__main__":
    print("--- 开始 CPI 相关指数计算 ---")
    
    # 检查配置 (保持不变)
    if CLICKHOUSE_HOST == 'localhost' and CLICKHOUSE_USER == 'default' and CLICKHOUSE_DATABASE == 'default':
        print("\n警告: 您似乎正在使用默认的 ClickHouse 连接配置。请更新脚本中的配置。")
        # exit(1) # 实际使用时建议退出

    client = get_clickhouse_client()

    if client:
        # 1. 计算并打印每日每类商品权重加权平均价格 (原有功能)
        print("\n--- 1. 计算每日每类商品权重加权平均价格 ---")
        category_results = calculate_product_weighted_price_per_category(client)
        if category_results:
            print(f"\n成功获取 {len(category_results)} 条每日每类商品权重加权平均价格数据:")
            print("====================================================")
            for row in category_results[:5]: # 打印前5条作为示例
                print(f"日期: {row['day']}, 分类: {row['category_name']}, "
                      f"商品权重平均价: {row['product_weighted_average_price']:.2f}, "
                      f"总权重: {row['total_product_weight']:.2f}, "
                      f"商品数: {row['distinct_products_sold']}")
            if len(category_results) > 5:
                print(f"... 等等 (总共 {len(category_results)} 条记录)")
            print("====================================================")
        else:
            print("\n未能计算出每日每类商品的任何结果。")

        # 2. 计算每日总体价格指数
        print("\n--- 2. 计算每日总体价格指数 ---")
        daily_index_data = calculate_daily_overall_price_index(client)

        if daily_index_data:
            print(f"\n成功获取 {len(daily_index_data)} 条每日总体价格指数数据:")
            print("====================================================")
            for row in daily_index_data[:5]: # 打印前5条作为示例
                print(f"日期: {row['day']}, "
                      f"总体价格指数: {row['daily_overall_price_index']:.2f}, "
                      f"当日总权重: {row['total_weight_for_day']:.2f}, "
                      f"当日商品数: {row['distinct_products_for_day']}")
            if len(daily_index_data) > 5:
                print(f"... 等等 (总共 {len(daily_index_data)} 条记录)")
            print("====================================================")
            
            # 3. 绘制每日总体价格指数趋势图
            print("\n--- 3. 绘制每日总体价格指数趋势图 ---")
            plot_daily_index_trend(daily_index_data)
        else:
            print("\n未能计算出每日总体价格指数。")
            
        client.close()
        print("\n与 ClickHouse 的连接已关闭。")

    print("\n--- 脚本执行结束 ---") 

    # 清除 Matplotlib 字体缓存
    print(matplotlib.get_cachedir()) 