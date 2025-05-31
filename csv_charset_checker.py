import chardet
import argparse # 保留导入，以防将来恢复命令行功能，但实际逻辑会先注释掉
import os # 导入os模块用于处理文件路径和文件名
import shutil # 导入shutil模块用于文件操作，例如备份

def detect_csv_encoding(file_path, sample_size=10240):
    """
    检测 CSV 文件的字符集编码。

    参数:
    file_path (str): CSV 文件的路径。
    sample_size (int): 用于检测编码的样本字节数，默认为 10240 (10KB)。
                       对于大多数文件来说，较小的样本通常足够。

    返回:
    tuple: (检测到的字符集编码名称, 置信度)，如果无法检测则返回 (None, 0.0)。
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            if encoding:
                print(f"文件: {file_path}")
                print(f"检测到的字符集: {encoding} (置信度: {confidence:.2f})")
                if confidence < 0.7 and confidence != 0.0: # 0.0 often means binary or no clear pattern
                    print("提醒: 字符集检测置信度较低，后续的转换可能不准确或失败。")
                return encoding, confidence
            else:
                print(f"文件: {file_path}")
                print("无法检测到明确的字符集。")
                return None, 0.0
    except FileNotFoundError:
        print(f"错误: 文件 '{file_path}' 未找到。")
        return None, 0.0
    except Exception as e:
        print(f"检测字符集 '{file_path}' 时发生错误: {e}")
        return None, 0.0

def convert_file_to_utf8_inplace(original_file_path, chardet_detected_encoding, create_backup=True):
    """
    将指定文件从原始编码转换为 UTF-8 编码，并直接修改原始文件。
    会尝试使用一个优先的编码列表（特别是针对中文）进行解码。
    强烈建议启用备份功能。

    参数:
    original_file_path (str): 原始文件的路径。
    chardet_detected_encoding (str): chardet检测到的原始文件的字符集编码。
    create_backup (bool): 是否在修改前创建原始文件的备份。默认为 True。

    返回:
    bool: 如果转换成功则返回 True，否则返回 False。
    """
    if not chardet_detected_encoding:
        print(f"文件 '{original_file_path}': 未提供原始编码（chardet未能检测），无法转换。")
        return False

    # 标准化chardet的检测结果，并检查是否已经是UTF-8
    normalized_chardet_encoding = chardet_detected_encoding.lower().replace('-', '')
    if normalized_chardet_encoding == 'utf8':
        print(f"文件 '{original_file_path}' 已经是 UTF-8 编码，无需转换。")
        return True

    # 构建尝试的编码列表 (针对"ANSI"中文，优先GB18030, GBK)
    encodings_to_try = []
    preferred_chinese_encodings = ['gb18030', 'gbk']
    encodings_to_try.extend(preferred_chinese_encodings)

    if chardet_detected_encoding:
        # 检查 chardet 的检测结果是否已在优先列表中 (忽略大小写和连字符比较)
        is_chardet_already_preferred = False
        norm_chardet_enc = chardet_detected_encoding.lower().replace('-', '')
        for pref_enc in preferred_chinese_encodings:
            if norm_chardet_enc == pref_enc.lower().replace('-', ''):
                is_chardet_already_preferred = True
                break
        if not is_chardet_already_preferred:
            encodings_to_try.append(chardet_detected_encoding)
    
    # 添加 GB2312 作为备选，如果它与 chardet 的不同且不在优先列表
    gb2312_variants = ['gb2312', 'GB2312']
    add_gb2312 = True
    current_encs_normalized = [e.lower().replace('-', '') for e in encodings_to_try]
    for variant in gb2312_variants:
        if variant.lower().replace('-', '') in current_encs_normalized:
            add_gb2312 = False
            break
    if add_gb2312:
        encodings_to_try.append('GB2312') # 使用一个固定的大小写形式

    # 去重，并保留顺序
    unique_encodings_to_try = list(dict.fromkeys(encodings_to_try))

    content = None
    successfully_read_encoding = None

    print(f"文件 '{original_file_path}': chardet初步检测为 '{chardet_detected_encoding}'. 实际尝试解码顺序: {unique_encodings_to_try}")

    for enc_try_count, encoding_attempt in enumerate(unique_encodings_to_try):
        try:
            print(f"  尝试使用编码 '{encoding_attempt}' (strict模式) 读取...")
            with open(original_file_path, 'r', encoding=encoding_attempt, errors='strict') as f_original:
                content = f_original.read()
            successfully_read_encoding = encoding_attempt
            print(f"  成功使用编码 '{successfully_read_encoding}' 读取文件内容。")
            break # 成功读取，跳出循环
        except UnicodeDecodeError:
            print(f"  使用编码 '{encoding_attempt}' 解码失败 (UnicodeDecodeError)。")
            if enc_try_count == len(unique_encodings_to_try) - 1: # 如果是最后一次 strict 尝试失败
                print(f"警告: 所有优先编码 ({unique_encodings_to_try}) 均无法以strict模式完全解码文件 '{original_file_path}'.")
                # 最后手段：使用 chardet 最初检测到的编码配合 errors='replace' (如果chardet有结果)
                if chardet_detected_encoding: # 确保 chardet_detected_encoding 非空
                    print(f"将尝试使用 chardet 最初检测到的编码 '{chardet_detected_encoding}' 配合 errors='replace' 作为最后手段，可能导致数据丢失。")
                    try:
                        with open(original_file_path, 'r', encoding=chardet_detected_encoding, errors='replace') as f_fallback:
                            content = f_fallback.read()
                        successfully_read_encoding = chardet_detected_encoding + " (with errors='replace')"
                        print(f"  成功使用编码 '{successfully_read_encoding}' 读取文件内容 (部分字符可能被替换)。")
                    except Exception as e_fallback:
                        print(f"  最后尝试使用 '{chardet_detected_encoding}' (errors='replace') 读取也失败: {e_fallback}")
                        content = None # 确保内容为None，以便后续逻辑判断
                else: # chardet 本身就没有检测出任何编码
                    content = None # 确保内容为None
        except FileNotFoundError:
            print(f"错误: 原始文件 '{original_file_path}' 未找到（在尝试编码 {encoding_attempt} 时）。")
            return False
        except Exception as e:
            print(f"  读取文件时发生其他错误 (编码: {encoding_attempt}): {e}")

    if content is None:
        print(f"最终未能读取文件 '{original_file_path}' 的内容。无法进行转换。")
        return False

    # --- 文件备份逻辑 (与之前一致) ---
    backup_file_path = ""
    if create_backup:
        counter = 0
        backup_base = original_file_path + ".bak"
        backup_file_path = backup_base
        while os.path.exists(backup_file_path):
            counter += 1
            backup_file_path = f"{backup_base}.{counter}"
        try:
            shutil.copy2(original_file_path, backup_file_path)
            print(f"已为 '{original_file_path}' 创建备份: '{backup_file_path}'")
        except Exception as e:
            print(f"为 '{original_file_path}' 创建备份失败: {e}")
            print("警告：未创建备份，继续转换将直接修改原文件且无备份！")
            backup_file_path = ""
    # --- 文件备份逻辑结束 ---

    print(f"准备将文件 '{original_file_path}' (实际读取编码: {successfully_read_encoding}) 直接写入为 UTF-8...")
    try:
        with open(original_file_path, 'w', encoding='utf-8') as f_new:
            f_new.write(content)
        
        print(f"成功！文件 '{original_file_path}' 已直接转换为 UTF-8 编码。")
        if backup_file_path:
            print(f"原始文件备份在: '{backup_file_path}'")
        return True
    except Exception as e: # 主要捕获写入时可能发生的错误
        print(f"将内容写入文件 '{original_file_path}' (UTF-8) 时发生错误: {e}")
        print(f"重要：文件 '{original_file_path}' 可能已被部分修改或损坏！")
        if backup_file_path:
            print(f"建议从备份恢复: '{backup_file_path}'")
        else:
            print("警告：没有备份文件可供恢复。")
        return False

if __name__ == "__main__":
    # --- 用户配置区 ---
    # 请在这里直接修改你要检查和转换的文件路径。
    #
    # 帮助：
    # 1. 如果你的文件路径中包含反斜杠 `\\` (例如 Windows 系统中的路径 D:\\folder\\file.csv)，
    #    建议在路径字符串前面加上一个小写字母 `r`，例如：r"D:\\folder\\file.csv"。
    #    这样可以防止反斜杠被错误地理解。或者，你也可以把所有的 `\\` 替换成 `/`，例如："D:/folder/file.csv"。
    # 2. 你可以检查单个文件，也可以检查多个文件。
    #
    # 方式一：检查单个文件
    # 将文件路径直接赋值给 target_paths_input。请取消下面这行的注释，并填入你的文件路径。
    # target_paths_input = r"请在这里填入你的单个CSV文件完整路径"
    #
    # 方式二：检查多个文件 (默认启用此方式)
    # 将多个文件路径放在一个列表中，赋值给 target_paths_input。
    # 如果你只想检查单个文件，请注释掉下面的列表，并启用上面的"方式一"。
    target_paths_input = [
        r"D:\学习资料\大三下\大数据应用实践\data\categories.csv",
        # 你可以根据需要，继续添加更多文件的路径，每行一个，用英文逗号隔开。
        # 例如:
        # r"C:/Users/YourName/Documents/data1.csv",
        # r"../another_folder/data2.csv",
    ]

    # (可选) 设置用于检测编码的样本字节数 (单位：字节)
    # 这个数值越大，检测可能越准，但也可能越慢。通常 10KB (10240字节) 已经足够。
    sample_size_to_use = 10240

    # 设置一个置信度阈值，低于此阈值（且非0）的检测结果将提示，但仍会尝试转换。
    # 如果希望更严格，可以在调用 convert_file_to_utf8_inplace 前增加判断。
    minimum_confidence_for_conversion_hint = 0.7

    # 是否在覆盖原始文件前创建备份（强烈建议保持为 True）
    CREATE_BACKUP_FILES = True

    # --- 执行区 (一般情况下，你不需要修改以下代码) ---
    print("--- 开始字符集检测与原地UTF-8转换 ---")

    if isinstance(target_paths_input, str):
        # 处理单个文件
        if target_paths_input == r"请在这里填入你的单个CSV文件完整路径":
            print("\n重要提示：你似乎没有修改单个文件的示例路径。")
            print("请打开 csv_charset_checker.py 文件，在 '用户配置区' 修改 target_paths_input 为你实际的文件路径。")
        else:
            print(f"准备检查单个文件: {target_paths_input}")
            original_encoding, confidence = detect_csv_encoding(target_paths_input, sample_size_to_use)
            if original_encoding:
                # 检查是否需要转换 (非UTF-8且编码有效)
                normalized_original_encoding = original_encoding.lower().replace('-', '')
                if normalized_original_encoding != 'utf8':
                    # if confidence >= minimum_confidence_for_conversion_hint: # 可以选择更严格的转换条件
                    if convert_file_to_utf8_inplace(target_paths_input, original_encoding, CREATE_BACKUP_FILES):
                        print(f"文件 '{target_paths_input}' 已成功转换为 UTF-8 并保存为: {target_paths_input}")
                    else:
                        print(f"文件 '{target_paths_input}' 从 {original_encoding} 转换失败")
                    # else:
                    #     print(f"文件 '{target_paths_input}': 原始编码 '{original_encoding}' 置信度 ({confidence:.2f}) 过低，跳过自动转换。")
                    #     failed_conversion_summary.append(target_paths_input + f" (因置信度低未转换)")
                else:
                    print(f"文件 '{target_paths_input}' 已经是 UTF-8 编码，无需转换。")
            else:
                print(f"文件 '{target_paths_input}' 无法检测原始编码")
    elif isinstance(target_paths_input, list):
        # 处理文件列表
        if not target_paths_input or \
           (len(target_paths_input) >= 1 and target_paths_input[0] == r"请在这里填入第一个CSV文件的完整路径" and len(target_paths_input) == 1 and target_paths_input[0].strip()=="") or \
           (len(target_paths_input) >= 1 and target_paths_input[0] == r"请在这里填入你的单个CSV文件完整路径" and len(target_paths_input) == 1 and target_paths_input[0].strip()=="") :
            print("\n重要提示：你似乎没有修改文件列表中的示例路径或列表为空。")
            print("请打开 csv_charset_checker.py 文件，在 '用户配置区' 修改 target_paths_input 列表为你实际的文件路径。")
            if len(target_paths_input) > 0 and not (target_paths_input[0] == r"请在这里填入第一个CSV文件的完整路径" and len(target_paths_input) ==1 and target_paths_input[0].strip()=="") : # Avoid processing default placeholder if it's the only one and not truly empty
                 pass # Don't process if it's just the placeholder
            else: # if the list is truly empty or only contains the placeholder
                target_paths_input = [] # Ensure it is empty for the loop

        if target_paths_input: # Only proceed if there are actual paths after placeholder check
            print(f"准备检查文件列表 (共 {len(target_paths_input)} 个文件)")
            successfully_modified_files = []
            failed_or_not_modified_files = []
            for i, file_path in enumerate(target_paths_input):
                file_path = file_path.strip() # 移除路径前后可能存在的空格
                if file_path and not file_path.startswith('#') and not file_path.startswith(r"请在这里填入"): # 忽略空行、注释行和未修改的占位符
                    print(f"\n[文件 {i+1}/{len(target_paths_input)}] 正在处理: {file_path}")
                    original_encoding, confidence = detect_csv_encoding(file_path, sample_size_to_use)
                    if original_encoding:
                        # 检查是否需要转换 (非UTF-8且编码有效)
                        normalized_original_encoding = original_encoding.lower().replace('-', '')
                        if normalized_original_encoding != 'utf8':
                            # if confidence >= minimum_confidence_for_conversion_hint: # 可以选择更严格的转换条件
                            if convert_file_to_utf8_inplace(file_path, original_encoding, CREATE_BACKUP_FILES):
                                successfully_modified_files.append(file_path)
                            else:
                                failed_or_not_modified_files.append(file_path + f" (从 {original_encoding} 转换失败或未完成)")
                            # else:
                            #     print(f"文件 '{file_path}': 原始编码 '{original_encoding}' 置信度 ({confidence:.2f}) 过低，跳过自动转换。")
                            #     failed_or_not_modified_files.append(file_path + f" (因置信度低未转换)")
                        else:
                            print(f"文件 '{file_path}' 已经是 UTF-8 编码，无需修改。")
                    else:
                        failed_or_not_modified_files.append(file_path + " (无法检测原始编码，未修改)")
                elif not file_path or file_path.startswith(r"请在这里填入"):
                    print(f"\n[文件 {i+1}/{len(target_paths_input)}] 路径为空或为占位符，已跳过。")
                elif file_path.startswith('#'):
                    print(f"\n[文件 {i+1}/{len(target_paths_input)}] 注释行，已跳过: {file_path}")

            print("\n--- 所有文件处理完成 ---")

            # 准确计算实际尝试处理的文件数
            actual_processed_count = 0
            if isinstance(target_paths_input, list):
                for p in target_paths_input:
                    p_stripped = p.strip()
                    if p_stripped and not p_stripped.startswith('#') and not p_stripped.startswith(r"请在这里填入"):
                        actual_processed_count += 1
            elif isinstance(target_paths_input, str): # Should be a list from earlier logic, but defensive check
                p_stripped = target_paths_input.strip()
                if p_stripped and not p_stripped.startswith('#') and not p_stripped.startswith(r"请在这里填入"):
                    actual_processed_count = 1

            # 判断是否是用户未修改占位符的情况
            is_placeholder_case = False
            if isinstance(target_paths_input, str) and target_paths_input.startswith(r"请在这里填入你的单个CSV文件完整路径"):
                is_placeholder_case = True
            elif isinstance(target_paths_input, list):
                if not target_paths_input: # 用户提供了一个空列表
                    pass # 不是占位符情况，但 actual_processed_count 会是 0
                elif all(p.strip().startswith(r"请在这里填入") for p in target_paths_input):
                    is_placeholder_case = True

            if is_placeholder_case and actual_processed_count == 0:
                print("\n重要提示：你似乎没有修改脚本中的示例文件路径。")
                print("\n请打开 csv_charset_checker.py 文件，在 '用户配置区' 修改 target_paths_input 为你实际的文件路径。")
            elif actual_processed_count == 0:
                print("\n没有提供有效的文件路径进行处理。请检查脚本中的 '用户配置区'。")
            else:
                if successfully_modified_files:
                    print("\n成功转换并原地修改为UTF-8的文件列表:")
                    for f_path in successfully_modified_files:
                        print(f"  - {f_path}")
                        if CREATE_BACKUP_FILES: # 提醒备份文件的存在
                            print(f"    (原始文件备份通常在此文件同目录下，以 .bak 或 .bak.n 结尾)")

                if failed_or_not_modified_files:
                    print("\n处理失败、未修改或无需修改的文件/原因:")
                    for item in failed_or_not_modified_files:
                        print(f"  - {item}")

                if not successfully_modified_files and not failed_or_not_modified_files and actual_processed_count > 0:
                    print("\n所有已成功检测的文件均无需转换或已是UTF-8编码。")
                elif len(successfully_modified_files) == actual_processed_count and actual_processed_count > 0:
                    print("\n所有提供的有效文件均已成功转换为UTF-8（或本身已是UTF-8）。")

        elif not (isinstance(target_paths_input, str) and target_paths_input != r"请在这里填入你的单个CSV文件完整路径"): # Only print if not the single file placeholder case
            print("提示：文件列表为空，没有文件需要处理。请在脚本中 '用户配置区' 添加文件路径。")

    else:
        print("错误：target_paths_input 变量的格式不正确。请确保它是一个文件路径字符串或一个文件路径列表。")
        print("请检查脚本中的 '用户配置区'。")

    print("--- 检测与原地转换结束 ---")

