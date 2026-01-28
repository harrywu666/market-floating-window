# 市场行情浮动窗口

一个优雅的桌面浮动窗口应用，实时显示黄金、白银和加密货币的最新价格。

![Market Floating Window](resources/ui/assets/app_icon.png)

## ✨ 功能特性

- 📊 **实时数据更新**：自动获取黄金、白银和多种加密货币价格（BTC, ETH, BNB, SOL, HYPE）
- 🌍 **国内外双价格**：同时显示国际价格和国内价格
- 🔄 **无缝推演**：国内休市期间基于国际盘面智能推演国内价格
- 📌 **窗口置顶**：支持窗口置顶功能，方便随时查看
- 🎨 **毛玻璃UI**：现代化半透明界面设计
- 🖱️ **自由拖动**：可拖动到屏幕任意位置
- 🌓 **透明度调节**：支持窗口透明度自定义
- 🎯 **灵活筛选**：可自由显示/隐藏各个版块和币种
- 💻 **系统托盘**：最小化到系统托盘，不占用任务栏

## 📋 系统要求

- macOS 10.14+ / Windows 10+ / Linux
- Python 3.8+
- 网络连接（用于数据获取）

## 🚀 快速开始

### 安装依赖

```bash
# 使用提供的安装脚本（macOS）
./scripts/setup.command

# 或手动安装
pip install -r requirements.txt
```

### 运行程序

```bash
# 使用启动脚本（macOS）
./scripts/run_mac.command

# 或使用Python直接运行
python -m src.main
```

## 📦 打包分发

### macOS用户

在 `scripts/build/` 目录下提供了两个打包脚本：

1. **一键安装到本机(自己用).command**：创建适合自己使用的应用包
2. **构建完整安装包(发给朋友).command**：创建可分发的DMG安装包

详细打包流程请参考 [`docs/mac_packaging_workflow.md`](docs/mac_packaging_workflow.md)

## 🏗️ 项目结构

```
market-floating-window/
├── src/                        # 源代码
│   ├── core/                   # 核心功能模块
│   │   ├── config.py          # 应用配置
│   │   └── data_fetcher.py    # 数据抓取
│   ├── ui/                     # UI模块
│   │   ├── window.py          # 主窗口
│   │   ├── menu.py            # 右键菜单
│   │   └── tray.py            # 系统托盘
│   ├── workers/                # 异步工作线程
│   │   └── fetch_worker.py    # 数据抓取工作线程
│   └── main.py                # 应用入口
├── resources/                  # 资源文件
│   ├── ui/                    # Web UI资源
│   │   ├── index.html
│   │   ├── style.css
│   │   └── assets/           # 图标等资源
│   └── redesign/             # UI重设计方案
├── scripts/                   # 脚本工具
│   ├── setup.command         # 安装脚本
│   ├── run_mac.command       # 运行脚本
│   ├── build/                # 打包脚本
│   └── utils/                # 工具脚本
├── docs/                      # 文档
└── tests/                     # 测试（待实现）
```

## 🎮 使用说明

### 基本操作

- **拖动窗口**：鼠标左键点击窗口任意位置拖动
- **打开菜单**：鼠标右键点击窗口
- **置顶窗口**：通过右键菜单或UI按钮切换
- **调节透明度**：右键菜单 → 透明度滑块

### 菜单功能

- **显示/隐藏版块**：控制黄金、白银、加密货币版块的显示
- **加密货币筛选**：单独控制每个币种的显示
- **立即刷新数据**：手动触发数据更新
- **透明度调节**：20%-100%范围调节
- **完全退出程序**：关闭应用

### 数据源

- **黄金/白银价格**：新浪财经API（国际）+ 东方财富API（国内）
- **加密货币价格**：OKX交易所API
- **汇率数据**：新浪财经API

## ⚙️ 配置

主要配置项在 `src/core/config.py` 中，可以调整：

- 窗口大小和透明度
- 数据更新频率
- 支持的加密货币列表
- API地址等

## 🔧 开发指南

### 代码架构

项目采用分层架构设计：

1. **核心层（core）**：数据获取和应用配置
2. **UI层（ui）**：窗口、菜单、托盘等界面组件
3. **工作层（workers）**：异步任务处理

### 添加新的加密货币

在 `src/core/config.py` 中修改：

```python
CRYPTO_SYMBOLS = {
    "BTC": "BTCUSDT",
    "YOUR_COIN": "YOUR_COIN_USDT",  # 添加新币种
}

CRYPTO_ORDER = ['BTC', 'ETH', 'YOUR_COIN']  # 调整显示顺序
```

### 自定义UI

UI文件位于 `resources/ui/` 目录：
- `index.html`：HTML结构
- `style.css`：样式定义

## 📝 依赖项

- **PySide6**：Qt界面框架
- **requests**：HTTP请求库
- **urllib3**：URL处理
- **certifi**：SSL证书

## 🐛 常见问题

### Q: 数据不更新？
A: 检查网络连接，确认防火墙未阻止程序访问网络。

### Q: macOS提示"无法打开，因为它来自身份不明的开发者"？
A: 右键点击应用图标，选择"打开"，或在系统偏好设置中允许该应用运行。

### Q: 窗口无法置顶？
A: 某些系统安全设置可能限制窗口置顶功能，请检查系统权限设置。

## 📄 许可证

本项目仅供个人学习和使用。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题或建议，请通过GitHub Issues联系。

---

**享受实时市场行情监控！** 📈
