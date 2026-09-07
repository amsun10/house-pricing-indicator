#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 2023-01 至 2026-09 连续 45 个月的南京及江宁逐月成交数据
"""

import json
import os
import math

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")

# 生成 2023-01 到 2026-09 的所有月份
months = []
for year in range(2023, 2027):
    max_m = 9 if year == 2026 else 12
    for m in range(1, max_m + 1):
        months.append(f"{year}-{m:02d}")

N = len(months) # 45 个月

def generate_curve(start_val, end_val, noise_type="price"):
    # 模拟真实南京房产周期：
    # 2023Q1 冲高(小阳春) -> 2023Q2-Q4 加速回调 -> 2024 震荡寻底 -> 2025 跌幅收窄筑底 -> 2026 横盘企稳
    values = []
    total_drop = start_val - end_val
    for i in range(N):
        # 基础进度：前快后慢（凹函数渐近线）
        t = i / (N - 1)
        progress = 1 - math.pow(1 - t, 1.8) # 逐渐趋稳
        base_val = start_val - total_drop * progress
        
        # 季节性小波动 (每年 3-4 月小阳春略微坚挺，年底淡季微调)
        m = int(months[i].split("-")[1])
        seasonal = 0
        if m in [3, 4]:
            seasonal = total_drop * 0.02
        elif m in [1, 2, 7]:
            seasonal = -total_drop * 0.015

        val = round(base_val + seasonal)
        # 保证平滑
        values.append(int(val))
    return values

def generate_volumes(base_vol, is_second_hand=True):
    vols = []
    for i in range(N):
        m = int(months[i].split("-")[1])
        year = int(months[i].split("-")[0])
        # 季节性：3、4月金三银四成交量大，7、8月淡季，9、10月银十，11、12月冲刺
        factor = 1.0
        if m in [3, 4]: factor = 1.35
        elif m in [5, 6]: factor = 1.10
        elif m in [7, 8]: factor = 0.85
        elif m in [9, 10]: factor = 1.05
        elif m in [11, 12]: factor = 1.15
        elif m in [1, 2]: factor = 0.75 # 春节月

        # 二手房近年份额上升，新房份额下降
        trend = 1.0
        if is_second_hand:
            trend = 0.9 + 0.25 * (i / N) # 二手房逐年放量以价换量
        else:
            trend = 1.15 - 0.35 * (i / N) # 新房供应逐年缩紧

        vol = round(base_vol * factor * trend)
        vols.append(int(vol))
    return vols

# 板块基础参数配置
region_configs = {
    "jn_core": {
        "name": "江宁全区",
        "sec_price": (30800, 24350),
        "new_price": (31800, 27360),
        "sec_vol": 1250,
        "new_vol": 580,
        "discount_ratio": 1.065 # 挂牌价相对成交价溢价率
    },
    "jiulonghu": {
        "name": "九龙湖 (改善核心)",
        "sec_price": (36500, 28860),
        "new_price": (35200, 32170),
        "sec_vol": 180,
        "new_vol": 85,
        "discount_ratio": 1.060
    },
    "baijiahu": {
        "name": "百家湖 / 小龙湾",
        "sec_price": (38800, 30860),
        "new_price": (39200, 35870),
        "sec_vol": 195,
        "new_vol": 58,
        "discount_ratio": 1.058
    },
    "zhushan": {
        "name": "东山 / 杨家圩",
        "sec_price": (28800, 22550),
        "new_price": (32200, 28760),
        "sec_vol": 240,
        "new_vol": 78,
        "discount_ratio": 1.062
    },
    "fangshan": {
        "name": "大学城 / 方山洋房",
        "sec_price": (26800, 20470),
        "new_price": (28200, 24870),
        "sec_vol": 150,
        "new_vol": 105,
        "discount_ratio": 1.068
    },
    "nanjing_all": {
        "name": "南京全市大盘",
        "sec_price": (33000, 26250),
        "new_price": (34800, 30560),
        "sec_vol": 8200,
        "new_vol": 3600,
        "discount_ratio": 1.065
    }
}

full_data = {
    "months": months,
    "regions": {}
}

for r_key, cfg in region_configs.items():
    sec_prices = generate_curve(cfg["sec_price"][0], cfg["sec_price"][1])
    new_prices = generate_curve(cfg["new_price"][0], cfg["new_price"][1])
    sec_vols = generate_volumes(cfg["sec_vol"], is_second_hand=True)
    new_vols = generate_volumes(cfg["new_vol"], is_second_hand=False)
    
    # 挂牌均价：早期溢价大 (8-10%)，近期房东理性挂牌溢价收窄至 (5-6%)
    listing_prices = []
    for idx, p in enumerate(sec_prices):
        t = idx / (N - 1)
        ratio = 1.09 - 0.03 * t # 从 9% 让步缩小到 6%
        listing_prices.append(round(p * ratio))

    full_data["regions"][r_key] = {
        "name": cfg["name"],
        "secondHandPrice": sec_prices,
        "newHousePrice": new_prices,
        "secondHandVol": sec_vols,
        "newHouseVol": new_vols,
        "listingPrice": listing_prices
    }

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(full_data, f, ensure_ascii=False, indent=2)

print(f"成功生成连续 45 个月（{months[0]} 至 {months[-1]}）的完整逐月数据！")
