"""Export and Benchmark Optimized CrowdSight YOLO Model (ONNX & TensorRT Engine).

Usage:
    python scripts/export_optimized_model.py --format onnx --half
    python scripts/export_optimized_model.py --benchmark
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    import torch
    from ultralytics import YOLO
except ImportError:
    print("Error: PyTorch and Ultralytics are required.")
    sys.exit(1)


def benchmark_model(weights_path: Path, imgsz: int = 1280, runs: int = 20) -> None:
    print("=" * 60)
    print("CROWDSIGHT AI/ML INFERENCE BENCHMARK")
    print("=" * 60)
    print(f"Weights path: {weights_path}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")

    model = YOLO(str(weights_path))
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # Warmup
    print("\nWarming up model...")
    for _ in range(3):
        model.predict(dummy_frame, imgsz=imgsz, verbose=False)

    # Benchmark CPU
    print("\n[1] Benchmarking on CPU (FP32)...")
    start = time.perf_counter()
    for _ in range(runs):
        model.predict(dummy_frame, imgsz=imgsz, device="cpu", verbose=False)
    cpu_time = (time.perf_counter() - start) / runs
    cpu_fps = 1.0 / cpu_time
    print(f"  -> CPU Mean Latency: {cpu_time * 1000:.1f} ms | Throughput: {cpu_fps:.1f} FPS")

    # Benchmark GPU (FP16) if CUDA available
    if torch.cuda.is_available():
        print("\n[2] Benchmarking on GPU CUDA (FP16 Tensor Cores)...")
        start = time.perf_counter()
        for _ in range(runs):
            model.predict(dummy_frame, imgsz=imgsz, device="cuda:0", half=True, verbose=False)
        gpu_time = (time.perf_counter() - start) / runs
        gpu_fps = 1.0 / gpu_time
        speedup = cpu_time / gpu_time
        print(f"  -> GPU Mean Latency: {gpu_time * 1000:.1f} ms | Throughput: {gpu_fps:.1f} FPS")
        print(f"\n[SUMMARY] GPU CUDA FP16 is {speedup:.1f}x faster than CPU!")


def export_model(weights_path: Path, export_format: str = "onnx", half: bool = True) -> Path:
    print(f"Exporting {weights_path} to format: {export_format.upper()} (half={half})...")
    model = YOLO(str(weights_path))
    exported_path_str = model.export(
        format=export_format,
        imgsz=1280,
        half=half,
        device="cuda:0" if torch.cuda.is_available() else "cpu",
    )
    exported_path = Path(exported_path_str)
    print(f"Successfully exported to: {exported_path}")
    print(f"Exported artifact size: {exported_path.stat().st_size / (1024 * 1024):.2f} MB")
    return exported_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export & Benchmark Optimized CrowdSight YOLO Model")
    parser.add_argument("--weights", default="models/best.pt", help="Path to best.pt weights")
    parser.add_argument("--format", default="onnx", choices=["onnx", "engine"], help="Export format")
    parser.add_argument("--half", action="store_true", default=True, help="Enable FP16 half precision")
    parser.add_argument("--benchmark", action="store_true", help="Run comparative benchmark")
    args = parser.parse_args()

    weights_path = Path(args.weights).resolve()
    if not weights_path.is_file():
        weights_path = ROOT / "models" / "best.pt"
    if not weights_path.is_file():
        weights_path = ROOT / "yolo11n.pt"

    if args.benchmark:
        benchmark_model(weights_path)
    else:
        export_model(weights_path, export_format=args.format, half=args.half)


if __name__ == "__main__":
    main()
