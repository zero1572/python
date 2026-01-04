import pandas as pd
import json
import openpyxl
import dashscope
from dashscope import Generation
import os
from difflib import SequenceMatcher

# --- API Key 设置 ---
DASHSCOPE_API_KEY = ""
dashscope.api_key = DASHSCOPE_API_KEY


# --- 构建所有合法合并场景列表（用于兜底匹配）---
def build_valid_scenarios(df_ref):
    """
    从参考表构建所有合法的 (行业, 一级, 二级) 三元组及合并字符串。
    返回:
      - valid_triples: list of (industry, l1, l2)
      - valid_merged: list of "行业-一级-二级"
    """
    valid_triples = []
    for _, row in df_ref.iterrows():
        industry = str(row['行业']).strip()
        l1 = str(row['一级场景名称']).strip()
        l2 = str(row['二级场景名称']).strip()
        if industry != 'nan' and l1 != 'nan' and l2 != 'nan':
            valid_triples.append((industry, l1, l2))
    return valid_triples


def fallback_match(project_text, valid_triples):
    """
    当模型返回无效结果时，使用关键词相似度从合法三元组中选择最佳匹配。
    策略：将 project_text 与 "行业 一级 二级" 拼接字符串做相似度比较。
    """
    best_score = -1
    best_triple = ("未匹配", "未匹配", "未匹配")

    # 提取项目关键词（可扩展）
    text_lower = project_text.lower()

    for (ind, l1, l2) in valid_triples:
        candidate = f"{ind} {l1} {l2}".lower()
        score = SequenceMatcher(None, text_lower, candidate).ratio()
        if score > best_score:
            best_score = score
            best_triple = (ind, l1, l2)

    return {
        "所属行业": best_triple[0],
        "一级场景": best_triple[1],
        "二级场景": best_triple[2]
    }


# --- 调用 Qwen 分类（带后处理）---
def get_qwen_classification(text_to_classify, system_prompt, valid_triples):
    prompt = f"""
你是一个专业的数据分类助手。你的任务是根据给定的三级分类体系，将提供的“ICT项目”文本分配到最合适的类别中。

这是你的**参考分类体系**（行业 > 一级场景名称 > 二级场景名称）：
{system_prompt}

请**严格**根据文本的语义理解和项目内容，从上述体系中选择最匹配的“所属行业”、“一级场景”和“二级场景”。
一定是参考表里面存在的，不要联想其他场景词。
**即使不确定，也必须选择一个最接近的合法分类，不能返回“未匹配”或空值。**

现在，请对以下项目文本进行分类，并只返回**完整的JSON对象**，不要包含任何其他文字、解释或Markdown格式：
项目文本: "{text_to_classify}"
"""

    try:
        response = Generation.call(
            model="qwen-plus",
            prompt=prompt,
            temperature=0.0,
            seed=12345,
            result_format="text"
        )

        if response.status_code != 200:
            print(f"API 调用失败，状态码: {response.status_code}")
            return fallback_match(text_to_classify, valid_triples)

        raw_text = response.output.text.strip()

        # 清理可能的 ```json 包裹
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if len(lines) > 2 and lines[-1].strip() == "```":
                raw_text = "\n".join(lines[1:-1])
            else:
                raw_text = lines[0].strip("`").strip()

        try:
            classification = json.loads(raw_text)
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，尝试提取字段（保守策略）
            classification = {"所属行业": "Error", "一级场景": "Error", "二级场景": "Error"}

        # 检查是否为无效返回
        invalid = any(
            v in ["未匹配", "Error", "", "nan", "null", None]
            for v in classification.values()
        )
        if invalid:
            return fallback_match(text_to_classify, valid_triples)

        # 额外检查：该三元组是否在合法列表中？
        triple = (
            str(classification.get("所属行业", "")).strip(),
            str(classification.get("一级场景", "")).strip(),
            str(classification.get("二级场景", "")).strip()
        )
        if triple not in valid_triples:
            # 如果模型返回了非法组合，仍用兜底
            return fallback_match(text_to_classify, valid_triples)

        return classification

    except Exception as e:
        print(f"调用通义千问时出错: {e}")
        return fallback_match(text_to_classify, valid_triples)


# --- 主程序 ---
def main():
    # 1. 加载数据
    try:
        df_data = pd.read_excel("待处理8.xlsx")
        df_ref = pd.read_excel("参考表.xlsx")
        print("Excel文件加载成功。")
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return

    # 2. 构建分类体系字符串（用于 prompt）
    classification_system = ""
    for industry, group_i in df_ref.groupby('行业'):
        classification_system += f"## 行业: {industry}\n"
        for l1, group_l1 in group_i.groupby('一级场景名称'):
            classification_system += f"  - 一级场景: {l1}\n"
            l2_list = group_l1['二级场景名称'].dropna().unique().tolist()
            l2_str = ", ".join([str(x) for x in l2_list if str(x).strip() != ''])
            classification_system += f"    - 二级场景列表: {l2_str or '[无]'}\n"

    # 3. 构建合法三元组（用于验证和兜底）
    valid_triples = build_valid_scenarios(df_ref)
    print(f"共加载 {len(valid_triples)} 个合法分类场景。")

    # 4. 遍历分类
    classification_results = []
    total_rows = len(df_data)
    print(f"开始处理 {total_rows} 条数据...")

    for index, row in df_data.iterrows():
        project_text = str(row['ICT项目']).strip() if pd.notna(row['ICT项目']) else ""
        if not project_text:
            result = {"所属行业": "空文本", "一级场景": "空文本", "二级场景": "空文本"}
        else:
            print(f"[{index + 1}/{total_rows}] 正在分类: {project_text[:40]}...")
            result = get_qwen_classification(project_text, classification_system, valid_triples)
        result['ICT项目'] = project_text
        classification_results.append(result)

    # 5. 保存结果
    df_classified = pd.DataFrame(classification_results)
    df_classified = df_classified[['ICT项目', '所属行业', '一级场景', '二级场景']]
    df_final = df_data[['ICT项目']].merge(df_classified, on='ICT项目', how='left')

    output_filename = "classified_output_Qwen.xlsx"
    df_final.to_excel(output_filename, index=False)
    print(f"✅ 分类完成！结果已保存到 {output_filename}")


if __name__ == "__main__":
    main()