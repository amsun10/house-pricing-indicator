#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
南京房产数据自动化同步脚本 (针对购房决策看板)
从南京网上房地产 (www.njhouse.com.cn) 提取官方发布的最新月度真实成交指标同步至 data.json。
由 GitHub Actions 或本地定时触发执行。
绝不添加任何非官方臆造数据。
"""

import os
import sys
from fetch_njhouse_data import sync_njhouse_data

if __name__ == "__main__":
    success = sync_njhouse_data()
    if not success:
        print("[Error] 官方数据同步未能完成")
        sys.exit(1)
