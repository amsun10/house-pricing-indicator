#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open("data.json", "r", encoding="utf-8") as f:
    d = json.load(f)

with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()

idx1 = html.find("const DEFAULT_HOUSING_DATA =")
idx2 = html.find("let activeRegionKey =", idx1)

if idx1 == -1 or idx2 == -1:
    print("[Error] markers not found in index.html")
    exit(1)

new_block = (
    "const DEFAULT_HOUSING_DATA = " + json.dumps(d, ensure_ascii=False, indent=2) + ";\n\n"
    "    let currentData = DEFAULT_HOUSING_DATA;\n"
    "    try {\n"
    "      const cached = localStorage.getItem('nj_housing_data');\n"
    "      if (cached) {\n"
    "        const parsed = JSON.parse(cached);\n"
    "        if (parsed.months && parsed.months.length >= DEFAULT_HOUSING_DATA.months.length) {\n"
    "          currentData = parsed;\n"
    "        } else {\n"
    "          localStorage.setItem('nj_housing_data', JSON.stringify(DEFAULT_HOUSING_DATA));\n"
    "        }\n"
    "      }\n"
    "    } catch(e) {\n"
    "      currentData = DEFAULT_HOUSING_DATA;\n"
    "    }\n\n    "
)

updated_html = html[:idx1] + new_block + html[idx2:]
with open("index.html", "w", encoding="utf-8") as f:
    f.write(updated_html)

print("成功将连续 45 个月（2023-01 至 2026-09）的数据注入 index.html！")
