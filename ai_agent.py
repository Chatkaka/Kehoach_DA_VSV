import os
import re
import json
from pydantic import BaseModel, Field
from typing import Optional

# Check if google-genai is installed
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class TaskUpdateInfo(BaseModel):
    ma_ngan_sach: str = Field(description="Mã ngân sách hoặc STT công việc được nhắc đến, ví dụ: '28.11.2.1' hoặc 'TD.BĐS.28.11.2.1'")
    trang_thai: str = Field(description="Trạng thái của công việc: 'Todo', 'In-Progress', 'Done', hoặc 'Delayed'")
    tien_do: float = Field(description="Tiến độ công việc dưới dạng phần trăm (0 đến 100)")
    dieu_kien_ghi_nhan: str = Field(description="Điều kiện ghi nhận kết quả hoặc mô tả ngắn gọn nội dung công việc đã hoàn thành")

def get_gemini_client(api_key: str = None):
    # Use provided api_key, otherwise fallback to environment variable
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    if not HAS_GENAI:
        return None
    try:
        return genai.Client(api_key=key)
    except Exception as e:
        print(f"Không thể khởi tạo Gemini Client: {e}")
        return None

def parse_natural_language_update(text: str, api_key: str = None) -> dict:
    """
    Sử dụng Gemini Pro (hoặc regex fallback) để bóc tách văn bản cập nhật tiến độ công việc.
    """
    client = get_gemini_client(api_key)
    if client:
        try:
            prompt = (
                f"Hãy phân tích câu thông báo sau đây của quản lý dự án để bóc tách thông tin tiến độ công việc:\n"
                f"Câu thông báo: \"{text}\"\n\n"
                f"Hãy trích xuất mã công việc (ma_ngan_sach hoặc STT), xác định trạng thái (Todo, In-Progress, Done, Delayed), "
                f"tiến độ (0-100), và điều kiện ghi nhận kết quả."
            )
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TaskUpdateInfo,
                    temperature=0.1
                ),
            )
            
            # Phản hồi dạng JSON tuân thủ schema
            data = json.loads(response.text)
            return {
                "ma_ngan_sach": data.get("ma_ngan_sach", ""),
                "trang_thai": data.get("trang_thai", "Done"),
                "tien_do": float(data.get("tien_do", 100.0)),
                "dieu_kien_ghi_nhan": data.get("dieu_kien_ghi_nhan", text),
                "method": "Gemini AI"
            }
        except Exception as e:
            print(f"Lỗi khi gọi Gemini API: {e}. Sử dụng Regex fallback...")
    
    # Regex fallback nếu không có API key hoặc lỗi
    return regex_parse_fallback(text)

def regex_parse_fallback(text: str) -> dict:
    """
    Trích xuất bằng Regex cho mục đích thử nghiệm offline
    """
    # Tìm chuỗi số dạng WBS hoặc STT (ví dụ: 28.11.2.1 hoặc TD.BĐS.28...)
    match = re.search(r'([A-Za-z\.]+)?\d+(\.\d+)+', text)
    ma_ngan_sach = match.group(0) if match else "1.1"

    # Đoán trạng thái và tiến độ từ từ khóa
    trang_thai = "Done"
    tien_do = 100.0
    
    lower_text = text.lower()
    if "chưa" in lower_text or "chậm" in lower_text:
        trang_thai = "Delayed"
        tien_do = 30.0
    elif "đang" in lower_text or "bắt đầu" in lower_text:
        trang_thai = "In-Progress"
        tien_do = 50.0
    elif "hoàn thành" in lower_text or "đã xong" in lower_text or "đã duyệt" in lower_text or "phê duyệt" in lower_text:
        trang_thai = "Done"
        tien_do = 100.0

    # Điều kiện ghi nhận là mô tả từ văn bản thô
    dieu_kien_ghi_nhan = text.strip()

    return {
        "ma_ngan_sach": ma_ngan_sach,
        "trang_thai": trang_thai,
        "tien_do": tien_do,
        "dieu_kien_ghi_nhan": dieu_kien_ghi_nhan,
        "method": "Regex Fallback (Offline)"
    }

def evaluate_financial_risk(project_total_budget: float, total_spent: float, spending_details: list, api_key: str = None) -> str:
    """
    Đánh giá rủi ro tài chính và tiến độ dựa trên số liệu ngân sách và thực chi.
    """
    client = get_gemini_client(api_key)
    ratio = (total_spent / project_total_budget * 100) if project_total_budget > 0 else 0.0
    
    if client:
        try:
            details_str = json.dumps(spending_details[:10], ensure_ascii=False)
            prompt = (
                f"Bạn là Giám đốc Tài chính (CFO) của dự án Bất động sản Ven Sông Vinh.\n"
                f"Hãy đánh giá rủi ro tài chính của dự án dựa trên số liệu sau:\n"
                f"- Tổng ngân sách dự án: {project_total_budget:,.2f} Trđ\n"
                f"- Lũy kế thực chi: {total_spent:,.2f} Trđ (Tỷ lệ giải ngân: {ratio:.2f}%)\n"
                f"- Chi tiết các khoản chi lớn/vượt ngân sách gần đây: {details_str}\n\n"
                f"Hãy viết một báo cáo đánh giá rủi ro tài chính và tiến độ ngắn gọn (dưới 200 từ), "
                f"chỉ ra các mối nguy hại tiềm ẩn (nếu có) và đưa ra 2 khuyến nghị hành động nhanh cho CEO."
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Lỗi khi gọi Gemini API đánh giá rủi ro: {e}")

    # Fallback báo cáo tài chính ngoại tuyến
    if ratio > 90:
        status_text = "CẢNH BÁO ĐỎ: Ngân sách đã giải ngân đạt mức báo động (>90%)."
        recs = "1. Dừng ngay việc duyệt tất cả các khoản chi phát sinh ngoài ngân sách.\n2. Tổ chức họp khẩn cấp với các Ban quản lý để rà soát tổng thể mức đầu tư."
    elif ratio > 75:
        status_text = "CẢNH BÁO VÀNG: Tỷ lệ giải ngân khá cao, cần kiểm soát chặt chẽ."
        recs = "1. Yêu cầu báo cáo chi tiết các hạng mục chuẩn bị thi công.\n2. Tối ưu hóa lại chi phí nhân công và vật tư xây dựng."
    else:
        status_text = "AN TOÀN: Tỷ lệ giải ngân nằm trong tầm kiểm soát."
        recs = "1. Tiếp tục bám sát tiến độ giải ngân theo kế hoạch quý.\n2. Phê duyệt nhanh các hạng mục thi công đúng tiến độ."

    report = (
        f"**BÁO CÁO ĐÁNH GIÁ RỦI RO TÀI CHÍNH DỰ ÁN (OFFLINE)**\n\n"
        f"- **Tổng ngân sách:** {project_total_budget:,.2f} Trđ\n"
        f"- **Lũy kế thực chi:** {total_spent:,.2f} Trđ ({ratio:.2f}%)\n"
        f"- **Đánh giá chung:** {status_text}\n\n"
        f"**Khuyến nghị hành động:**\n{recs}"
    )
    return report
