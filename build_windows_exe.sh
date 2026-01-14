#!/bin/bash
# 在 macOS 上使用 PyInstaller + Wine 编译 Windows .exe 文件

set -e

echo "========================================="
echo "黄金价格爬虫 - Windows .exe 编译脚本"
echo "========================================="

# 1. 检查并安装 Wine
if ! command -v wine &> /dev/null; then
    echo "Wine 未安装，正在安装..."
    if command -v brew &> /dev/null; then
        brew install --cask wine-stable
    else
        echo "请先安装 Homebrew: https://brew.sh"
        exit 1
    fi
fi

# 2. 安装 Windows 版 Python（通过 Wine）
echo "正在检查 Windows Python..."
if [ ! -f ~/.wine/drive_c/Python312/python.exe ]; then
    echo "正在安装 Windows 版 Python 3.12..."
    mkdir -p ~/tmp/python_installer
    cd ~/tmp/python_installer
    curl -L -o python-installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
    wine python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 TargetDir=C:\Python312
    cd -
    rm -rf ~/tmp/python_installer
fi

# 3. 设置 Wine Python 路径
export PATH="$HOME/.wine/drive_c/Python312:$HOME/.wine/drive_c/Python312/Scripts:$PATH"

# 4. 安装 Windows 版依赖
echo "正在安装 Windows 版依赖..."
wine C:\\Python312\\python.exe -m pip install --upgrade pip
wine C:\\Python312\\python.exe -m pip install pyinstaller requests beautifulsoup4 pandas openpyxl lxml

# 5. 编译 .exe 文件
echo "正在编译 .exe 文件..."
wine C:\\Python312\\Scripts\\pyinstaller.exe \
    --onefile \
    --windowed \
    --name="GoldPriceCrawler" \
    --icon=none \
    gold_price_crawler.py

echo "========================================="
echo "编译完成！"
echo "可执行文件位置: dist/GoldPriceCrawler.exe"
echo "========================================="
