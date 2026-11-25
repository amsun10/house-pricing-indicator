#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万流宁邸 (嘉宏·万流江宁, NJhouse prjId=4600200) 每日官方销售数据抓取脚本
数据源：南京网上房地产 (www.njhouse.com.cn) 官方项目主页静态公示表
"""

import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

PROJECT_ID = "4600200"
PROJECT_NAME = "嘉宏·万流宁邸 (万流江宁)"
OFFICIAL_URL = f"https://www.njhouse.com.cn/project/info/{PROJECT_ID}/homePage.html"
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wanliu_daily.json")
TZ_CN = timezone(timedelta(hours=8))


def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_homepage_html(retries=3, timeout=20):
    """请求 NJhouse 万流宁邸项目官网主页，支持重试"""
    ctx = create_ssl_context()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(OFFICIAL_URL, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                if "项目整体销售情况" in html:
                    return html
                raise ValueError("页面内容不包含'项目整体销售情况'")
        except Exception as e:
            last_err = e
            print(f"[Warn] 第 {attempt}/{retries} 次抓取失败: {e}")
            if attempt < retries:
                time.sleep(attempt * 3)
    raise RuntimeError(f"连续 {retries} 次请求失败: {last_err}")


def extract_metric(html, label, is_float=False):
    """从表格 HTML 中精准提取指定字段数值"""
    pattern = rf'<td[^>]*>\s*{re.escape(label)}\s*</td>\s*<td[^>]*>\s*([\d\.]+)\s*(?:套|㎡)?\s*</td>'
    m = re.search(pattern, html)
    if not m:
        raise ValueError(f"未能从页面提取字段: {label}")
    val_str = m.group(1)
    return round(float(val_str), 2) if is_float else int(round(float(val_str)))


def parse_sales_metrics(html):
    """解析项目整体销售情况所有官方指标"""
    total_suites = extract_metric(html, "入网总套数")
    total_area = extract_metric(html, "入网总面积", is_float=True)
    unsold_suites = extract_metric(html, "未售总套数")
    unsold_area = extract_metric(html, "未售总面积", is_float=True)
    subscribed_suites = extract_metric(html, "总认购套数")
    subscribed_area = extract_metric(html, "总认购面积", is_float=True)
    sold_suites = extract_metric(html, "总成交套数")
    sold_area = extract_metric(html, "总成交面积", is_float=True)
    today_subscribed = extract_metric(html, "今日认购")
    today_sold = extract_metric(html, "今日成交")

    # 数据一致性校验
    if sold_suites + subscribed_suites + unsold_suites != total_suites:
        print(
            f"[Warn] 套数加和校验有差异: 成交({sold_suites}) + 认购({subscribed_suites}) + 未售({unsold_suites}) != 入网总套数({total_suites})"
        )

    return {
        "total_suites": total_suites,
        "total_area": total_area,
        "sold_suites": sold_suites,
        "sold_area": sold_area,
        "subscribed_suites": subscribed_suites,
        "subscribed_area": subscribed_area,
        "unsold_suites": unsold_suites,
        "unsold_area": unsold_area,
        "today_subscribed": today_subscribed,
        "today_sold": today_sold,
    }


def load_existing_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "project_id": PROJECT_ID,
        "project_name": PROJECT_NAME,
        "official_url": OFFICIAL_URL,
        "source": "南京网上房地产 (www.njhouse.com.cn)",
        "updated_at": "",
        "daily_records": [],
    }


def main():
    print("=" * 60)
    print(f"【{PROJECT_NAME}】NJhouse 每日销售数据采集")
    print("=" * 60)

    now_cn = datetime.now(TZ_CN)
    today_str = now_cn.strftime("%Y-%m-%d")
    timestamp_str = now_cn.strftime("%Y-%m-%d %H:%M:%S")

    html = fetch_homepage_html()
    metrics = parse_sales_metrics(html)

    record = {
        "date": today_str,
        **metrics,
        "updated_at": timestamp_str,
    }

    data = load_existing_data()
    data["project_id"] = PROJECT_ID
    data["project_name"] = PROJECT_NAME
    data["official_url"] = OFFICIAL_URL
    data["source"] = "南京网上房地产 (www.njhouse.com.cn)"
    data["updated_at"] = timestamp_str

    records = data.get("daily_records", [])
    # 幂等更新同一天记录
    updated = False
    for idx, item in enumerate(records):
        if item.get("date") == today_str:
            records[idx] = record
            updated = True
            break
    if not updated:
        records.append(record)

    records.sort(key=lambda x: x["date"])
    data["daily_records"] = records

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    committed = metrics["sold_suites"] + metrics["subscribed_suites"]
    rate = (committed / metrics["total_suites"] * 100) if metrics["total_suites"] else 0.0
    print(f"[Success] {today_str} 快照已保存至 {DATA_PATH}")
    print(
        f"  • 入网总套数: {metrics['total_suites']} 套 ({metrics['total_area']} ㎡)\n"
        f"  • 总成交: {metrics['sold_suites']} 套 | 总认购: {metrics['subscribed_suites']} 套 | 综合去化率: {rate:.1f}%\n"
        f"  • 剩余未售: {metrics['unsold_suites']} 套 ({metrics['unsold_area']} ㎡)\n"
        f"  • 官网当日瞬时: 今日认购 {metrics['today_subscribed']} 套 | 今日成交 {metrics['today_sold']} 套"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"[Error] 采集失败: {err}", file=sys.stderr)
        sys.exit(1)
