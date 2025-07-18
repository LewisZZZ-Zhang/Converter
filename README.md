# Converter
Mac用格式小工具  
包括：

- 视频格式转换
- 视频轨道选择、增加、重新打包
- 音轨提取
- 等

支持大部分主流格式  

## 使用方法

### 1. 使用 zip 安装

- 下载 `.zip` 文件  
- 解压 `.zip`  
- 将解压出来的文件夹中的 `Converter.app` 移动到 Mac 的 `Application` 文件夹

### 2. 安装依赖（如果有问题可以尝试）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install ffmpeg
ffmpeg -version
