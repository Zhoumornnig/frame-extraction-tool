"""FrameExtractor 单元测试."""

import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from frame_extractor import FrameExtractor


def _create_test_video(
    filepath: str,
    num_frames: int = 30,
    fps: float = 10.0,
    width: int = 320,
    height: int = 240,
) -> str:
    """创建一个测试用的 MP4 视频.

    生成交替的纯色帧来模拟"场景切换"。
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

    for i in range(num_frames):
        # 每 5 帧切换一次颜色，模拟场景变化
        if (i // 5) % 2 == 0:
            color = (0, 0, 255)  # 红色
        else:
            color = (0, 255, 0)  # 绿色

        frame = np.full((height, width, 3), color, dtype=np.uint8)
        writer.write(frame)

    writer.release()
    return filepath


class TestFrameExtractor:
    """FrameExtractor 测试."""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录."""
        d = tempfile.mkdtemp()
        yield d
        shutil.rmtree(d, ignore_errors=True)

    @pytest.fixture
    def test_video(self, temp_dir):
        """创建测试视频."""
        path = os.path.join(temp_dir, "test.mp4")
        return _create_test_video(path)

    def test_init_file_not_found(self):
        """测试视频文件不存在时抛出异常."""
        with pytest.raises(FileNotFoundError):
            FrameExtractor("nonexistent.mp4")

    def test_init_invalid_format(self, test_video):
        """测试不支持的格式抛出异常."""
        with pytest.raises(ValueError):
            FrameExtractor(test_video, fmt="bmp")

    def test_video_properties(self, test_video):
        """测试视频属性读取."""
        with FrameExtractor(test_video) as e:
            assert e.fps == 10.0
            assert e.total_frames == 30
            assert e.duration == pytest.approx(3.0, rel=0.1)

    def test_extract_all(self, test_video, temp_dir):
        """测试提取所有帧."""
        out = os.path.join(temp_dir, "all_frames")
        with FrameExtractor(test_video, output_dir=out) as e:
            files = e.extract_all()

        assert len(files) == 30
        for f in files:
            assert os.path.isfile(f)

    def test_extract_all_with_max_frames(self, test_video, temp_dir):
        """测试 max_frames 限制."""
        out = os.path.join(temp_dir, "limited")
        with FrameExtractor(test_video, output_dir=out) as e:
            files = e.extract_all(max_frames=10)

        assert len(files) == 10

    def test_extract_by_interval_sec(self, test_video, temp_dir):
        """测试按时间间隔提取."""
        out = os.path.join(temp_dir, "by_sec")
        with FrameExtractor(test_video, output_dir=out) as e:
            files = e.extract_by_interval_sec(seconds=1.0)

        # 10fps, 每1秒 → 每10帧一张 → 30帧应有3张
        assert len(files) == 3

    def test_extract_by_interval_frame(self, test_video, temp_dir):
        """测试按帧数间隔提取."""
        out = os.path.join(temp_dir, "by_frame")
        with FrameExtractor(test_video, output_dir=out) as e:
            files = e.extract_by_interval_frame(interval=10)

        # 每10帧一张 → 30帧应有3张 (0, 10, 20)
        assert len(files) == 3

    def test_extract_keyframes(self, test_video, temp_dir):
        """测试关键帧提取."""
        out = os.path.join(temp_dir, "keyframes")
        with FrameExtractor(test_video, output_dir=out) as e:
            files = e.extract_keyframes(threshold=0.3)

        # 至少应该有第一帧 + 场景切换帧
        assert len(files) >= 2
        for f in files:
            assert os.path.isfile(f)

    def test_extract_keyframes_high_threshold(self, test_video, temp_dir):
        """测试高阈值下只提取少量关键帧."""
        out = os.path.join(temp_dir, "keyframes_high")
        with FrameExtractor(test_video, output_dir=out) as e:
            files = e.extract_keyframes(threshold=1e9)

        # 阈值极高，应该只有第一帧
        assert len(files) == 1

    def test_output_format_png(self, test_video, temp_dir):
        """测试 PNG 输出格式."""
        out = os.path.join(temp_dir, "png_out")
        with FrameExtractor(test_video, output_dir=out, fmt="png") as e:
            files = e.extract_all(max_frames=3)

        assert len(files) == 3
        for f in files:
            assert f.endswith(".png")

    def test_context_manager(self, test_video):
        """测试上下文管理器."""
        with FrameExtractor(test_video) as e:
            assert e.cap.isOpened()
        # 退出后应已释放
        assert e._cap is None
