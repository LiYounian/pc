#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格爬虫脚本
爬取北京菜百金价的每日黄金价格并保存到Excel
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time

def crawl_gold_price():
    """爬取黄金价格数据"""
    url = "http://www.huangjinjiage.cn/gold/bjcbjj.html"

    # 设置请求头，模拟浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
    }

    try:
        print(f"正在爬取网页: {url}")
        response = requests.get(url, headers=headers, timeout=30)

        # 自动检测编码
        response.encoding = response.apparent_encoding
        response.raise_for_status()

        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        gold_data = []

        # 查找包含黄金价格的主容器或表格
        # 尝试多种可能的定位方式

        # 方式1: 查找表格
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            # 获取表头，确定列的索引
            headers_row = None
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if cols:
                    header_texts = [col.get_text().strip() for col in cols]
                    # 检查是否包含我们需要的字段
                    if any(keyword in ' '.join(header_texts) for keyword in ['首饰', '价格', '单位', '纯度', '手工费', '更新']):
                        headers_row = header_texts
                        break

            if headers_row:
                # 根据表头确定列索引
                col_mapping = {}
                for idx, header in enumerate(headers_row):
                    if '首饰' in header or '名称' in header:
                        col_mapping['首饰名称'] = idx
                    elif '价格' in header and '最新' in header:
                        col_mapping['最新价格'] = idx
                    elif '单位' in header:
                        col_mapping['单位'] = idx
                    elif '纯度' in header:
                        col_mapping['纯度'] = idx
                    elif '手工' in header:
                        col_mapping['手工费'] = idx
                    elif '更新' in header:
                        col_mapping['更新日期'] = idx

                # 提取数据行
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= len(col_mapping) and cols[0].get_text().strip() not in ['首饰', '价格', '单位', '纯度', '手工费', '更新']:
                        item = {}
                        for field, idx in col_mapping.items():
                            if idx < len(cols):
                                # 清理文本并处理编码
                                text = cols[idx].get_text().strip()
                                # 尝试编码转换
                                try:
                                    # 如果显示乱码，尝试重新编码
                                    if text:
                                        item[field] = text.encode('latin-1').decode('gbk', errors='ignore').encode('gbk').decode('utf-8', errors='ignore')
                                    else:
                                        item[field] = ''
                                except:
                                    item[field] = text
                            else:
                                item[field] = ''

                        # 确保至少有首饰名称或价格
                        if item.get('首饰名称') or item.get('最新价格'):
                            gold_data.append(item)

        # 方式2: 如果没找到表格，尝试查找div结构
        if not gold_data:
            print("未在表格中找到数据，尝试查找其他HTML结构...")

            # 查找所有包含数据信息的div或容器
            # 查找可能包含商品信息的元素
            product_elements = soup.find_all(['div', 'li', 'dl'])

            for element in product_elements:
                text = element.get_text().strip()

                # 尝试匹配包含数字（价格）的数据行
                if any(char.isdigit() for char in text) and len(text) > 10:
                    # 清理编码
                    try:
                        clean_text = text.encode('latin-1').decode('gbk', errors='ignore').encode('gbk').decode('utf-8', errors='ignore')
                    except:
                        clean_text = text

                    gold_data.append({
                        '首饰名称': clean_text[:50],  # 截取前50字符作为名称
                        '最新价格': '',
                        '单位': '元/克',
                        '纯度': '',
                        '手工费': '',
                        '更新日期': datetime.now().strftime('%Y-%m-%d')
                    })

        # 提取页面上的更新日期
        update_date = ''
        date_patterns = [
            r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
            r'更新时间[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        ]

        import re
        page_text = soup.get_text()

        # 清理页面文本编码
        try:
            page_text = page_text.encode('latin-1').decode('gbk', errors='ignore').encode('gbk').decode('utf-8', errors='ignore')
        except:
            pass

        for pattern in date_patterns:
            match = re.search(pattern, page_text)
            if match:
                update_date = match.group(1)
                break

        # 为所有记录统一更新日期
        if update_date:
            for item in gold_data:
                if not item.get('更新日期'):
                    item['更新日期'] = update_date

        return gold_data

    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except Exception as e:
        print(f"解析失败: {e}")
        return None

def save_to_excel(data, filename='gold_price.xlsx'):
    """将数据保存到Excel"""
    if not data:
        print("没有数据可保存")
        return False

    try:
        df = pd.DataFrame(data)

        # 确保列顺序
        columns_order = ['首饰名称', '最新价格', '单位', '纯度', '手工费', '更新日期']
        # 只保留存在的列
        df = df[[col for col in columns_order if col in df.columns]]

        # 添加爬取时间
        df['爬取时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 保存到Excel
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"数据已成功保存到 {filename}")
        print(f"共保存 {len(df)} 条记录")

        # 打印数据预览
        print("\n数据预览:")
        print(df.head().to_string(index=False))

        return True

    except Exception as e:
        print(f"保存Excel失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("黄金价格爬虫脚本 - 北京菜百金价")
    print("=" * 50)

    # 爬取数据
    data = crawl_gold_price()

    if data:
        print(f"\n成功爬取到 {len(data)} 条数据")

        # 保存到Excel
        filename = f"gold_price_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        save_to_excel(data, filename)
    else:
        print("爬取失败，请检查网络连接或网站是否可访问")
        print("\n提示:")
        print("1. 确保网络连接正常")
        print("2. 检查网站是否可访问: http://www.huangjinjiage.cn/gold/bjcbjj.html")
        print("3. 网站结构可能发生变化，需要调整解析逻辑")

if __name__ == "__main__":
    main()
