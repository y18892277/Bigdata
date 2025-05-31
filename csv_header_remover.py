import os
import shutil
import chardet
import tempfile

# --- 用户配置区 ---
# 请指定包含CSV文件的目标目录路径
# 例如: TARGET_DIRECTORY = r"D:\\我的文档\\CSV数据" (Windows)
#       TARGET_DIRECTORY = "/home/user/csv_files" (Linux/macOS)
TARGET_DIRECTORY = r"D:/学习资料/大三下/大数据应用实践/data/extra"

# 是否在修改原始文件前创建备份 (强烈建议保持为 True)
# 备份文件将以 .bak 后缀保存在原文件同目录下 (例如: data.csv -> data.csv.bak)
CREATE_BACKUP_FILES = True

# 用于编码检测的样本字节数
ENCODING_SAMPLE_SIZE = 10240  # 10KB

# 备选尝试的编码列表 (当chardet检测不明确或失败时)
FALLBACK_ENCODINGS = [
    'utf-8',        # 最常用
    'gb18030',      # 最全的中文编码
    'gbk',          # 常用中文编码
    'gb2312',       # 简体中文
    'utf-8-sig',    # UTF-8 with BOM
    'latin1',       # ISO 8859-1
    'windows-1252'  # Western European
]
# --- 用户配置区结束 ---

def robust_detect_encoding(file_path, sample_size=ENCODING_SAMPLE_SIZE):
    """尝试更可靠地检测文件编码。
    首先使用chardet，然后尝试备选列表。
    返回: (检测到的编码名称 (str) 或 None, 是否应使用errors='replace'读取 (bool))。
    """
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)
            if not sample:
                print(f"  文件 '{file_path}' 为空，无法检测编码。")
                return None, False

        # 1. 尝试 chardet
        chardet_result = chardet.detect(sample)
        detected_encoding = chardet_result['encoding']
        confidence = chardet_result['confidence']
        
        if detected_encoding and confidence > 0.7: # 如果chardet有较高置信度的结果
            # 尝试用此编码读取一小部分以验证
            try:
                sample.decode(detected_encoding, errors='strict')
                print(f"  Chardet检测到编码: {detected_encoding} (置信度: {confidence:.2f}), 严格模式验证通过。")
                return detected_encoding, False # 使用严格模式
            except UnicodeDecodeError:
                print(f"  Chardet检测到编码: {detected_encoding}, 但用严格模式验证失败。将尝试备选列表。")
        elif detected_encoding:
            print(f"  Chardet检测到编码: {detected_encoding} (置信度: {confidence:.2f}较低). 将尝试备选列表。")
        else:
            print(f"  Chardet未能明确检测到编码。将尝试备选列表。")

        # 2. 尝试备选编码列表 (FALLBACK_ENCODINGS)
        for enc_attempt in FALLBACK_ENCODINGS:
            try:
                sample.decode(enc_attempt, errors='strict')
                print(f"  通过备选列表成功匹配编码 (严格模式): {enc_attempt}")
                return enc_attempt, False # 使用严格模式
            except UnicodeDecodeError:
                continue # 尝试下一个
        
        # 3. 如果严格模式都失败，最后使用chardet的原始检测（如果有），并建议配合replace
        if detected_encoding:
             print(f"  所有严格模式解码失败。建议使用 chardet 的初始检测 '{detected_encoding}' 配合 'errors=replace' 进行读取。")
             return detected_encoding, True # 建议使用 'replace'

        print(f"  警告: 文件 '{file_path}' 未能通过任何已知方式确定编码。")
        return None, False

    except FileNotFoundError:
        # 此处不应发生，因为主程序会检查文件存在性
        return None, False
    except Exception as e:
        print(f"  检测编码时发生意外错误: {e}")
        return None, False

