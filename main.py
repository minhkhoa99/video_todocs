"""
Video → Documents converter (CLI)
Powered by Google Gemini 2.5 Pro.

Usage:
    python main.py video.mp4
    python main.py video.mp4 --formats docx,pdf,xlsx,pptx,md,json
    python main.py video.mp4 --mode exercise --output ./output
"""
import argparse
import os
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from gemini_analyzer import analyze_video
from exporters import export_all


ALL_FORMATS = ["docx", "pdf", "xlsx", "pptx", "md", "json"]


def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s:02d}s" if m else f"{s}s"


def main():
    parser = argparse.ArgumentParser(
        description="Video → Documents: chuyển video thành tài liệu (Word/PDF/Excel/PowerPoint/Markdown/JSON) bằng Gemini 2.5 Pro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python main.py video.mp4
      → Chuyển video.mp4 thành tất cả định dạng trong ./output/

  python main.py "C:/Videos/bai_giang.mp4" --mode lecture --formats docx,pdf
      → Chỉ xuất Word và PDF, chế độ bài giảng

  python main.py homework.mp4 --mode exercise -o ./tai_lieu
      → Chế độ bài tập, lưu vào ./tai_lieu/
""",
    )
    parser.add_argument("video", help="Đường dẫn file video (mp4, mov, avi, mkv, webm...)")
    parser.add_argument(
        "--formats", "-f",
        default="all",
        help=f"Định dạng output (cách nhau bằng dấu phẩy). Mặc định: all. "
             f"Lựa chọn: {','.join(ALL_FORMATS)} hoặc 'all'",
    )
    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Thư mục lưu file output. Mặc định: ./output",
    )
    parser.add_argument(
        "--mode", "-m",
        default="auto",
        choices=["auto", "exercise", "lecture", "transcript"],
        help="Chế độ phân tích: auto/exercise/lecture/transcript. Mặc định: auto",
    )
    parser.add_argument(
        "--language", "-l",
        default="vi",
        help="Ngôn ngữ chính của video (vi/en/auto). Mặc định: vi",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-pro",
        help="Model Gemini. Mặc định: gemini-2.5-pro. Có thể dùng gemini-2.5-flash để rẻ hơn.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Google API key (hoặc set biến môi trường GOOGLE_API_KEY)",
    )
    parser.add_argument(
        "--save-raw-json",
        action="store_true",
        help="Lưu thêm file JSON thô từ Gemini (debug)",
    )

    args = parser.parse_args()

    # Validate API key
    api_key = args.api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ LỖI: Chưa có Google API key.")
        print("   → Tạo file .env với nội dung: GOOGLE_API_KEY=your_key")
        print("   → Hoặc dùng: --api-key YOUR_KEY")
        print("   → Lấy API key miễn phí tại: https://aistudio.google.com/app/apikey")
        sys.exit(1)

    # Validate input video
    video_path = Path(args.video).expanduser().resolve()
    if not video_path.exists():
        print(f"❌ LỖI: Không tìm thấy file video: {video_path}")
        sys.exit(1)

    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 2048:
        print(f"⚠️  Video lớn ({file_size_mb:.0f}MB). Gemini File API giới hạn ~2GB. Cân nhắc nén video trước.")

    # Validate formats
    if args.formats.lower() in ("all", "*"):
        formats = ALL_FORMATS.copy()
    else:
        formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
        invalid = [f for f in formats if f not in ALL_FORMATS]
        if invalid:
            print(f"❌ Format không hỗ trợ: {invalid}. Hỗ trợ: {ALL_FORMATS}")
            sys.exit(1)

    # Setup output directory
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = sanitize_filename(video_path.stem)

    # Banner
    print("=" * 72)
    print("  🎬  VIDEO → DOCUMENTS  (Gemini 2.5 Pro)")
    print("=" * 72)
    print(f"  📹 Video:       {video_path.name} ({file_size_mb:.1f} MB)")
    print(f"  🧠 Model:       {args.model}")
    print(f"  🎯 Chế độ:      {args.mode}")
    print(f"  🌐 Ngôn ngữ:    {args.language}")
    print(f"  📂 Output:      {output_dir}")
    print(f"  📄 Định dạng:   {', '.join(formats)}")
    print("=" * 72)

    # Step 1: Analyze
    t0 = time.time()
    print(f"\n[1/2] 🔍 Phân tích video bằng Gemini...")
    try:
        result = analyze_video(
            video_path=str(video_path),
            api_key=api_key,
            mode=args.mode,
            language=args.language,
            model=args.model,
        )
    except Exception as e:
        print(f"❌ Lỗi khi gọi Gemini API: {e}")
        sys.exit(2)

    elapsed = time.time() - t0
    n_sections = len(result.get("sections", []))
    n_exercises = len(result.get("exercises", []))
    n_terms = len(result.get("key_terms", []))
    print(f"      ✓ Hoàn thành trong {fmt_time(elapsed)}")
    print(f"      📊 Tìm thấy: {n_sections} sections, {n_exercises} bài tập, {n_terms} thuật ngữ")

    # Optional: save raw JSON
    if args.save_raw_json:
        import json
        raw_path = output_dir / f"{base_name}.raw.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"      💾 Đã lưu raw JSON: {raw_path}")

    # Step 2: Export
    print(f"\n[2/2] 📝 Xuất tài liệu...")
    output_files = export_all(result, output_dir, base_name, formats)

    # Summary
    total = time.time() - t0
    print("\n" + "=" * 72)
    print(f"  ✅ HOÀN TẤT trong {fmt_time(total)} — {len(output_files)} file đã tạo:")
    for f in output_files:
        size_kb = f.stat().st_size / 1024
        print(f"     • {f}  ({size_kb:.1f} KB)")
    print("=" * 72)


def sanitize_filename(name: str) -> str:
    """Loại bỏ ký tự không hợp lệ cho tên file."""
    invalid = '<>:"/\\|?*'
    for ch in invalid:
        name = name.replace(ch, "_")
    return name.strip(". ") or "output"


if __name__ == "__main__":
    main()
