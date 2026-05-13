"""
Gemini video analyzer - dùng REST API trực tiếp (không cần SDK).
Tương thích Python 3.7+.

Upload video → wait processing → request structured JSON output.
"""
import json
import mimetypes
import os
import time
from pathlib import Path

import requests


API_BASE = "https://generativelanguage.googleapis.com"
UPLOAD_URL = f"{API_BASE}/upload/v1beta/files"
FILES_URL = f"{API_BASE}/v1beta/files"


ANALYSIS_PROMPT_VI = """Bạn là chuyên gia phân tích video học thuật chuyên nghiệp. Hãy XEM TOÀN BỘ video và trích xuất TẤT CẢ nội dung một cách CHI TIẾT, ĐẦY ĐỦ và CHÍNH XÁC NHẤT có thể.

NHIỆM VỤ:
1. Phân tích HÌNH ẢNH: chữ trên bảng, slide, sách, công thức toán, hình vẽ, sơ đồ, biểu đồ, bảng biểu — KHÔNG bỏ sót.
2. Phân tích LỜI NÓI: chép lại NGUYÊN VĂN toàn bộ lời nói kèm timestamp chính xác (không tóm tắt, không rút gọn).
3. Phân biệt rõ: bài tập, ví dụ, định nghĩa, định lý, lời giải, đáp án, ghi chú.
4. Giữ NGUYÊN VĂN tiếng Việt, không dịch thuật ngữ chuyên ngành.
5. Công thức toán phải viết bằng LaTeX: $...$ (inline) hoặc $$...$$ (block).
6. Hình vẽ/sơ đồ: mô tả CHI TIẾT bằng text (vị trí, nhãn, mũi tên, màu sắc, ký hiệu).
7. Nếu có nhiều bài tập, đánh số rõ ràng (Bài 1, Bài 2, Câu a, b, c...).

YÊU CẦU OUTPUT:
- Trả về JSON HỢP LỆ đúng schema được cung cấp, KHÔNG kèm markdown ```json.
- KHÔNG bỏ sót bất kỳ nội dung nào trên màn hình hay trong lời nói.
- Với bài tập: ghi rõ ĐỀ BÀI nguyên văn, DỮ KIỆN, LỜI GIẢI từng bước (nếu có), ĐÁP ÁN cuối cùng.
- Với bài giảng: chia theo CHƯƠNG/PHẦN logic, mỗi section có timestamp.
- full_transcript: toàn bộ lời nói liên tục, có timestamp mỗi 30-60 giây hoặc khi đổi chủ đề.
"""


SCHEMA_HINT = """
JSON SCHEMA OUTPUT (BẮT BUỘC tuân thủ):
{
  "title": "string - tiêu đề video",
  "content_type": "exercise | lecture | tutorial | presentation | demonstration | other",
  "language": "string - vi/en/...",
  "duration_estimate": "string - HH:MM:SS",
  "summary": "string - tóm tắt 3-5 câu",
  "sections": [
    {
      "timestamp_start": "HH:MM:SS",
      "timestamp_end": "HH:MM:SS",
      "title": "string",
      "spoken_content": "string - lời nói NGUYÊN VĂN",
      "visual_content": "string - mô tả CHI TIẾT hình ảnh/chữ trên màn hình",
      "key_points": ["string", "..."],
      "notes": "string"
    }
  ],
  "exercises": [
    {
      "number": "string - VD 'Bài 1', 'Câu 2a'",
      "timestamp": "HH:MM:SS",
      "topic": "string",
      "problem_statement": "string - đề bài NGUYÊN VĂN, LaTeX cho công thức",
      "given_info": "string - dữ kiện",
      "diagram_description": "string - mô tả hình vẽ",
      "solution": "string - lời giải từng bước",
      "answer": "string - đáp án cuối",
      "difficulty": "easy | medium | hard | unknown"
    }
  ],
  "key_terms": [
    {"term": "string", "definition": "string"}
  ],
  "full_transcript": "string - toàn bộ lời nói với [HH:MM:SS] mỗi 30-60s"
}

LƯU Ý:
- Nếu video không có exercises thì để mảng rỗng []
- Nếu không có key_terms thì để mảng rỗng []
- Trả về JSON HỢP LỆ (parseable), KHÔNG thêm markdown fence
"""


# MIME type map for common video formats
VIDEO_MIME_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".flv": "video/x-flv",
    ".wmv": "video/x-ms-wmv",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".3gp": "video/3gpp",
}


def _get_mime_type(video_path):
    ext = Path(video_path).suffix.lower()
    if ext in VIDEO_MIME_TYPES:
        return VIDEO_MIME_TYPES[ext]
    guess, _ = mimetypes.guess_type(video_path)
    return guess or "video/mp4"


