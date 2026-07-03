# 帧提取工具 (Frame Extraction Tool)

从视频文件中提取帧的 Python CLI 工具。

## 功能

- 🎬 **提取所有帧** — 导出视频的每一帧
- ⏱️ **按时间间隔提取** — 每隔 N 秒提取一帧
- 🔢 **按帧数间隔提取** — 每隔 N 帧提取一帧
- 🔍 **关键帧检测** — 基于场景变化自动检测并提取关键帧
- 📁 **多种输出格式** — 支持 JPG / PNG
- ⚙️ **灵活配置** — 可调节输出质量、帧数上限等

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
# 提取所有帧
python -m frame_extractor video.mp4 --all

# 每隔 5 秒提取一帧
python -m frame_extractor video.mp4 --every-sec 5

# 每隔 30 帧提取一帧
python -m frame_extractor video.mp4 --every-frame 30

# 使用场景检测提取关键帧（阈值越低越敏感）
python -m frame_extractor video.mp4 --keyframes --threshold 0.3

# 提取所有帧，限制最多 100 张，输出到 screenshots/
python -m frame_extractor video.mp4 --all --max-frames 100 --output-dir screenshots

# 输出为 PNG 格式
python -m frame_extractor video.mp4 --every-sec 2 --format png
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `video` | 视频文件路径 | (必填) |
| `--all` | 提取所有帧 (默认模式) | - |
| `--every-sec SEC` | 每隔 N 秒提取一帧 | - |
| `--every-frame N` | 每隔 N 帧提取一帧 | - |
| `--keyframes` | 场景检测提取关键帧 | - |
| `--threshold N` | 关键帧检测阈值 | 0.5 |
| `--output-dir DIR` | 输出目录 | ./frames |
| `--format {jpg,png}` | 输出格式 | jpg |
| `--quality N` | JPEG 质量 (1-100) | 95 |
| `--max-frames N` | 最大提取帧数 | 无限制 |

## 作为 Python 库使用

```python
from frame_extractor import FrameExtractor

with FrameExtractor("video.mp4", output_dir="frames", fmt="jpg") as e:
    print(f"帧率: {e.fps:.2f}")
    print(f"总帧数: {e.total_frames}")

    # 提取所有帧
    files = e.extract_all(max_frames=100)

    # 按时间提取
    files = e.extract_by_interval_sec(seconds=5)

    # 按帧数提取
    files = e.extract_by_interval_frame(interval=30)

    # 关键帧提取
    files = e.extract_keyframes(threshold=30.0)
```

## 运行测试

```bash
pip install pytest
pytest tests/
```

## 项目结构

```
frame-extraction-tool/
├── README.md
├── requirements.txt
├── .gitignore
├── frame_extractor/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   └── extractor.py
└── tests/
    └── test_extractor.py
```

## 许可

MIT License
