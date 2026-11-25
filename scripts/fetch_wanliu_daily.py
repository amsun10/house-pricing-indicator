#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万流宁邸 (嘉宏·万流江宁, NJhouse prjId=4600200) 每日官方销售数据抓取脚本
数据源：南京网上房地产 (www.njhouse.com.cn) 项目主页与分楼栋销控表 (saleInfo.html)
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
SALE_INFO_URL = f"https://www.njhouse.com.cn/project/info/{PROJECT_ID}/saleInfo.html"
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wanliu_daily.json")
TZ_CN = timezone(timedelta(hours=8))


def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_html(url, expected_marker, retries=3, timeout=20):
    """通用抓取函数，支持重试与页面内容校验"""
    ctx = create_ssl_context()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                if expected_marker in html:
                    return html
                raise ValueError(f"页面内容未包含预期标识: {expected_marker}")
        except Exception as e:
            last_err = e
            print(f"[Warn] 请求 {url} 第 {attempt}/{retries} 次失败: {e}")
            if attempt < retries:
                time.sleep(attempt * 3)
    raise RuntimeError(f"连续 {retries} 次请求 {url} 失败: {last_err}")


def extract_metric(html, label, is_float=False):
    """从主页汇总表格 HTML 中精准提取数值"""
    pattern = rf'<td[^>]*>\s*{re.escape(label)}\s*</td>\s*<td[^>]*>\s*([\d\.]+)\s*(?:套|㎡)?\s*</td>'
    m = re.search(pattern, html)
    if not m:
        raise ValueError(f"未能从页面提取字段: {label}")
    val_str = m.group(1)
    return round(float(val_str), 2) if is_float else int(round(float(val_str)))


def parse_project_summary(html):
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


def building_sort_key(name):
    m = re.search(r'(\d+)', str(name))
    return (0, int(m.group(1)), str(name)) if m else (1, 0, str(name))


def parse_buildings(sale_html):
    """解析 saleInfo.html 中的逐栋销售实时数据 (projectInfoBuildingSaleInfo)"""
    m = re.search(r'let\s+projectInfoBuildingSaleInfo\s*=\s*(\[[\s\S]*?\]);', sale_html)
    if not m:
        raise ValueError("未能从 saleInfo.html 中找到 projectInfoBuildingSaleInfo")

    raw_js = m.group(1)
    # 将 JS 对象字面量的键名转为合法 JSON 字符串键名
    json_str = re.sub(r'([\{,\s])([a-zA-Z0-9_]+)\s*:', lambda x: f'{x.group(1)}"{x.group(2)}":', raw_js)
    items = json.loads(json_str)

    buildings = []
    for b in items:
        buildings.append({
            "build_id": str(b.get("buildId", "")),
            "name": str(b.get("buildingName", "")),
            "sale_date": str(b.get("saleDate", "")),
            "total_suites": int(round(float(b.get("allSets", 0) or 0))),
            "total_area": round(float(b.get("allArea", 0) or 0), 2),
            "sold_suites": int(round(float(b.get("soldSets", 0) or 0))),
            "sold_area": round(float(b.get("soldArea", 0) or 0), 2),
            "subscribed_suites": int(round(float(b.get("bookedSets", 0) or 0))),
            "subscribed_area": round(float(b.get("bookedArea", 0) or 0), 2),
            "unsold_suites": int(round(float(b.get("unsoldSets", 0) or 0))),
            "unsold_area": round(float(b.get("unsoldArea", 0) or 0), 2),
            "today_subscribed": int(round(float(b.get("bookedSetsToday", 0) or 0))),
            "today_sold": int(round(float(b.get("soldSetsToday", 0) or 0))),
            "building_url": f"https://www.njhouse.com.cn/project/info/{PROJECT_ID}/buildingInfo.html?projectId={PROJECT_ID}&buildId={b.get('buildId', '')}",
        })

    buildings.sort(key=lambda x: building_sort_key(x["name"]))
    return buildings


def load_existing_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "project_id": PROJECT_ID,
        "project_name": PROJECT_NAME,
        "official_url": OFFICIAL_URL,
        "sale_info_url": SALE_INFO_URL,
        "source": "南京网上房地产 (www.njhouse.com.cn)",
        "updated_at": "",
        "daily_records": [],
    }


def main():
    print("=" * 60)
    print(f"【{PROJECT_NAME}】NJhouse 每日销售数据（含分楼栋）采集")
    print("=" * 60)

    force = "--force" in sys.argv
    now_cn = datetime.now(TZ_CN)
    today_str = now_cn.strftime("%Y-%m-%d")
    timestamp_str = now_cn.strftime("%Y-%m-%d %H:%M:%S")

    data = load_existing_data()
    records = data.get("daily_records", [])
    if not force and any(item.get("date") == today_str for item in records):
        print(f"[Skip] 今日 ({today_str}) 已执行过数据采集，直接跳过（如需强制重抓请加 --force）。")
        return

    home_html = fetch_html(OFFICIAL_URL, "项目整体销售情况")
    metrics = parse_project_summary(home_html)

    sale_html = fetch_html(SALE_INFO_URL, "projectInfoBuildingSaleInfo")
    buildings = parse_buildings(sale_html)

    record = {
        "date": today_str,
        **metrics,
        "buildings": buildings,
        "updated_at": timestamp_str,
    }

    data["project_id"] = PROJECT_ID
    data["project_name"] = PROJECT_NAME
    data["official_url"] = OFFICIAL_URL
    data["sale_info_url"] = SALE_INFO_URL
    data["source"] = "南京网上房地产 (www.njhouse.com.cn)"
    data["updated_at"] = timestamp_str

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
    print(f"[Success] {today_str} 快照已保存至 {DATA_PATH} (共 {len(buildings)} 栋楼)")
    print(f"  • 整体：入网 {metrics['total_suites']} 套 | 成交 {metrics['sold_suites']} | 认购 {metrics['subscribed_suites']} | 未售 {metrics['unsold_suites']} (去化 {rate:.1f}%)")
    for b in buildings:
        print(
            f"    - {b['name']:>3} (开盘 {b['sale_date']}): 总 {b['total_suites']:>2} | 成交 {b['sold_suites']:>2} | 认购 {b['subscribed_suites']:>2} | 未售 {b['unsold_suites']:>2} | 今日认购:{b['today_subscribed']} 今日成交:{b['today_sold']}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"[Error] 采集失败: {err}", file=sys.stderr)
        sys.exit(1)
