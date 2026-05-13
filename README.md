# Video → Documents (Gemini 2.5 Pro)

Công cụ CLI Python tự động phân tích video (cả hình ảnh và lời nói) và xuất ra **Word, PDF, Excel, PowerPoint, Markdown, JSON**. Đặc biệt mạnh với video bài giảng, bài tập, hướng dẫn — Gemini sẽ "xem" video như con người, đọc công thức toán, hình vẽ, sơ đồ và ghi chép lại đầy đủ.

## ✨ Tính năng

- 🎬 Phân tích **toàn bộ video** (hình ảnh + âm thanh) bằng Gemini 2.5 Pro
- 📝 Chép nguyên văn lời nói có timestamp
- 🧮 Đọc công thức toán → LaTeX
- 📐 Mô tả chi tiết hình vẽ, sơ đồ, biểu đồ
- 📚 Trích xuất bài tập tự động (đề bài, dữ kiện, lời giải, đáp án)
- 📤 Xuất 6 định dạng cùng lúc: `.docx .pdf .xlsx .pptx .md .json`
- 🇻🇳 Hỗ trợ tốt tiếng Việt

## 🚀 Cài đặt nhanh (Windows)

### Bước 1: Lấy Google API Key (miễn phí)
1. Truy cập: https://aistudio.google.com/app/apikey
2. Đăng nhập tài khoản Google
3. Bấm **"Create API Key"** → copy key

### Bước 2: Chạy installer
Mở Command Prompt trong thư mục này và chạy:
```cmd
install.bat
```

### Bước 3: Cấu hình API key
Mở file `.env` (vừa được tạo) bằng Notepad và dán key vào:
```
GOOGLE_API_KEY=AIzaSy....your_key_here
```

## 🎯 Sử dụng

### Cách đơn giản nhất
```cmd
run.bat "C:\Videos\bai_giang.mp4"
```
Tự động tạo cả 6 định dạng trong thư mục `./output/`.

### Sử dụng nâng cao
```cmd
REM Kích hoạt venv trước
.venv\Scripts\activate

REM Chế độ bài tập, xuất Word + PDF
python main.py "C:\Videos\bai_tap.mp4" --mode exercise --formats docx,pdf

REM Chế độ bài giảng, lưu vào thư mục tùy chọn
python main.py video.mp4 --mode lecture -o "D:\Tai_lieu"

REM Chỉ chép lời nói (transcript)
python main.py video.mp4 --mode transcript --formats md,docx

REM Dùng Gemini Flash (nhanh và rẻ hơn ~10 lần)
python main.py video.mp4 --model gemini-2.5-flash
```

## 📋 Các tham số CLI

| Tham số | Viết tắt | Mô tả | Mặc định |
|---|---|---|---|
| `video` | | Đường dẫn file video (bắt buộc) | — |
| `--formats` | `-f` | Định dạng output, phân cách bằng dấu phẩy. Hoặc `all`. | `all` |
| `--output` | `-o` | Thư mục lưu kết quả | `./output` |
| `--mode` | `-m` | `auto` / `exercise` / `lecture` / `transcript` | `auto` |
| `--language` | `-l` | Ngôn ngữ chính (`vi`/`en`/`auto`) | `vi` |
| `--model` | | Model Gemini | `gemini-2.5-pro` |
| `--api-key` | | API key trực tiếp (thay cho .env) | — |
| `--save-raw-json` | | Lưu thêm JSON debug | off |

### Chế độ phân tích (`--mode`)

| Mode | Khi nào dùng |
|---|---|
| `auto` | Mặc định, Gemini tự nhận diện loại nội dung |
| `exercise` | Video chứa bài tập — tập trung trích xuất chi tiết từng bài |
| `lecture` | Bài giảng — chép nguyên văn lời giảng + chia chương |
| `transcript` | Chỉ cần chép lời (như podcast, phỏng vấn) |

### Định dạng video hỗ trợ
`.mp4 .mov .avi .mkv .webm .flv .wmv .mpeg .3gp` — bất kỳ định dạng nào Gemini File API chấp nhận.

## 📁 File output

Sau khi chạy, bạn sẽ có trong thư mục `./output/`:

| File | Nội dung |
|---|---|
| `video.docx` | Word có heading, mục lục, công thức |
| `video.pdf` | PDF in được, hỗ trợ tiếng Việt |
| `video.xlsx` | 5 sheet: Tổng quan, Timeline, Bài tập, Thuật ngữ, Transcript |
| `video.pptx` | Slides cho từng section + bài tập |
| `video.md` | Markdown để xem nhanh hoặc import vào Notion/Obsidian |
| `video.json` | Dữ liệu thô có cấu trúc, dùng cho automation |

## 💡 Mẹo

- **Video dài (>1h)**: nén video xuống 480p và mono audio bằng ffmpeg để upload nhanh hơn:
  ```
  ffmpeg -i input.mp4 -vf scale=854:480 -ac 1 -b:v 800k output.mp4
  ```
- **Tiết kiệm chi phí**: dùng `--model gemini-2.5-flash` cho video dài, chất lượng vẫn ổn cho hầu hết mục đích.
- **Bài tập có nhiều công thức**: kết quả LaTeX trong file Word/PDF có thể cần Mathpix Snip hoặc MathType để hiển thị đẹp như công thức Word native.
- **Debug**: thêm `--save-raw-json` để xem Gemini trả về gì.

## 💰 Chi phí ước tính

Gemini 2.5 Pro tính theo token. Một video 1 tiếng (~720p) khoảng:
- Gemini 2.5 Pro: ~$0.50 – $2.00
- Gemini 2.5 Flash: ~$0.05 – $0.20

Google AI Studio có **gói miễn phí** cho phép xử lý vài chục video/ngày — đủ dùng cho cá nhân.

## 🐛 Khắc phục sự cố

**Lỗi `ModuleNotFoundError`** → Chưa kích hoạt venv. Chạy `.venv\Scripts\activate` trước.

**Lỗi `API key invalid`** → Kiểm tra file `.env`, đảm bảo không có dấu cách thừa quanh key.

**Lỗi `Status: FAILED`** → Video bị hỏng hoặc định dạng không hỗ trợ. Convert qua mp4 bằng ffmpeg.

**Lỗi PDF có dấu tiếng Việt bị mất** → Cài font Arial/Tahoma trên hệ thống. Code đã tự tìm font Windows.

**Video quá lớn (>2GB)** → Nén video bằng ffmpeg trước khi upload.

## 📐 Cấu trúc dự án

```
video_to_docs/
├── main.py              # CLI entry point
├── gemini_analyzer.py   # Logic gọi Gemini + schema JSON
├── exporters.py         # 6 exporter functions
├── requirements.txt     # Python dependencies
├── install.bat          # Windows installer
├── run.bat              # Windows runner
├── .env.example         # Template biến môi trường
└── README.md            # File này
```

## 🔧 Mở rộng

Muốn thêm tính năng?
- **Diarization (phân biệt người nói)**: tích hợp `pyannote.audio` sau khi tách audio bằng ffmpeg
- **OCR tăng cường cho công thức**: gọi Mathpix API cho frames có công thức phức tạp
- **Web UI**: thêm FastAPI ở `app.py`, upload qua trình duyệt
- **Batch processing**: viết loop xử lý cả thư mục video

Code được tách module rõ ràng, dễ mở rộng. Chỉ cần sửa `VIDEO_SCHEMA` trong `gemini_analyzer.py` và thêm exporter tương ứng.

---
Built with ❤️ — Gemini 2.5 Pro + Python
