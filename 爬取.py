import os
import requests
from bs4 import BeautifulSoup
import re
import csv

def crawl_and_save(url, file_number, csv_writer, output_folder):
    hd = {'user-agent': 'chrome'}

    try:
        r = requests.get(url, headers=hd, timeout=10)
        r.encoding = 'utf-8'
        r.raise_for_status()  # 检查请求是否成功，若失败则抛出异常
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return

    soup = BeautifulSoup(r.text, features="html.parser")

    # 找到标题
    title_element = soup.find('div', class_='article-title')
    title_text = title_element.find('h4').text.strip() if title_element else ''

    # 找到发布时间
    time_element = soup.find('ul', class_='list-unstyled list-inline')
    time_li = time_element.find('li', string=re.compile(r'发布时间')) if time_element else None
    time_text = time_li.text.strip() if time_li else ''

    # 找到正文内容
    li_element = soup.find('div', class_='article-body')

    # 检查是否找到正文内容
    if li_element:
        li_elements = li_element.find_all('p')

        # 计算正文字数
        word_count = sum(len(re.findall(r'[\u4e00-\u9fa5]', p.text.strip())) for p in li_elements)

        # 生成文件名
        file_path = os.path.join(output_folder, f'{file_number:02d}.txt')

        with open(file_path, 'w', encoding='utf-8') as file:
            # 写入标题和时间
            file.write(f"{title_text}\n" if title_text else "")
            file.write(f"{time_text}\n\n" if time_text else "")

            # 写入正文内容
            for li_element in li_elements:
                file.write(li_element.text.strip() + '\n')

        # 写入CSV文件
        csv_writer.writerow([file_number, time_text, word_count, title_text])

    else:
        print(f"未找到正文内容：{url}")

# 循环爬取文章，并记录统计信息
output_folder = 'C:\\Users\\蔡梓凯\\Desktop\\2240232127蔡梓凯\\txt'
csv_path = os.path.join(output_folder, '统计.csv')

with open(csv_path, 'w', encoding='utf-8-sig', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["序号", "时间", "字数", "标题"])  # 写入CSV文件的标题行

    for i in range(10, 45):
        url = f'https://news.seig.edu.cn/cms/81{i}.html'
        try:
            crawl_and_save(url, i - 11, csv_writer, output_folder)
        except Exception as e:
            i = i - 9
            print(f"爬取第 {i} 篇文章时出错: {e}")
