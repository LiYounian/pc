#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黄金价格爬虫脚本
爬取北京菜百金价的每日黄金价格并保存到数据库
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import sqlite3
import schedule

# 数据库配置
DB_FILE = 'gold_price.db'

# 全局定时任务配置
SCHEDULE_TIME = "12:00"

def set_schedule_time(time_str):
    """设置定时任务的执行时间"""
    global SCHEDULE_TIME
    try:
        # 验证时间格式
        from datetime import datetime as dt
        dt.strptime(time_str, '%H:%M')
        SCHEDULE_TIME = time_str
        print(f"定时任务时间已更新为: {SCHEDULE_TIME}")
        return True
    except ValueError:
        print("时间格式错误，请使用 HH:MM 格式（例如：12:00）")
        return False

def init_database():
    """初始化数据库，如果不存在则创建"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 创建黄金价格表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gold_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            首饰名称 TEXT,
            最新价格 TEXT,
            单位 TEXT,
            纯度 TEXT,
            更新日期 TEXT,
            爬取时间 TEXT,
            创建时间 DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_FILE}")

def save_to_database(data):
    """将数据保存到数据库"""
    if not data:
        print("没有数据可保存到数据库")
        return False

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        crawl_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for item in data:
            cursor.execute('''
                INSERT INTO gold_prices (首饰名称, 最新价格, 单位, 纯度, 更新日期, 爬取时间)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                item.get('首饰名称', ''),
                item.get('最新价格', ''),
                item.get('单位', ''),
                item.get('纯度', ''),
                item.get('更新日期', ''),
                crawl_time
            ))

        conn.commit()
        print(f"成功保存 {len(data)} 条数据到数据库")
        return True

    except Exception as e:
        print(f"保存到数据库失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def export_to_excel():
    """从数据库导出数据到Excel"""
    conn = sqlite3.connect(DB_FILE)
    try:
        # 从数据库读取所有数据
        query = "SELECT 首饰名称, 最新价格, 单位, 纯度, 更新日期, 爬取时间, 创建时间 FROM gold_prices"
        df = pd.read_sql_query(query, conn)

        if df.empty:
            print("数据库中没有数据")
            return False

        # 转换爬取时间为datetime类型以便比较
        df['爬取时间'] = pd.to_datetime(df['爬取时间'])

        # 按照"首饰名称"、"更新日期"、"爬取时间"排序（保留最新爬取时间）
        df_sorted = df.sort_values(['首饰名称', '更新日期', '爬取时间'], ascending=[True, True, False])

        # 按照"首饰名称"、"更新日期"去重，保留每组中爬取时间最新的记录
        df_deduplicated = df_sorted.drop_duplicates(subset=['首饰名称', '更新日期'], keep='first')

        # 移除创建时间列（导出时不需要）
        df_export = df_deduplicated[['首饰名称', '最新价格', '单位', '纯度', '更新日期', '爬取时间']].copy()

        # 格式化爬取时间显示
        df_export['爬取时间'] = df_export['爬取时间'].dt.strftime('%Y-%m-%d %H:%M:%S')

        # 生成文件名
        filename = f"information_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # 保存到Excel
        df_export.to_excel(filename, index=False, engine='openpyxl')
        print(f"数据已成功导出到 {filename}")
        print(f"共导出 {len(df_export)} 条记录（去重前：{len(df)} 条）")

        # 打印数据预览
        print("\n数据预览:")
        print(df_export.head(10).to_string(index=False))

        return True

    except Exception as e:
        print(f"导出Excel失败: {e}")
        return False
    finally:
        conn.close()

def query_database(limit=None):
    """查询数据库中的数据"""
    conn = sqlite3.connect(DB_FILE)
    try:
        query = "SELECT 首饰名称, 最新价格, 单位, 纯度, 更新日期, 爬取时间, 创建时间 FROM gold_prices ORDER BY 创建时间 DESC"
        if limit:
            query += f" LIMIT {limit}"

        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"查询数据库失败: {e}")
        return None
    finally:
        conn.close()

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
                    if any(keyword in ' '.join(header_texts) for keyword in ['首饰', '价格', '单位', '纯度', '更新']):
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
                    elif '更新' in header:
                        col_mapping['更新日期'] = idx

                # 提取数据行
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= len(col_mapping) and cols[0].get_text().strip() not in ['首饰', '价格', '单位', '纯度', '更新']:
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
    """将数据保存到Excel（保留此函数用于兼容）"""
    if not data:
        print("没有数据可保存")
        return False

    try:
        df = pd.DataFrame(data)

        # 确保列顺序
        columns_order = ['首饰名称', '最新价格', '单位', '纯度', '更新日期']
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

def show_help():
    """显示帮助信息"""
    print("\n" + "=" * 50)
    print("可用命令:")
    print("  run_once         - 立即执行爬取任务")
    print("  set_time HH:MM   - 修改定时任务时间（例如：set_time 14:30）")
    print("  start            - 开启定时任务模式（每天在设定时间自动执行）")
    print("  stop             - 停止定时任务")
    print("  export           - 从数据库导出数据到Excel")
    print("  query [N]        - 查询数据库中的最新N条记录（不指定N则查询全部）")
    print("  help             - 显示此帮助信息")
    print("  exit             - 退出程序")
    print("=" * 50)

def handle_command(cmd):
    """处理用户命令"""
    cmd = cmd.strip().lower()

    if cmd == 'run_once':
        scheduled_task()
    elif cmd.startswith('set_time '):
        time_str = cmd[9:].strip()  # 获取 "set_time " 之后的时间
        if set_schedule_time(time_str):
            print(f"定时时间已更新，下次定时任务将使用新时间: {SCHEDULE_TIME}")
    elif cmd == 'start':
        print(f"\n定时任务已开启，每天 {SCHEDULE_TIME} 自动执行")
        print("提示: 输入 'stop' 停止定时任务")
        return True  # 返回True表示需要进入定时任务循环
    elif cmd == 'stop':
        schedule.clear()
        print("定时任务已停止")
    elif cmd == 'export':
        export_to_excel()
    elif cmd.startswith('query'):
        parts = cmd.split()
        limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        df = query_database(limit)
        if df is not None and not df.empty:
            print(f"\n查询结果 ({'全部' if limit is None else f'最新 {limit} 条'}):")
            print(df.to_string(index=False))
        elif df is not None and df.empty:
            print("数据库中没有数据")
    elif cmd == 'help':
        show_help()
    else:
        print(f"未知命令: {cmd}")
        print("输入 'help' 查看可用命令")

    return False  # 返回False表示不需要进入定时任务循环

def scheduled_task():
    """定时任务：爬取数据、保存到数据库、导出Excel"""
    print("\n" + "=" * 50)
    print(f"定时任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 爬取数据
    data = crawl_gold_price()

    if data:
        print(f"\n成功爬取到 {len(data)} 条数据")

        # 保存到数据库
        save_to_database(data)

        # 导出Excel
        export_to_excel()

        print("\n定时任务完成")
    else:
        print("爬取失败，请检查网络连接或网站是否可访问")
        print("\n提示:")
        print("1. 确保网络连接正常")
        print("2. 检查网站是否可访问: http://www.huangjinjiage.cn/gold/bjcbjj.html")
        print("3. 网站结构可能发生变化，需要调整解析逻辑")

import sys

def has_stdin():
    """检查是否有可用的标准输入流"""
    try:
        # 尝试访问 sys.stdin
        sys.stdin.fileno()
        # 检查是否为终端或有效输入流
        return sys.stdin.isatty() or not sys.stdin.closed
    except (AttributeError, OSError):
        return False

def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode in ['--run', '-r', 'run']:
            # 自动运行模式：执行一次任务后退出
            print("=" * 50)
            print("黄金价格爬虫脚本 - 自动运行模式")
            print("=" * 50)
            init_database()
            scheduled_task()
            print("\n任务完成！程序将在5秒后自动退出...")
            time.sleep(5)
            return

    print("=" * 50)
    print("黄金价格爬虫脚本 - 北京菜百金价")
    print("=" * 50)

    # 初始化数据库
    init_database()

    # 检查是否有标准输入流
    if not has_stdin():
        print("\n检测到无交互环境（如双击exe文件），将执行以下操作:")
        print("1. 立即执行一次爬取任务并生成Excel")
        print("2. 切换到定时任务模式（每天自动执行）")
        print(f"   定时时间: {SCHEDULE_TIME}")
        print("提示：也可以通过命令行参数运行: program.exe --run\n")

        # 立即执行一次爬取任务
        scheduled_task()

        # 进入定时任务模式
        print(f"\n定时任务已开启，每天 {SCHEDULE_TIME} 自动执行")
        print("提示: 按 Ctrl+C 可停止程序\n")

        # 设置定时任务
        schedule.every().day.at(SCHEDULE_TIME).do(scheduled_task)

        try:
            # 先执行一次检查
            schedule.run_pending()

            while True:
                time.sleep(60)  # 每分钟检查一次
                schedule.run_pending()
        except KeyboardInterrupt:
            print("\n定时任务已停止")
            schedule.clear()
        return

    # 显示帮助信息
    show_help()

    # 交互模式
    while True:
        try:
            cmd = input("\n请输入命令: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n程序退出")
            break

        if cmd == 'exit':
            print("程序退出")
            break
        elif cmd == 'start':
            print(f"\n定时任务已开启，每天 {SCHEDULE_TIME} 自动执行")
            print("提示: 输入 'stop' 停止定时任务")
            print("注意: 部分环境下无法在定时任务期间交互，可使用 Ctrl+C 停止\n")

            # 设置定时任务
            schedule.every().day.at(SCHEDULE_TIME).do(scheduled_task)

            try:
                # 先执行一次检查
                schedule.run_pending()

                while True:
                    time.sleep(60)  # 每分钟检查一次
                    schedule.run_pending()
            except KeyboardInterrupt:
                print("\n定时任务已停止")
                schedule.clear()
        else:
            handle_command(cmd)

if __name__ == "__main__":
    main()