def remove_first_line_from_csv(csv_file_path, create_backup=CREATE_BACKUP_FILES):
    """从指定的CSV文件中删除第一行，保留原编码。
    返回: (bool, str) -> (是否成功, 消息/备份路径)
    """
    if not os.path.exists(csv_file_path):
        return False, "文件未找到。"
    if os.path.getsize(csv_file_path) == 0:
        print(f"文件 '{csv_file_path}' 为空，无需处理。")
        return True, "文件为空，无需处理。"

    print(f"开始处理文件: {csv_file_path}")
    detected_encoding, use_replace_for_read = robust_detect_encoding(csv_file_path)
    
    read_encoding_options = {}
    write_encoding_options = {}

    if detected_encoding:
        read_errors = 'replace' if use_replace_for_read else 'strict'
        read_encoding_options = {'encoding': detected_encoding, 'errors': read_errors}
        # 写入时必须严格，并使用基础编码
        write_encoding_options = {'encoding': detected_encoding, 'errors': 'strict'}
        
        print(f"  将使用编码 '{detected_encoding}' (读取选项: {read_errors}) 和 '{detected_encoding}' (写入选项: strict) 进行操作。")
        if use_replace_for_read:
            print(f"  警告: 读取时将使用 'errors=replace'，因为严格模式解码失败。这可能导致无法解码的字符被替换。")
    else:
        print(f"警告: 未能可靠检测文件 '{csv_file_path}' 的编码。跳过此文件以防损坏。")
        return False, f"未能可靠检测编码，跳过。"

    backup_file_path = ""
    if create_backup:
        counter = 0
        backup_base = csv_file_path + ".bak"
        backup_file_path = backup_base
        while os.path.exists(backup_file_path):
            counter += 1
            backup_file_path = f"{backup_base}.{counter}"
        try:
            shutil.copy2(csv_file_path, backup_file_path)
            print(f"  已创建备份: '{backup_file_path}'")
        except Exception as e:
            print(f"  创建备份失败: {e}。将不继续处理此文件。")
            return False, f"备份失败: {e}"

    temp_fd, temp_path = -1, None
    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix=".tmp", text=False) # text=False for binary mode initially
        
        lines_written = 0
        # newline='' is important for csv/text processing to handle line endings correctly
        with open(csv_file_path, 'r', newline='', **read_encoding_options) as infile, \
             os.fdopen(temp_fd, 'w', newline='', **write_encoding_options) as outfile:
            
            first_line_skipped = False
            for line_number, line in enumerate(infile):
                if not first_line_skipped:
                    first_line_skipped = True
                    print(f"  已跳过第一行。")
                    continue
                outfile.write(line)
                lines_written += 1
        
        if not first_line_skipped and lines_written == 0:
             print(f"  文件 '{csv_file_path}' 似乎只有一行或没有内容可写到临时文件。")

        shutil.move(temp_path, csv_file_path)
        temp_path = None # So finally block doesn't try to remove it again
        print(f"  成功删除第一行并覆盖原文件: '{csv_file_path}'")
        return True, backup_file_path if backup_file_path else "成功，未创建备份。"

    except UnicodeDecodeError as ude:
        print(f"  错误: 文件 '{csv_file_path}' 使用编码 '{read_encoding_options.get('encoding')}' 解码失败: {ude}。")
        print(f"  文件可能未被修改。如果已创建备份，请检查备份文件。")
        # Clean up temp file if open
        if temp_path and os.path.exists(temp_path): shutil.move(temp_path, csv_file_path + ".failed_tmp")
        print(f"  问题临时文件（如果生成）已保存为: {csv_file_path}.failed_tmp")
        return False, f"解码错误: {ude}"
    except Exception as e:
        print(f"  处理文件 '{csv_file_path}' 时发生错误: {e}")
        return False, f"处理错误: {e}"
    finally:
        # The primary goal of this finally block is to remove the temporary file
        # if it was created and not successfully moved to its final destination.
        # temp_path is set to None after a successful shutil.move or if mkstemp failed.
        if temp_path and os.path.exists(temp_path): # Check temp_path is not None first
            try:
                os.remove(temp_path)
                print(f"  已清理临时文件: {temp_path}")
            except OSError as ose:
                print(f"  清理临时文件 '{temp_path}' 失败: {ose}")

if __name__ == "__main__":
    if TARGET_DIRECTORY == r"请在这里填入你的CSV文件所在目录的完整路径":
        print("错误: 请先在脚本中设置 'TARGET_DIRECTORY' 的正确路径。")
        exit(1)

    if not os.path.isdir(TARGET_DIRECTORY):
        print(f"错误: 指定的目录 '{TARGET_DIRECTORY}' 不存在或不是一个目录。")
        exit(1)

    print(f"--- 开始处理目录: {TARGET_DIRECTORY} ---")
    if CREATE_BACKUP_FILES:
        print("将为每个修改的文件创建备份 (后缀 .bak)。")
    else:
        print("警告: 未启用备份功能。将直接修改原始文件！")

    processed_files_count = 0
    successful_modifications_count = 0
    failed_modifications_list = []

    for filename in os.listdir(TARGET_DIRECTORY):
        if filename.lower().endswith('.csv'):
            file_path = os.path.join(TARGET_DIRECTORY, filename)
            if os.path.isfile(file_path):
                processed_files_count += 1
                success, message = remove_first_line_from_csv(file_path, CREATE_BACKUP_FILES)
                if success:
                    successful_modifications_count += 1
                else:
                    failed_modifications_list.append((filename, message))
                print("-" * 30) 
    
    print("\n--- 处理完毕 ---")
    print(f"总共扫描到CSV文件数: {processed_files_count}")
    print(f"成功删除第一行的文件数: {successful_modifications_count}")
    if failed_modifications_list:
        print(f"处理失败或跳过的文件数: {len(failed_modifications_list)}")
        for fname, reason in failed_modifications_list:
            print(f"  - 文件: {fname}, 原因: {reason}")
    else:
        if processed_files_count > 0 and successful_modifications_count == processed_files_count:
            print("所有扫描到的CSV文件均已成功处理。")
        elif processed_files_count == 0:
            print("在指定目录中未找到CSV文件。")

    print("脚本执行结束。") 