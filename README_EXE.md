# 黄金价格爬虫 - Windows 可执行文件编译说明

## 方案一：在 macOS 上编译（使用 Wine + PyInstaller）

### 步骤：

1. **安装 Homebrew**（如果未安装）
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **安装 Wine**
   ```bash
   brew install --cask wine-stable
   ```

3. **运行编译脚本**
   ```bash
   chmod +x build_windows_exe.sh
   ./build_windows_exe.sh
   ```

4. **获取 .exe 文件**
   编译完成后，.exe 文件位于 `dist/GoldPriceCrawler.exe`

---

## 方案二：使用 GitHub Actions 自动编译（推荐，更简单）

### 步骤：

1. **创建 GitHub 仓库**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   gh repo create gold-price-crawler --public --source=.
   git push -u origin main
   ```

2. **创建 Actions 配置文件**
   创建 `.github/workflows/build.yml`：
   ```yaml
   name: Build Windows EXE

   on:
     push:
       tags:
         - 'v*'
     workflow_dispatch:

   jobs:
     build:
       runs-on: windows-latest
       steps:
         - uses: actions/checkout@v3

         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.12'

         - name: Install dependencies
           run: |
             pip install pyinstaller
             pip install -r requirements.txt

         - name: Build EXE
           run: |
             pyinstaller --onefile --windowed --name="GoldPriceCrawler" gold_price_crawler.py

         - name: Upload artifact
           uses: actions/upload-artifact@v3
           with:
             name: GoldPriceCrawler-Windows
             path: dist/GoldPriceCrawler.exe
   ```

3. **触发编译**
   - 推送标签触发：`git tag v1.0.0 && git push origin v1.0.0`
   - 或在 GitHub 网页上手动触发 Actions

4. **下载 .exe 文件**
   在 GitHub Actions 页面下载构建好的 .exe 文件

---

## 方案三：使用 Docker + Wine

### 步骤：

1. **创建 Dockerfile**
   ```dockerfile
   FROM ubuntu:22.04

   RUN apt-get update && apt-get install -y \
       wine64 \
       python3 \
       curl \
       && rm -rf /var/lib/apt/lists/*

   WORKDIR /app
   COPY requirements.txt .
   COPY gold_price_crawler.py .

   RUN python3 -m pip install pyinstaller
   RUN python3 -m pip install -r requirements.txt

   RUN pyinstaller --onefile --windowed --name="GoldPriceCrawler" gold_price_crawler.py
   ```

2. **构建镜像**
   ```bash
   docker build -t gold-crawler .
   ```

3. **提取 .exe 文件**
   ```bash
   docker run --rm -v $(pwd):/output gold-crawler cp dist/GoldPriceCrawler.exe /output/
   ```

---

## 给 Windows 用户的说明

### 使用方法：

1. 下载 `GoldPriceCrawler.exe` 文件
2. 双击运行（无需安装 Python）
3. 程序会在同目录下生成 Excel 文件

### 注意事项：

- 首次运行可能需要网络连接下载黄金价格数据
- Windows 10/11 需要允许程序运行（系统可能提示"未知发行者"）
- 确保系统防火墙允许程序访问网络

### 如果遇到问题：

- 杀毒软件可能误报，请添加到白名单
- 提示缺少 DLL 文件：尝试以管理员身份运行
- 程序闪退：在命令行运行查看错误信息

---

## 推荐：方案二（GitHub Actions）

**为什么推荐方案二？**
- ✅ 无需在 Mac 上安装 Wine
- ✅ 使用真实的 Windows 环境编译，兼容性更好
- ✅ 可以自动化构建和发布
- ✅ GitHub 免费提供 Windows 环境
- ✅ 构建速度快，可重复使用

---

## 测试 .exe 文件

在 Mac 上可以使用 Wine 测试 .exe 文件：
```bash
wine dist/GoldPriceCrawler.exe
```
