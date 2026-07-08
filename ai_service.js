/**
 * GEMINI AI COGNITIVE LAYER & DATA INGESTION SERVICE
 * Harness Engineer Implementation for Construction Life Cycle
 */

class GeminiAIService {
    constructor() {
        this.apiKey = localStorage.getItem('gemini_api_key') || '';
        this.model = localStorage.getItem('gemini_model') || 'gemini-3.5-flash';
        this.isSimulation = !this.apiKey;
    }

    setApiKey(key) {
        this.apiKey = key;
        localStorage.setItem('gemini_api_key', key);
        this.isSimulation = !key;
    }

    setModel(modelName) {
        this.model = modelName || 'gemini-3.5-flash';
        localStorage.setItem('gemini_model', this.model);
    }

    getAiStatus() {
        if (this.isSimulation) {
            return {
                mode: 'simulation',
                text: 'Đang ở chế độ Giả lập (Simulation Mode - Không cần API Key)',
                color: 'var(--warning)'
            };
        } else {
            return {
                mode: 'live',
                text: `Gemini AI Live (${this.model}) - Sẵn sàng kết nối`,
                color: '#10b981'
            };
        }
    }

    /**
     * Call Google Gemini API (Dynamic Model)
     */
    async callGeminiAPI(prompt, systemInstruction = '') {
        if (this.isSimulation) {
            return this.getMockResponse(prompt);
        }

        const url = `https://generativelanguage.googleapis.com/v1beta/models/${this.model}:generateContent?key=${this.apiKey}`;
        const requestBody = {
            contents: [{
                parts: [{ text: prompt }]
            }]
        };

        if (systemInstruction) {
            requestBody.systemInstruction = {
                parts: [{ text: systemInstruction }]
            };
        }

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.error?.message || 'Lỗi kết nối Gemini API');
            }

            const resData = await response.json();
            return resData.candidates[0].content.parts[0].text;
        } catch (error) {
            console.error('Gemini API Error, falling back to simulation:', error);
            return `[Lỗi API: ${error.message}]. Phản hồi giả lập:\n\n` + this.getMockResponse(prompt);
        }
    }

    /**
     * Custom Fallback Responses for Simulation Mode
     */
    getMockResponse(prompt) {
        const query = prompt.toLowerCase();
        
        if (query.includes('rủi ro tài chính') || query.includes('vượt trần') || query.includes('rủi ro cao nhất')) {
            return `### BÁO CÁO PHÂN TÍCH RỦI RO TÀI CHÍNH (GEMINI AGENT)

Dự trên việc quét Bảng Master và các Sổ nghiệp vụ, tôi phát hiện các rủi ro tài chính sau:

1. **Gói thầu nguy cấp nhất: VSV_QLTC_TT.01 (CT-01: Thi công & lắp đặt thiết bị Nhà mẫu)**
   - **Lũy kế Tổng Chi phí:** **1.34 tỷ** (Giá trị HĐ A-B) + **0.80 tỷ** (Phát sinh đã duyệt) = **2.14 tỷ**.
   - **Ngân sách CĐT duyệt:** **2.18 tỷ**.
   - **Tỷ lệ chi phí/ngân sách:** **98.17%** (Đã vượt ngưỡng an toàn **95%**).
   - **Tác động:** Hệ thống đã kích hoạt **Chốt chặn Ngân sách (Financial Hard Gate)**, khóa phê duyệt các phát sinh mới.
   
2. **Khuyến nghị điều hành (Prescriptive Action):**
   - Giám đốc dự án cần làm việc với CĐT để ký **Phụ lục hợp đồng điều chỉnh tăng ngân sách gói thầu CT-01** lên tối thiểu **3.5 tỷ** để giải phóng chốt chặn.`;
        }

        if (query.includes('tiến độ') || query.includes('trễ hạn') || query.includes('chậm')) {
            return `### TÓM TẮT PHƯƠNG ÁN BÙ TIẾN ĐỘ

* **Nguyên nhân gốc rễ:** Mưa lớn kéo dài kết hợp xuất hiện túi bùn địa chất yếu cục bộ tại khu vực hố móng.
* **Biện pháp khắc phục đã duyệt:**
  - Thực hiện tăng ca đêm 2h/ngày.
  - Bổ sung 1 máy ép cọc chuyên dụng đẩy nhanh tiến độ cọc đại trà.
  - Tổ chức lại dây chuyền đổ bê tông phân đoạn cuốn chiếu.
* **Kết quả thực hiện:** Đã bù lại được **2/5 ngày** chậm trễ, đảm bảo mốc bàn giao móng.`;
        }

        return `### Trợ Lý AI Gemini trả lời:
Tôi đã nhận được câu hỏi của bạn về dự án. Dưới đây là phân tích nhanh:
- Hiện tại hệ thống ghi nhận đầy đủ các gói thầu/hạng mục trong CSDL Master.
- Bạn có thể hỏi sâu hơn bằng cách ra lệnh: *"Mã BSC nào đang gặp rủi ro tài chính cao nhất?"* hoặc *"Tóm tắt bù tiến độ"* để phân tích chuyên sâu.`;
    }
}

const GeminiAI = new GeminiAIService();
window.GeminiAI = GeminiAI;

// --- TELEGRAM MESSAGE SENDER CLIENT SIDE ---
async function sendTelegramMessage(message) {
    const token = localStorage.getItem("telegram_bot_token") || "";
    const chatId = localStorage.getItem("telegram_chat_id") || "";
    if (!token || !chatId) {
        console.warn("Telegram notification skipped: Bot Token or Chat ID not configured.");
        return false;
    }
    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                chat_id: chatId,
                text: message,
                parse_mode: "HTML"
            })
        });
        const data = await response.json();
        return data.ok;
    } catch (e) {
        console.error("Failed to send Telegram message:", e);
        return false;
    }
}