def _upload_video(video_path, api_key):
    """Resumable upload to Gemini File API. Returns file metadata."""
    file_size = os.path.getsize(video_path)
    mime_type = _get_mime_type(video_path)
    display_name = os.path.basename(video_path)

    # Step 1: Initialize resumable upload session
    init_headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(file_size),
        "X-Goog-Upload-Header-Content-Type": mime_type,
        "Content-Type": "application/json",
    }
    init_body = {"file": {"display_name": display_name}}

    r = requests.post(
        f"{UPLOAD_URL}?key={api_key}",
        headers=init_headers,
        data=json.dumps(init_body),
        timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Init upload failed [{r.status_code}]: {r.text}")
    upload_url = r.headers.get("X-Goog-Upload-URL") or r.headers.get("x-goog-upload-url")
    if not upload_url:
        raise RuntimeError(f"Không nhận được upload URL từ Gemini. Response: {r.text}")

    # Step 2: Upload bytes
    with open(video_path, "rb") as f:
        upload_headers = {
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        }
        r = requests.post(upload_url, headers=upload_headers, data=f, timeout=600)

    if r.status_code != 200:
        raise RuntimeError(f"Upload bytes failed [{r.status_code}]: {r.text}")

    body = r.json()
    return body.get("file") or body


def _wait_for_active(file_resource, api_key, timeout_s=900):
    """Poll until file state is ACTIVE."""
    name = file_resource["name"]  # e.g. "files/xxxxx"
    url = f"{API_BASE}/v1beta/{name}?key={api_key}"
    start = time.time()
    wait = 0
    while time.time() - start < timeout_s:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"Get file failed [{r.status_code}]: {r.text}")
        info = r.json()
        state = info.get("state", "UNKNOWN")
        if state == "ACTIVE":
            return info
        if state == "FAILED":
            raise RuntimeError(f"Gemini xử lý video thất bại: {info}")
        print(f"   → Status: {state} ({wait}s elapsed)")
        time.sleep(5)
        wait += 5
    raise TimeoutError(f"Timeout chờ Gemini xử lý video (>{timeout_s}s)")


def _generate_content(model, file_info, prompt, api_key, generation_config=None):
    """Call generateContent with file reference."""
    url = f"{API_BASE}/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "file_data": {
                            "mime_type": file_info.get("mimeType", "video/mp4"),
                            "file_uri": file_info["uri"],
                        }
                    },
                    {"text": prompt},
                ]
            }
        ]
    }
    if generation_config:
        payload["generationConfig"] = generation_config

    r = requests.post(url, json=payload, timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"generateContent failed [{r.status_code}]: {r.text}")

    result = r.json()
    candidates = result.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini không trả về kết quả. Response: {json.dumps(result, ensure_ascii=False)[:500]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return text


def _delete_file(file_resource, api_key):
    try:
        name = file_resource["name"]
        requests.delete(f"{API_BASE}/v1beta/{name}?key={api_key}", timeout=30)
    except Exception:
        pass


def _safe_json_parse(text):
    """Parse JSON robustly, stripping markdown fences if present."""
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise RuntimeError(f"Không parse được JSON từ Gemini: {e}\nResponse (preview): {text[:500]}")


def analyze_video(
    video_path,
    api_key,
    mode="auto",
    language="vi",
    model="gemini-2.5-pro",
):
    """Upload video to Gemini File API and get structured analysis."""
    print(f"   → Uploading video to Gemini File API...")
    file_info = _upload_video(video_path, api_key)
    print(f"   → File ID: {file_info.get('name', '?')}")
    print(f"   → URI:     {file_info.get('uri', '?')}")

    # Wait for file to be processed
    file_info = _wait_for_active(file_info, api_key)
    print(f"   → Status: ACTIVE ✓")
    print(f"   → Đang gửi tới {model} để phân tích chi tiết...")

    prompt = ANALYSIS_PROMPT_VI
    if mode == "exercise":
        prompt += "\n\nĐẶC BIỆT QUAN TRỌNG: Video này chứa BÀI TẬP. Tập trung trích xuất ĐẦY ĐỦ TẤT CẢ bài tập trong array 'exercises'."
    elif mode == "lecture":
        prompt += "\n\nĐẶC BIỆT QUAN TRỌNG: Video là BÀI GIẢNG. Chép NGUYÊN VĂN lời giảng trong 'full_transcript' và chia 'sections' theo logic chương/mục."
    elif mode == "transcript":
        prompt += "\n\nĐẶC BIỆT QUAN TRỌNG: Mục đích chính là CHÉP LẠI lời nói. Ưu tiên 'full_transcript' với timestamp dày đặc (mỗi 15-30 giây)."

    prompt += "\n\n" + SCHEMA_HINT

    generation_config = {
        "responseMimeType": "application/json",
        "temperature": 0.1,
        "maxOutputTokens": 65000,
    }

    try:
        text = _generate_content(model, file_info, prompt, api_key, generation_config)
    finally:
        _delete_file(file_info, api_key)

    if not text:
        raise RuntimeError("Gemini trả về response trống.")

    return _safe_json_parse(text)


if __name__ == "__main__":
    import sys
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    if len(sys.argv) < 2:
        print("Usage: python gemini_analyzer.py <video_path>")
        sys.exit(1)
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GOOGLE_API_KEY in .env")
        sys.exit(1)
    result = analyze_video(sys.argv[1], api_key)
    print(json.dumps(result, ensure_ascii=False, indent=2))
