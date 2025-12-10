# Converter
A small format utility for macOS

Includes:

- Video format conversion
- Video track selection, addition, and repackaging
- Audio track extraction
- And more

Supports most mainstream formats.

## Usage

### 1. Install using the zip

- Download the `.zip` file
- Unzip the archive
- Move the extracted folder's `Converter.app` into the Mac `Applications` folder

### 2. Install dependencies (optional)

If you run into problems you can try installing dependencies, but in most cases this is not necessary — newer releases bundle `ffmpeg` and `ffprobe`.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install ffmpeg
ffmpeg -version
```
