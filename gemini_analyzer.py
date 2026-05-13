"""
Gemini 2.5 Pro video analyzer.
Upload video → wait processing → request structured JSON output.
"""
import time
import json
from pathlib import Path
from google import genai
from google.genai import types


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
- Trả về JSON đúng schema được cung cấp.
- KHÔNG bỏ sót bất kỳ nội dung nào trên màn hình hay trong lời nói.
- Với bài tập: ghi rõ ĐỀ BÀI nguyên văn, DỮ KIỆN, LỜI GIẢI từng bước (nếu có), ĐÁP ÁN cuối cùng.
- Với bài giảng: chia theo CHƯƠNG/PHẦN logic, mỗi section có timestamp.
- full_transcript: toàn bộ lời nói liên tục, có timestamp mỗi 30-60 giây hoặc khi đổi chủ đề.
"""


VIDEO_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Tiêu đề video, suy ra từ nội dung chính"
        },
        "content_type": {
            "type": "string",
            "enum": ["exercise", "lecture", "tutorial", "presentation", "demonstration", "other"],
            "description": "Loại nội dung video"
        },
        "language": {"type": "string", "description": "Ngôn ngữ chính: vi, en, etc."},
        "duration_estimate": {"type": "string", "description": "Ước lượng thời lượng video"},
        "summary": {"type": "string", "description": "Tóm tắt 3-5 câu về nội dung"},
        "sections": {
            "type": "array",
            "description": "Các phần/chương của video theo trình tự thời gian",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp_start": {"type": "string", "description": "HH:MM:SS"},
                    "timestamp_end": {"type": "string", "description": "HH:MM:SS"},
                    "title": {"type": "string"},
                    "spoken_content": {
                        "type": "string",
                        "description": "Lời nói NGUYÊN VĂN trong section này, không tóm tắt"
                    },
                    "visual_content": {
                        "type": "string",
                        "description": "Mô tả CHI TIẾT mọi thứ hiển thị trên màn hình: chữ, công thức (LaTeX), hình vẽ, sơ đồ, bảng"
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Các ý chính của section"
                    },
                    "notes": {"type": "string", "description": "Ghi chú thêm nếu có"}
                },
                "required": ["timestamp_start", "title", "spoken_content", "visual_content"]
            }
        },
        "exercises": {
            "type": "array",
            "description": "Danh sách TẤT CẢ bài tập xuất hiện trong video",
            "items": {
                "type": "object",
                "properties": {
                    "number": {"type": "string", "description": "VD: 'Bài 1', 'Câu 2a'"},
                    "timestamp": {"type": "string", "description": "Thời điểm xuất hiện HH:MM:SS"},
                    "topic": {"type": "string", "description": "Chủ đề/môn học"},
                    "problem_statement": {
                        "type": "string",
                        "description": "Đề bài NGUYÊN VĂN, công thức bằng LaTeX"
                    },
                    "given_info": {"type": "string", "description": "Dữ kiện cho trước"},
                    "diagram_description": {
                        "type": "string",
                        "description": "Mô tả chi tiết hình vẽ kèm theo (nếu có)"
                    },
                    "solution": {
                        "type": "string",
                        "description": "Lời giải từng bước (nếu video có)"
                    },
                    "answer": {"type": "string", "description": "Đáp án cuối cùng (nếu có)"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["easy", "medium", "hard", "unknown"]
                    }
                },
                "required": ["number", "problem_statement"]
            }
        },
        "key_terms": {
            "type": "array",
            "description": "Thuật ngữ, định nghĩa, định lý quan trọng",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "definition": {"type": "string"}
                },
                "required": ["term", "definition"]
            }
        },
        "full_transcript": {
            "type": "string",
            "description": "Toàn bộ lời nói nguyên văn với timestamp [HH:MM:SS] xuất hiện mỗi 30-60 giây"
        }
    },
    "required": ["title", "content_type", "sections"]
}


def analyze_video(
    video_path: str,
    api_key: str,
    mode: str = "auto",
    language: str = "vi",
    model: str = "gemini-2.5-pro",
) -> dict:
    """Upload video to Gemini File API and get structured analysis."""
    client = genai.Client(api_key=api_key)

    print(f"   → Uploading video to Gemini File API...")
    video_file = client.files.upload(file=video_path)
    print(f"   → File ID: {video_file.name}")

    # Wait for video to be processed
    wait = 0
    while video_file.state.name == "PROCESSING":
        print(f"   → Status: PROCESSING ({wait}s elapsed)")
        time.sleep(5)
        wait += 5
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini không xử lý được video: {video_file.error}")

    print(f"   → Status: {video_file.state.name} ✓")
    print(f"   → Đang gửi tới {model} để phân tích chi tiết...")

    prompt = ANALYSIS_PROMPT_VI
    if mode == "exercise":
        prompt += "\n\nĐẶC BIỆT QUAN TRỌNG: Video này chứa BÀI TẬP. Tập trung trích xuất ĐẦY ĐỦ TẤT CẢ bài tập trong array 'exercises'."
    elif mode == "lecture":
        prompt += "\n\nĐẶC BIỆT QUAN TRỌNG: Video là BÀI GIẢNG. Chép NGUYÊN VĂN lời giảng trong 'full_transcript' và chia 'sections' theo logic chương/mục."
    elif mode == "transcript":
        prompt += "\n\nĐẶC BIỆT QUAN TRỌNG: Mục đích chính là CHÉP LẠI lời nói. Ưu tiên 'full_transcript' với timestamp dày đặc (mỗi 15-30 giây)."

    response = client.models.generate_content(
        model=model,
        contents=[video_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VIDEO_SCHEMA,
            temperature=0.1,
            max_output_tokens=65000,
        ),
    )

    # Cleanup uploaded file (Gemini auto-deletes after 48h anyway)
    try:
        client.files.delete(name=video_file.name)
    except Exception:
        pass

    if not response.text:
        raise RuntimeError("Gemini trả về response trống.")

    return json.loads(response.text)


if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv

    load_dotenv()
    if len(sys.argv) < 2:
        print("Usage: python gemini_analyzer.py <video_path>")
        sys.exit(1)
    result = analyze_video(sys.argv[1], os.environ["GOOGLE_API_KEY"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
