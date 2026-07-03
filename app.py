"""帧提取工具 — Web 可视化界面.

启动方式:
    python app.py
    浏览器自动打开 http://localhost:7860
"""

import os
import tempfile
from pathlib import Path

import gradio as gr

from frame_extractor import FrameExtractor

# 主题色
THEME = gr.themes.Soft(
    primary_hue="orange",
    secondary_hue="gray",
)


def extract_frames(
    video_file: str | None,
    mode: str,
    interval_sec: float,
    interval_frame: int,
    threshold: float,
    output_format: str,
    quality: int,
    max_frames: int,
) -> tuple[list[str], str, str]:
    """处理视频并提取帧.

    Returns:
        (图片路径列表, 视频信息文本, 输出目录)
    """
    if video_file is None:
        return [], "⚠️ 请先上传视频文件", ""

    video_path = str(Path(video_file).resolve())

    # 输出到临时目录
    output_dir = tempfile.mkdtemp(prefix="frame_extractor_")

    try:
        with FrameExtractor(video_path, output_dir=output_dir,
                            fmt=output_format, quality=quality) as e:
            # 视频信息
            info_lines = [
                f"📹 **视频信息**",
                f"",
                f"| 属性 | 值 |",
                f"|------|-----|",
                f"| 帧率 | {e.fps:.2f} fps |",
                f"| 总帧数 | {e.total_frames} |",
                f"| 时长 | {e.duration:.2f} 秒 |",
                f"| 分辨率 | {int(e.cap.get(3))}×{int(e.cap.get(4))} |",
            ]

            # 按模式提取
            if mode == "按时间间隔":
                info_lines.append(f"| 模式 | 每隔 {interval_sec} 秒 |")
                files = e.extract_by_interval_sec(interval_sec, max_frames)
            elif mode == "按帧数间隔":
                info_lines.append(f"| 模式 | 每隔 {interval_frame} 帧 |")
                files = e.extract_by_interval_frame(interval_frame, max_frames)
            elif mode == "关键帧检测":
                info_lines.append(f"| 模式 | 关键帧检测 (阈值={threshold}) |")
                files = e.extract_keyframes(threshold, max_frames)
            else:  # 提取所有帧
                limit = f" (最多{max_frames}帧)" if max_frames > 0 else ""
                info_lines.append(f"| 模式 | 提取所有帧{limit} |")
                files = e.extract_all(max_frames)

            info_lines.append(f"| 提取帧数 | **{len(files)}** |")
            info = "\n".join(info_lines)

            return files, info, output_dir

    except Exception as exc:
        return [], f"❌ 错误: {exc}", ""


def build_ui() -> gr.Blocks:
    """构建 Gradio 界面."""
    with gr.Blocks(title="帧提取工具") as demo:
        gr.Markdown(
            "# 🎬 帧提取工具\n"
            "从视频文件中提取帧 — 支持均匀间隔、关键帧检测等多种模式"
        )

        with gr.Row(equal_height=False):
            # ===== 左侧：控制面板 =====
            with gr.Column(scale=1, min_width=320):
                gr.Markdown("### 📹 视频")

                video_input = gr.Video(
                    label="上传视频文件",
                    sources=["upload"],
                    height=200,
                )

                gr.Markdown("### 🎯 提取模式")

                mode_radio = gr.Radio(
                    choices=["提取所有帧", "按时间间隔", "按帧数间隔", "关键帧检测"],
                    value="关键帧检测",
                    label="选择提取模式",
                )

                gr.Markdown("### ⚙️ 参数")

                with gr.Column(visible=False) as sec_panel:
                    interval_sec = gr.Slider(
                        0.1, 60.0, value=1.0, step=0.1,
                        label="时间间隔 (秒)",
                    )

                with gr.Column(visible=False) as frame_panel:
                    interval_frame = gr.Slider(
                        1, 300, value=30, step=1,
                        label="帧数间隔",
                    )

                with gr.Column(visible=True) as kf_panel:
                    threshold = gr.Slider(
                        0.0, 5.0, value=0.5, step=0.05,
                        label="关键帧检测阈值 (越小越敏感)",
                    )

                output_format = gr.Radio(
                    choices=["jpg", "png"],
                    value="jpg",
                    label="输出格式",
                )

                quality = gr.Slider(
                    10, 100, value=95, step=5,
                    label="JPEG 质量",
                )

                max_frames = gr.Slider(
                    0, 500, value=100, step=10,
                    label="最大帧数 (0=不限制)",
                )

                extract_btn = gr.Button("🚀 开始提取", variant="primary", size="lg")

            # ===== 右侧：结果面板 =====
            with gr.Column(scale=2, min_width=480):
                video_info = gr.Markdown("📊 等待上传视频...")

                gr.Markdown("### 🖼️ 提取结果")

                gallery = gr.Gallery(
                    label="提取的帧",
                    columns=4,
                    rows=2,
                    height=400,
                    object_fit="contain",
                )

                with gr.Row():
                    output_dir_text = gr.Textbox(
                        label="输出目录",
                        interactive=False,
                        scale=3,
                    )
                    open_btn = gr.Button("📁 打开文件夹", scale=1)

        # ===== 模式切换逻辑 =====
        def on_mode_change(mode: str):
            return (
                gr.update(visible=(mode == "按时间间隔")),   # sec_panel
                gr.update(visible=(mode == "按帧数间隔")),   # frame_panel
                gr.update(visible=(mode == "关键帧检测")),   # kf_panel
            )

        mode_radio.change(
            on_mode_change,
            inputs=[mode_radio],
            outputs=[sec_panel, frame_panel, kf_panel],
        )

        # ===== 提取按钮 =====
        extract_btn.click(
            extract_frames,
            inputs=[
                video_input,
                mode_radio,
                interval_sec,
                interval_frame,
                threshold,
                output_format,
                quality,
                max_frames,
            ],
            outputs=[gallery, video_info, output_dir_text],
        )

        # ===== 打开文件夹按钮 =====
        open_btn.click(
            lambda d: os.startfile(d) if d and os.path.isdir(d) else None,
            inputs=[output_dir_text],
            outputs=[],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        theme=THEME,
        inbrowser=True,
        show_error=True,
    )
