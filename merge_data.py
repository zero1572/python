import pandas as pd
import os
import glob


def extract_data_from_excel(filepath):
    """
    从单个Excel文件中提取指定数据。
    如果成功，返回一个包含数据和“源文件”列的DataFrame。
    如果失败（找不到表头或工作表），返回None。
    """
    try:
        # 读取整个工作表，不设置表头，以便我们查找
        df_full = pd.read_excel(filepath, sheet_name='附表1.5设备采购费', header=None)
    except ValueError:
        print(f"  [警告] 文件 {os.path.basename(filepath)} 中未找到名为 '附表1.5设备采购费' 的工作表，已跳过。")
        return None
    except Exception as e:
        print(f"  [错误] 读取文件 {os.path.basename(filepath)} 时发生未知错误: {e}，已跳过。")
        return None

    # 定义需要查找的列名
    columns_to_find = [
        "设备/软件", "设备品牌", "设备型号", "采购方式", "设备参数",
        "数量", "单位", "单价（不含税）", "合计（不含税）"
    ]

    # 查找表头所在的行索引
    header_row_index = None
    for index, row in df_full.iterrows():
        # 检查该行是否包含所有我们需要的列名
        if all(col in row.values for col in columns_to_find):
            header_row_index = index
            break

    if header_row_index is not None:
        # 使用找到的表头行重新读取数据
        df = pd.read_excel(filepath, sheet_name='附表1.5设备采购费', header=header_row_index)

        # 只选择我们需要的列
        df_extracted = df[columns_to_find].copy()  # 使用.copy()避免SettingWithCopyWarning

        # 删除完全为空的行
        df_extracted.dropna(how='all', inplace=True)

        # 添加一列，记录数据来源的文件名，方便追溯
        df_extracted['源文件'] = os.path.basename(filepath)

        return df_extracted
    else:
        print(f"  [警告] 在文件 {os.path.basename(filepath)} 的工作表中未找到匹配的表头，已跳过。")
        return None


def main():
    """
    主函数，遍历文件夹，提取并合并所有数据。
    """
    # --- 配置区 ---
    # 存放所有Excel文件的文件夹名称
    input_folder = 'excel_files'
    # 最终合并后输出的文件名
    output_filename = '设备采购费汇总表.xlsx'
    # --- 配置结束 ---

    # 检查输入文件夹是否存在
    if not os.path.isdir(input_folder):
        print(f"错误：文件夹 '{input_folder}' 不存在！请检查脚本和文件夹的相对位置。")
        return

    # 使用glob查找文件夹内所有的.xlsx和.xls文件
    search_path = os.path.join(input_folder, '*.xls*')
    excel_files = glob.glob(search_path)

    if not excel_files:
        print(f"在文件夹 '{input_folder}' 中未找到任何Excel文件。")
        return

    print(f"在文件夹 '{input_folder}' 中找到 {len(excel_files)} 个文件，开始处理...")
    print("-" * 50)

    all_data_frames = []

    # 遍历所有找到的Excel文件
    for file_path in excel_files:
        print(f"正在处理: {os.path.basename(file_path)}")
        extracted_df = extract_data_from_excel(file_path)

        # 如果成功提取到数据，就将其添加到列表中
        if extracted_df is not None and not extracted_df.empty:
            all_data_frames.append(extracted_df)

    print("-" * 50)

    # 检查是否有数据被提取出来
    if not all_data_frames:
        print("未能从任何文件中提取到有效数据。")
        return

    # 使用pd.concat合并所有DataFrame
    # ignore_index=True会重新生成一个从0开始的连续索引
    final_df = pd.concat(all_data_frames, ignore_index=True)

    # 将合并后的数据保存到新的Excel文件
    try:
        final_df.to_excel(output_filename, index=False)
        print(f"\n数据合并成功！")
        print(f"总共从 {len(all_data_frames)} 个文件中提取了 {len(final_df)} 行数据。")
        print(f"结果已保存到文件: {output_filename}")
    except Exception as e:
        print(f"\n保存文件时出错: {e}")


if __name__ == "__main__":
    main()
