"""视频帧提取核心逻辑."""

import os
from pathlib import Path

import cv2
import numpy as np


class FrameExtractor:
    """从视频文件中提取帧。

    支持四种提取模式：
    - 提取所有帧
    - 按时间间隔提取
    - 按帧数间隔提取
    - 基于场景检测提取关键帧
    """

    def __init__(
        self,
        video_path: str,
        output_dir: str = "./frames",
        fmt: str = "jpg",
        quality: int = 95,
    ):
        """初始化提取器。

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            fmt: 输出格式 (jpg / png)
            quality: JPEG 质量 (1-100), PNG 忽略此参数
        """
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        self.output_dir = Path(output_dir)
        self.fmt = fmt.lower()
        if self.fmt not in ("jpg", "jpeg", "png"):
            raise ValueError(f"不支持的格式: {fmt}，仅支持 jpg / png")

        self.quality = max(1, min(100, quality))
        self._cap: cv2.VideoCapture | None = None

    @property
    def cap(self) -> cv2.VideoCapture:
        """延迟初始化 VideoCapture."""
        if self._cap is None:
            self._cap = cv2.VideoCapture(str(self.video_path))
            if not self._cap.isOpened():
                raise RuntimeError(f"无法打开视频文件: {self.video_path}")
        return self._cap

    @property
    def fps(self) -> float:
        """视频帧率."""
        return self.cap.get(cv2.CAP_PROP_FPS)

    @property
    def total_frames(self) -> int:
        """视频总帧数."""
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    @property
    def duration(self) -> float:
        """视频时长 (秒)."""
        total = self.total_frames
        fps = self.fps
        return total / fps if fps > 0 else 0.0

    def _ensure_output_dir(self) -> None:
        """确保输出目录存在."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_output_path(self, frame_index: int) -> str:
        """生成输出文件路径."""
        ext = "jpg" if self.fmt in ("jpg", "jpeg") else "png"
        return str(self.output_dir / f"frame_{frame_index:06d}.{ext}")

    def _write_frame(self, frame: np.ndarray, filepath: str) -> bool:
        """写入单帧图片.

        使用 imencode + 原生文件写入，以支持中文路径。

        Returns:
            True 表示写入成功
        """
        try:
            ext = "jpg" if self.fmt in ("jpg", "jpeg") else "png"
            params = []
            if self.fmt in ("jpg", "jpeg"):
                params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            elif self.fmt == "png":
                params = [cv2.IMWRITE_PNG_COMPRESSION, 3]

            success, buf = cv2.imencode(f".{ext}", frame, params)
            if not success:
                return False

            with open(filepath, "wb") as f:
                f.write(buf.tobytes())
            return True
        except OSError:
            return False

    def _read_frame(self) -> tuple[bool, np.ndarray | None]:
        """读取一帧.

        Returns:
            (success, frame) — success 为 False 表示视频结束
        """
        ret, frame = self.cap.read()
        if not ret:
            return False, None
        return True, frame

    def extract_all(self, max_frames: int = 0) -> list[str]:
        """提取视频中所有帧.

        Args:
            max_frames: 最大帧数限制，0 表示无限制

        Returns:
            已保存的文件路径列表
        """
        self._ensure_output_dir()
        saved = []
        frame_idx = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            out_path = self._get_output_path(frame_idx)
            if self._write_frame(frame, out_path):
                saved.append(out_path)
                frame_idx += 1

            if max_frames > 0 and frame_idx >= max_frames:
                break

        return saved

    def extract_by_interval_sec(
        self, seconds: float, max_frames: int = 0
    ) -> list[str]:
        """每隔 N 秒提取一帧.

        Args:
            seconds: 时间间隔 (秒)
            max_frames: 最大帧数限制

        Returns:
            已保存的文件路径列表
        """
        self._ensure_output_dir()

        fps = self.fps
        if fps <= 0:
            raise RuntimeError("无法获取视频帧率")

        frame_interval = max(1, int(fps * seconds))
        return self.extract_by_interval_frame(frame_interval, max_frames)

    def extract_by_interval_frame(
        self, interval: int, max_frames: int = 0
    ) -> list[str]:
        """每隔 N 帧提取一帧.

        Args:
            interval: 帧数间隔
            max_frames: 最大帧数限制

        Returns:
            已保存的文件路径列表
        """
        self._ensure_output_dir()
        saved = []
        frame_idx = 0
        saved_count = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            if frame_idx % interval == 0:
                out_path = self._get_output_path(saved_count)
                if self._write_frame(frame, out_path):
                    saved.append(out_path)
                    saved_count += 1

                if max_frames > 0 and saved_count >= max_frames:
                    break

            frame_idx += 1

        return saved

    def extract_keyframes(
        self, threshold: float = 0.5, max_frames: int = 0
    ) -> list[str]:
        """基于场景检测提取关键帧.

        使用帧间 HSV 直方图的卡方距离来检测场景切换。
        当相邻帧的直方图差异超过阈值时，记录为关键帧。

        Args:
            threshold: 检测阈值 (默认 30.0)，值越小越敏感
            max_frames: 最大帧数限制

        Returns:
            已保存的文件路径列表
        """
        self._ensure_output_dir()
        saved = []
        saved_count = 0
        last_hist: np.ndarray | None = None

        # 直方图参数
        h_bins, s_bins = 50, 60
        hist_size = [h_bins, s_bins]
        h_ranges = [0, 180]
        s_ranges = [0, 256]
        ranges = h_ranges + s_ranges
        channels = [0, 1]

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            # 转换到 HSV 并计算直方图
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist(
                [hsv], channels, None, hist_size, ranges
            )
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

            # 第一帧始终保留
            if last_hist is None:
                is_keyframe = True
            else:
                # 计算卡方距离
                dist = cv2.compareHist(last_hist, hist, cv2.HISTCMP_CHISQR)
                is_keyframe = dist > threshold

            if is_keyframe:
                out_path = self._get_output_path(saved_count)
                if self._write_frame(frame, out_path):
                    saved.append(out_path)
                    saved_count += 1
                    last_hist = hist

                if max_frames > 0 and saved_count >= max_frames:
                    break

        return saved

    def close(self) -> None:
        """释放视频资源."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        if hasattr(self, "_cap") and self._cap is not None:
            self._cap.release()
