"""命令行接口."""

import argparse
import sys

from .extractor import FrameExtractor


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器."""
    parser = argparse.ArgumentParser(
        prog="frame-extractor",
        description="从视频文件中提取帧",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python -m frame_extractor video.mp4 --all
  python -m frame_extractor video.mp4 --every-sec 5
  python -m frame_extractor video.mp4 --every-frame 30
  python -m frame_extractor video.mp4 --keyframes --threshold 25
  python -m frame_extractor video.mp4 --every-sec 2 --output-dir screenshots --format png
        """,
    )

    parser.add_argument(
        "video",
        help="视频文件路径",
    )

    # 提取模式（互斥）
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="提取所有帧 (默认模式)",
    )
    mode.add_argument(
        "--every-sec",
        type=float,
        metavar="SEC",
        help="每隔 N 秒提取一帧",
    )
    mode.add_argument(
        "--every-frame",
        type=int,
        metavar="N",
        help="每隔 N 帧提取一帧",
    )
    mode.add_argument(
        "--keyframes",
        action="store_true",
        help="使用场景检测提取关键帧",
    )

    # 关键帧参数
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="关键帧检测阈值，值越小越敏感 (默认: 0.5)",
    )

    # 输出参数
    parser.add_argument(
        "--output-dir",
        default="./frames",
        help="输出目录 (默认: ./frames)",
    )
    parser.add_argument(
        "--format",
        choices=["jpg", "png"],
        default="jpg",
        help="输出格式 (默认: jpg)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="JPEG 质量 1-100 (默认: 95)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        metavar="N",
        help="最大提取帧数限制 (默认: 无限制)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口.

    Returns:
        退出码 (0 成功, 1 失败)
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        extractor = FrameExtractor(
            video_path=args.video,
            output_dir=args.output_dir,
            fmt=args.format,
            quality=args.quality,
        )

        # 显示视频信息
        print(f"视频: {args.video}")
        print(f"帧率: {extractor.fps:.2f} fps")
        print(f"总帧数: {extractor.total_frames}")
        print(f"时长: {extractor.duration:.2f} 秒")
        print(f"输出目录: {args.output_dir}")
        print("-" * 40)

        # 按模式提取
        if args.every_sec is not None:
            print(f"模式: 每隔 {args.every_sec} 秒提取一帧")
            files = extractor.extract_by_interval_sec(
                args.every_sec, args.max_frames
            )
        elif args.every_frame is not None:
            print(f"模式: 每隔 {args.every_frame} 帧提取一帧")
            files = extractor.extract_by_interval_frame(
                args.every_frame, args.max_frames
            )
        elif args.keyframes:
            print(f"模式: 关键帧检测 (阈值={args.threshold})")
            files = extractor.extract_keyframes(
                args.threshold, args.max_frames
            )
        else:
            print("模式: 提取所有帧")
            files = extractor.extract_all(args.max_frames)

        print("-" * 40)
        print(f"完成! 共提取 {len(files)} 帧")

        if len(files) <= 10:
            for f in files:
                print(f"  {f}")
        else:
            print(f"  输出目录: {extractor.output_dir.resolve()}")

        extractor.close()
        return 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
