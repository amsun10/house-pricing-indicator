# 张翔和葛秀的购房决策看板 (南京江宁 120-140㎡ 改善专版)

专为**张翔和葛秀**定制的南京（江宁核心板块）房产交易量价趋势与置业精算看板。
基于纯前端（Tailwind CSS + Apache ECharts）与 GitHub Actions 自动化工作流构建，**零服务器成本、免装环境、自动云端更新**。

---

## 🌟 核心特性

1. **江宁改善盘定制分析**：聚焦 **120-140㎡** 户型、**350-450万** 预算带（折合单价 2.50 ~ 3.50 万/㎡）；
2. **多板块下钻与横向对比**：一键切换江宁全区、九龙湖、百家湖、东山/杨家圩、大学城/方山及南京全市大盘；
3. **真实买方议价空间（砍价率）**：动态计算挂牌价与成交价差比，看房前评估房东谈判折让空间；
4. **精算工具**：内置 2026 最新南京商贷、公积金利率与契税新政（120-140㎡ 统一 1%）及前期现金储备建议；
5. **GitHub Actions 自动化流水线**：每周云端自动执行采集，同步最新月份行情，免人工维护。

---

## 🚀 极速上线指南（推送至 GitHub 并开启自动更新）

只需在本项目根目录下打开命令行（PowerShell 或 Git Bash），执行以下步骤：

### 第一步：初始化并推送到 GitHub 仓库

1. 在 GitHub 上新建一个仓库（例如命名为 `house-pricing-indicator`，可设为 Public）；
2. 在本地终端执行：
```bash
git init
git add .
git commit -m "feat: initial commit for Zhang Xiang & Ge Xiu housing indicator"
git branch -M main
git remote add origin https://github.com/<你的GitHub用户名>/house-pricing-indicator.git
git push -u origin main
```

---

### 第二步：开启免费的网页托管 (GitHub Pages)

推送完成后，让看板能够在手机和电脑浏览器中随时访问：
1. 进入 GitHub 仓库页面，点击右上角 **Settings**（设置）；
2. 在左侧菜单点击 **Pages**；
3. 在 **Build and deployment** 下方的 **Branch** 选择：
   * 分支选择：`main`
   * 目录选择：`/ (root)`
4. 点击 **Save** 保存。稍等 1~2 分钟，页面上方就会生成专属网址：
   `https://<你的GitHub用户名>.github.io/house-pricing-indicator/`
   👉 张翔和葛秀收藏该链接即可随时查看！

---

### 第三步：开启 GitHub Actions 自动提交权限 (关键设置)

为了让自动化脚本更新 `data.json` 后有权限推送到仓库：
1. 进入 GitHub 仓库页面的 **Settings**；
2. 左侧点击 **Actions** $\to$ **General**；
3. 翻到页面最下方的 **Workflow permissions**，勾选：
   * ✅ **Read and write permissions**（读写权限）
4. 点击 **Save** 保存。

---

## ⚙️ 自动化更新机制与手动测试

* **自动运行**：工作流配置在 `.github/workflows/update_data.yml` 中，**每周一凌晨 03:00（北京时间）** 自动在云端执行一次；
* **手动立即测试运行**：
  1. 进入 GitHub 仓库顶部的 **Actions** 标签页；
  2. 点击左侧的 **Auto Update Housing Data** 工作流；
  3. 点击右侧 **Run workflow** 按钮，几秒钟内即可在云端完成数据抓取与部署。
