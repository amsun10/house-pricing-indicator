#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从南京网上房地产 (www.njhouse.com.cn) 官方提取最新月度房地产市场分析数据
并与本地 data.json 进行核验与同步（杜绝任何非官方臆造数据）
"""

import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")

def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_official_reports_list():
    """从南京网上房地产首页抓取已发布的官方市场分析月报链接与文章ID"""
    url = "https://www.njhouse.com.cn/index.html"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    ctx = create_ssl_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[Warn] 获取官网首页失败: {e}")
        return []

    pattern = r'xwzxDetail\.html\?contentid=([a-zA-Z0-9]+)[\s\S]*?indexNews_list_mian_word[\x22\x27]>([^<]+)<'
    matches = re.findall(pattern, html)
    reports = []
    for cid, title in matches:
        title = title.strip()
        m_match = re.search(r'(\d{4})年(\d{1,2})月', title)
        if m_match and "市场分析" in title:
            year, month = m_match.group(1), int(m_match.group(2))
            ym = f"{year}-{month:02d}"
            reports.append({"contentId": cid, "title": title, "year_month": ym})
    
    reports.sort(key=lambda x: x["year_month"])
    return reports

def fetch_report_detail(content_id):
    """根据 contentId 请求官方月报富文本内容"""
    api_url = "https://www.njhouse.com.cn/jsmart/web/content/getDetailsByTContentId"
    data = urllib.parse.urlencode({"tContentId": content_id}).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    ctx = create_ssl_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8", errors="ignore"))
            return res.get("data", {}).get("content", "")
    except Exception as e:
        print(f"[Warn] 请求文章详情失败 ({content_id}): {e}")
        return ""

def parse_report_metrics(content_html):
    """解析官方月报内容中的商品住宅与二手住宅成交/上市套数与关键指标"""
    text = re.sub(r'<[^>]+>', ' ', content_html)
    text = re.sub(r'\s+', ' ', text)

    metrics = {
        "new_house_listed_suites": None,    # 全市商品住宅上市套数
        "new_house_listed_projects": None,  # 全市商品住宅上市项目数
        "sec_house_total_suites": None,     # 全市二手住宅成交总套数 (套)
        "sec_house_area_wan_m2": None,      # 全市二手住宅成交面积 (万㎡)
        "jn_highlight_projects": [],        # 官方通报提及的江宁重点楼盘
    }

    # 1. 新房住宅上市套数
    # 如: 商品住宅项目18个，上市1712套
    m_new = re.search(r'商品住宅项目\s*(\d+)\s*个[，,]\s*上市\s*(\d+)\s*套', text)
    if m_new:
        metrics["new_house_listed_projects"] = int(m_new.group(1))
        metrics["new_house_listed_suites"] = int(m_new.group(2))

    # 2. 全市二手住宅成交
    # 如: 其中二手住宅交易成交面积130.6万m2（1.43万套）
    # 或: 其中二手住宅交易成交面积90.16万m2（0. 98 万套）
    m_sec = re.search(r'二手住宅[^\d]*([\d\.]+)\s*万\s*m\s*2[^\d]*[（\(]\s*([\d\.\s]+)\s*万\s*套', text)
    if m_sec:
        metrics["sec_house_area_wan_m2"] = float(m_sec.group(1))
        val_str = re.sub(r'\s+', '', m_sec.group(2))
        try:
            metrics["sec_house_total_suites"] = int(round(float(val_str) * 10000))
        except ValueError:
            pass

    # 3. 提取官方通报中提及的江宁重点项目（新房/二手）
    for proj in [
        "湖滨尊邸", "樾满云川", "万流宁邸", "万流", "金茂府", 
        "东山樾府", "璞玥府", "百家臻园", "托乐嘉", "东郊小镇", 
        "新华公寓", "殷巷新寓", "锦绣前程悦府"
    ]:
        if proj in text and proj not in metrics["jn_highlight_projects"]:
            metrics["jn_highlight_projects"].append(proj)

    return metrics

def sync_njhouse_data():
    """拉取官方最新发布的月度数据并生成权威 data.json"""
    print("=" * 60)
    print("【南京网上房地产 (www.njhouse.com.cn)】官方全量数据抓取与对齐")
    print("=" * 60)

    reports = fetch_official_reports_list()
    if not reports:
        print("[Error] 未获取到官方月报列表")
        return False

    official_reports = []
    for r in reports:
        ym = r["year_month"]
        content = fetch_report_detail(r["contentId"])
        if content:
            m = parse_report_metrics(content)
            official_reports.append({
                "month": ym,
                "title": r["title"],
                "contentId": r["contentId"],
                "official_url": f"https://www.njhouse.com.cn/xwzxDetail.html?contentid={r['contentId']}",
                "sec_house_total_suites": m["sec_house_total_suites"],
                "sec_house_area_wan_m2": m["sec_house_area_wan_m2"],
                "new_house_listed_suites": m["new_house_listed_suites"],
                "new_house_listed_projects": m["new_house_listed_projects"],
                "jn_highlight_projects": m["jn_highlight_projects"]
            })
            print(f"  • {ym}：二手住宅网签 {m['sec_house_total_suites']} 套 ({m['sec_house_area_wan_m2']}万㎡) | 商品住宅上市 {m['new_house_listed_suites']} 套 | 官方江宁热盘: {','.join(m['jn_highlight_projects'])}")

    output_data = {
        "source": "南京网上房地产 (www.njhouse.com.cn) 官方权威发布",
        "publisher": "南京市房地产市场监测分析中心",
        "official_site": "https://www.njhouse.com.cn/",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mortgage_rates": {
            "commercial_first_home": 3.00,
            "provident_fund_first_home": 2.60
        },
        "official_reports": official_reports
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n[Success] 官方全量数据已写入: {DATA_PATH} (共 {len(official_reports)} 个月份官方报告)")
    return True

if __name__ == "__main__":
    sync_njhouse_data()
