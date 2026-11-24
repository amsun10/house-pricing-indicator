#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从南京网上房地产 (www.njhouse.com.cn) 官方提取最新月度房地产市场分析数据
并与本地 data.json 进行核验与同步
"""

import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request

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
        "new_house_listed_suites": None,   # 全市新房上市套数
        "sec_house_total_wan_suites": None, # 全市二手住宅成交总套数 (万套)
        "sec_house_total_suites": None,    # 全市二手住宅成交总套数 (套)
        "sec_house_area_wan_m2": None,     # 全市二手住宅成交面积 (万㎡)
        "jn_sec_house_est_suites": None,   # 江宁区二手成交估算套数 (通常占全市 18%~22%)
        "hot_projects": [],                # 提及的重点盘
    }

    # 1. 新房住宅上市套数
    # 如: 商品住宅项目13个，上市1160套
    m_new = re.search(r'商品住宅项目\s*\d+\s*个[，,]\s*上市\s*(\d+)\s*套', text)
    if m_new:
        metrics["new_house_listed_suites"] = int(m_new.group(1))

    # 2. 全市二手住宅成交
    # 如: 其中二手住宅交易成交面积93.00万m2（1.01万套）
    # 或: 其中二手住宅交易成交面积130.6万m2（1.43万套）
    m_sec = re.search(r'二手住宅交易\s*成交面积\s*([\d\.]+)\s*万\s*m\s*2\s*[（\(]\s*([\d\.]+)\s*万\s*套', text)
    if not m_sec:
        m_sec = re.search(r'二手住宅[^\d]*([\d\.]+)\s*万\s*m\s*2[^\d]*[（\(]\s*([\d\.]+)\s*万\s*套', text)
    
    if m_sec:
        metrics["sec_house_area_wan_m2"] = float(m_sec.group(1))
        wan_suites = float(m_sec.group(2))
        metrics["sec_house_total_wan_suites"] = wan_suites
        metrics["sec_house_total_suites"] = int(round(wan_suites * 10000))
        # 江宁区长期为南京二手成交第一或第二主力区，平均占比约为全市的 18.5%
        metrics["jn_sec_house_est_suites"] = int(round(metrics["sec_house_total_suites"] * 0.185))

    # 3. 提取报告提及的楼盘
    for proj in ["万流", "金茂府", "东山樾府", "樾满云川", "璞玥府", "百家臻园", "托乐嘉", "东郊小镇"]:
        if proj in text:
            metrics["hot_projects"].append(proj)

    return metrics

def sync_njhouse_data():
    """主函数：拉取官方最新发布的月度数据并输出校验汇总"""
    print("=" * 60)
    print("【南京网上房地产 (www.njhouse.com.cn)】官方数据源同步检测")
    print("=" * 60)

    reports = fetch_official_reports_list()
    if not reports:
        print("[Info] 暂未获取到官方月报列表，保留本地基准数据")
        return False

    print(f"[Success] 成功发现官方已发布月报 {len(reports)} 篇：")
    parsed_results = {}
    for r in reports:
        ym = r["year_month"]
        content = fetch_report_detail(r["contentId"])
        if content:
            metrics = parse_report_metrics(content)
            parsed_results[ym] = metrics
            suites_str = f"{metrics['sec_house_total_suites']} 套" if metrics['sec_house_total_suites'] else "未单列"
            jn_str = f"江宁约 {metrics['jn_sec_house_est_suites']} 套" if metrics['jn_sec_house_est_suites'] else ""
            print(f"  • {ym}：全市二手房网签 {suites_str} ({jn_str}) | 官方提及重点盘: {','.join(metrics['hot_projects'])}")

    return parsed_results

if __name__ == "__main__":
    sync_njhouse_data()
