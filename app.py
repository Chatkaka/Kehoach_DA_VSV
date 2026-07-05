import streamlit as st
import requests
import pandas as pd
import datetime

# Page configuration
st.set_page_config(
    page_title="Ven Sông Vinh - ERP ERP AI System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL (FastAPI Backend)
API_URL = "http://127.0.0.1:8000"

st.markdown("""
<style>
    .reportview-container {
        background: #0d1117;
    }
    h1 {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
    }
    .stButton>button {
        background-color: #6366f1;
        color: white;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #4f46e5;
    }
</style>
""", unsafe_allow_html=True)

st.title("💼 HỆ THỐNG QUẢN LÝ TIẾN ĐỘ & NGÂN SÁCH VEN SÔNG VINH")
st.caption("Giao diện điều hành & Nhập liệu (Layer 3: Permissions & Layer 2: Streamlit Interaction)")

# Sidebar for controls and roles
st.sidebar.header("🔑 PHÂN QUYỀN TRUY CẬP (LAYER 3)")
user_role = st.sidebar.selectbox(
    "Chọn vai trò của bạn:",
    ["Ban Quản lý Dự án (PM / Phòng ban)", "Admin / C-Level"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🔑 CẤU HÌNH AI GEMINI")
gemini_api_key = st.sidebar.text_input("Nhập Gemini API Key:", type="password", help="Nhập API Key để mở khóa sức mạnh AI")
if gemini_api_key:
    st.session_state.gemini_api_key = gemini_api_key
    import os
    os.environ["GEMINI_API_KEY"] = gemini_api_key
    st.sidebar.success("🔑 Đã lưu API Key thành công!")

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 Trạng thái máy chủ:")
try:
    health_res = requests.get(f"{API_URL}/api/stats")
    if health_res.status_code == 200:
        st.sidebar.success("🟢 Kết nối FastAPI Backend: OK")
    else:
        st.sidebar.warning("🟡 Cảnh báo: API Backend trả về mã lỗi")
except requests.exceptions.ConnectionError:
    st.sidebar.error("🔴 Lỗi: Không thể kết nối tới FastAPI Backend (127.0.0.1:8000)")

# Main Tabs
tabs = st.tabs([
    "📊 Dashboard C-Level", 
    "🗺️ Cấu trúc cây WBS", 
    "💸 Quản lý Giải ngân", 
    "🤖 Trợ lý AI & Rủi ro"
])

# ----------------- TAB 1: DASHBOARD C-LEVEL -----------------
with tabs[0]:
    st.subheader("📈 Chỉ số hiệu suất tài chính & tiến độ dự án")
    
    try:
        stats_res = requests.get(f"{API_URL}/api/stats").json()
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(
                label="Tổng ngân sách", 
                value=f"{stats_res['tong_ngan_sach']:,.2f} Trđ",
                help="Tính tổng từ WBS excel"
            )
        with c2:
            st.metric(
                label="Lũy kế thực chi đã duyệt", 
                value=f"{stats_res['tong_thuc_chi']:,.2f} Trđ",
                delta=f"{(stats_res['tong_thuc_chi'] / stats_res['tong_ngan_sach'] * 100):.2f}% giải ngân",
                delta_color="normal"
            )
        with c3:
            st.metric(
                label="Ngân sách còn lại", 
                value=f"{stats_res['con_lai']:,.2f} Trđ",
                help="Khả dụng chi tiêu"
            )
        with c4:
            st.metric(
                label="Tiến độ trung bình", 
                value=f"{stats_res['tien_do_trung_binh']:.2f}%"
            )

        # Alarm warning if WBS locked
        if stats_res["so_wbs_bi_khoa"] > 0:
            st.error(f"🚨 BÁO ĐỘNG ĐỎ: Đang có {stats_res['so_wbs_bi_khoa']} mã ngân sách (WBS) bị KHÓA do vượt chi (Hard Budget Gate)!")
            
        # Display S-Curve chart
        st.markdown("### 📈 Biểu đồ S-Curve chi tiết")
        scurve_res = requests.get(f"{API_URL}/api/s-curve").json()
        
        plan_df = pd.DataFrame(scurve_res["plan"])
        actual_df = pd.DataFrame(scurve_res["actual"])
        
        chart_data = pd.DataFrame({
            "Mốc thời gian": plan_df["period"],
            "Lũy kế Kế hoạch": plan_df["value"],
            "Lũy kế Thực chi": actual_df["value"]
        }).set_index("Mốc thời gian")
        
        st.line_chart(chart_data)

    except Exception as e:
        st.info("Vui lòng khởi động máy chủ FastAPI (`main.py`) để tải số liệu.")

# ----------------- TAB 2: CẤU TRÚC CÂY WBS -----------------
with tabs[1]:
    st.subheader("🗺️ Danh sách công việc theo 4 giai đoạn cốt lõi")
    
    phase_id = st.selectbox(
        "Chọn giai đoạn dự án:",
        [
            (1, "Giai đoạn 1: Hoàn thành pháp lý đủ điều kiện khởi công"),
            (2, "Giai đoạn 2: Quản lý thi công"),
            (3, "Giai đoạn 3: Nghiệm thu bàn giao đưa vào sử dụng"),
            (4, "Giai đoạn 4: Bàn giao, cấp GCNQSDĐ cho khách hàng")
        ],
        format_func=lambda x: x[1]
    )[0]
    
    try:
        tasks = requests.get(f"{API_URL}/api/tasks?phase_id={phase_id}").json()
        
        if not tasks:
            st.info("Không có công việc nào trong giai đoạn này.")
        else:
            # Convert to DataFrame to display
            df_tasks = pd.DataFrame([{
                "ID": t["id"],
                "STT": t["stt"],
                "Mã WBS": t["ma_ngan_sach"],
                "Cấp": t["level"],
                "Tên công việc": t["ten_cong_viec"],
                "Phòng ban thực hiện": t["phong_ban_thuc_hien"] or "-",
                "KPI trọng yếu": t["kpi_trong_yeu"] or "-",
                "Ngân sách (Trđ)": t["budget"]["ngan_sach_tong"] if t["budget"] else 0.0,
                "Tiến độ (%)": t["tien_do"],
                "Trạng thái": t["trang_thai"],
                "Bị khóa": "Bị khóa 🔒" if t["budget"] and t["budget"]["is_locked"] else "Bình thường"
            } for t in tasks])
            
            # Sort by STT hierarchically
            df_tasks = df_tasks.sort_values(
                by="STT", 
                key=lambda x: x.str.split('.').str.len()
            )
            
            st.dataframe(df_tasks, use_container_width=True, hide_index=True)
            
            # Form to update task progress (PM/Admin)
            st.markdown("### ✏️ Cập nhật tiến độ & trạng thái công việc")
            
            # Select task
            task_options = {f"{t['stt']} - {t['ten_cong_viec'][:50]}...": t["id"] for t in tasks if t["level"] == 3}
            if task_options:
                selected_task_label = st.selectbox("Chọn công việc cấp 3 cần cập nhật:", list(task_options.keys()))
                selected_task_id = task_options[selected_task_label]
                
                # Find current values
                curr_task = next(t for t in tasks if t["id"] == selected_task_id)
                
                c_p1, c_p2, c_p3 = st.columns(3)
                with c_p1:
                    new_progress = st.number_input(
                        "Tiến độ mới (%):", 
                        min_value=0.0, 
                        max_value=100.0, 
                        value=float(curr_task["tien_do"]),
                        step=5.0
                    )
                with c_p2:
                    new_status = st.selectbox(
                        "Trạng thái mới:",
                        ["Todo", "In-Progress", "Done", "Delayed"],
                        index=["Todo", "In-Progress", "Done", "Delayed"].index(curr_task["trang_thai"])
                    )
                with c_p3:
                    new_cond = st.text_input(
                        "Điều kiện ghi nhận kết quả:",
                        value=curr_task["dieu_kien_ghi_nhan"] or ""
                    )
                
                if st.button("Cập nhật tiến độ"):
                    # Call API to update progress
                    res = requests.put(
                        f"{API_URL}/api/tasks/{selected_task_id}/progress?user_role={user_role}",
                        json={
                            "tien_do": new_progress,
                            "trang_thai": new_status,
                            "dieu_kien_ghi_nhan": new_cond
                        }
                    )
                    
                    if res.status_code == 200:
                        st.success(f"Cập nhật công việc {curr_task['stt']} thành công!")
                        st.rerun()
                    else:
                        st.error(f"LỖI CHỐT CHẶN (PHASE GATE LOOP): {res.json()['detail']}")
            else:
                st.info("Không có công việc cấp 3 nào khả dụng trong giai đoạn này.")
                
    except Exception as e:
        st.error(f"Lỗi: {e}")

# ----------------- TAB 3: QUẢN LÝ GIẢI NGÂN -----------------
with tabs[2]:
    st.subheader("💸 Lập đề xuất & Duyệt chi giải ngân thực tế (Layer 4 Hooks)")
    
    st.markdown("### 💳 Gửi đề xuất chi phí giải ngân")
    
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        spend_task_id = st.number_input("Nhập Database ID của Task cần chi (Xem trong bảng WBS):", min_value=1, step=1)
        spend_amount = st.number_input("Số tiền đề xuất chi (VND Triệu):", min_value=0.01, step=10.0)
    with c_s2:
        spend_user = st.text_input("Người đề xuất cập nhật:", value="Ban Kỹ Thuật Thi Công")
        spend_doc = st.text_input("Chứng từ đính kèm (Link chứng từ/hóa đơn):", value="http://docs.corp/invoice123")
        
    if st.button("Phê duyệt và Ghi nhận thực chi"):
        # Make POST request to submit spending
        res = requests.post(
            f"{API_URL}/api/spending?user_role={user_role}",
            json={
                "task_id": int(spend_task_id),
                "so_tien_chi": float(spend_amount),
                "nguoi_cap_nhat": spend_user,
                "chung_tu_kem_theo": spend_doc,
                "trang_thai_duyet": "Approved"
            }
        )
        
        if res.status_code == 200:
            st.success("Yêu cầu giải ngân đã được kiểm tra và DUYỆT thành công (Hard Budget Gate: Đạt yêu cầu).")
            st.rerun()
        else:
            st.error(f"❌ CHỐT CHẶN BÁO ĐỘNG ĐỎ (HARD BUDGET GATE BLOCKED): {res.json()['detail']}")

    st.markdown("---")
    st.markdown("### 📝 Lịch sử giải ngân thực tế gần đây")
    try:
        spendings = requests.get(f"{API_URL}/api/spending").json()
        if not spendings:
            st.info("Chưa có giao dịch giải ngân nào được thực hiện.")
        else:
            df_spend = pd.DataFrame([{
                "ID": s["id"],
                "Database Task ID": s["task_id"],
                "Mã WBS": s["ma_ngan_sach"],
                "Tên công việc": s["ten_cong_viec"],
                "Số tiền chi (Trđ)": s["so_tien_chi"],
                "Ngày chi": s["ngay_chi"],
                "Người cập nhật": s["nguoi_cap_nhat"],
                "Chứng từ": s["chung_tu_kem_theo"],
                "Trạng thái": s["trang_thai_duyet"]
            } for s in spendings])
            st.dataframe(df_spend, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Lỗi tải lịch sử chi tiêu: {e}")

# ----------------- TAB 4: TRỢ LÝ AI & RỦI RO -----------------
with tabs[3]:
    st.subheader("🤖 Trợ lý AI thông minh & Phân tích rủi ro tài chính (Gemini Pro)")
    
    st.markdown("### 💬 Cập nhật tiến độ bằng Ngôn ngữ tự nhiên")
    st.info("Mẹo: Nhập báo cáo dạng tự do, ví dụ: 'Hôm nay Ban GPMB đã hoàn thành đo đạc kiểm đếm đền bù đất mã 8.2.1'")
    
    ai_text_input = st.text_area("Nhập văn bản thô báo cáo của phòng ban:")
    if st.button("Gửi cho Trợ lý AI xử lý"):
        if ai_text_input.strip():
            with st.spinner("AI đang phân tích và bóc tách dữ liệu..."):
                payload = {"text": ai_text_input}
                if "gemini_api_key" in st.session_state and st.session_state.gemini_api_key:
                    payload["api_key"] = st.session_state.gemini_api_key
                res = requests.post(
                    f"{API_URL}/api/ai/parse",
                    json=payload
                )
                
                if res.status_code == 200:
                    data = res.json()
                    st.success(data["message"])
                    st.json(data["task"])
                else:
                    st.error(f"Lỗi xử lý AI: {res.json()['detail']}")
        else:
            st.warning("Vui lòng nhập văn bản thông báo.")

    st.markdown("---")
    st.markdown("### 📁 Tải dữ liệu báo cáo để AI bóc tách & điền tự động")
    st.info("Tải lên tệp tin văn bản (.txt) chứa các câu báo cáo tiến độ thô để AI bóc tách hàng loạt.")
    
    uploaded_file = st.file_uploader("Chọn tệp văn bản báo cáo:", type=["txt"])
    if uploaded_file is not None:
        file_contents = uploaded_file.read().decode("utf-8")
        lines = [line.strip() for line in file_contents.split("\n") if line.strip()]
        
        st.write(f"Tìm thấy {len(lines)} dòng báo cáo trong tệp:")
        st.code("\n".join(lines[:10]) + ("\n..." if len(lines) > 10 else ""))
        
        if st.button("🚀 Bắt đầu AI đọc, bóc tách và điền dữ liệu"):
            results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, line in enumerate(lines):
                status_text.text(f"Đang xử lý dòng {idx+1}/{len(lines)}: '{line[:40]}...'")
                payload = {"text": line}
                if "gemini_api_key" in st.session_state and st.session_state.gemini_api_key:
                    payload["api_key"] = st.session_state.gemini_api_key
                
                try:
                    res = requests.post(f"{API_URL}/api/ai/parse", json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        results.append({
                            "Báo cáo gốc": line,
                            "Mã trích xuất": data["task"]["ma_ngan_sach"],
                            "Tên công việc": data["task"]["ten_cong_viec"],
                            "Tiến độ": f"{data['task']['tien_do']}%",
                            "Trạng thái": data["task"]["trang_thai"],
                            "Kết quả": "Thành công ✅"
                        })
                    else:
                        results.append({
                            "Báo cáo gốc": line,
                            "Mã trích xuất": "Lỗi",
                            "Tên công việc": "-",
                            "Tiến độ": "-",
                            "Trạng thái": "-",
                            "Kết quả": f"Thất bại (Chốt chặn hoặc Lỗi WBS) ❌"
                        })
                except Exception as ex:
                    results.append({
                        "Báo cáo gốc": line,
                        "Mã trích xuất": "Lỗi",
                        "Tên công việc": "-",
                        "Tiến độ": "-",
                        "Trạng thái": "-",
                        "Kết quả": f"Lỗi kết nối: {ex}"
                    })
                progress_bar.progress((idx + 1) / len(lines))
                
            status_text.success("Hoàn thành bóc tách và điền dữ liệu hàng loạt!")
            df_results = pd.DataFrame(results)
            st.dataframe(df_results, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🧠 CFO AI Risk Assessment (Gemini Pro)")
    
    risk_report_placeholder = st.empty()
    if st.button("Lấy báo cáo đánh giá CFO mới nhất"):
        with st.spinner("AI CFO đang phân tích ngân sách và thực chi..."):
            try:
                params = {}
                if "gemini_api_key" in st.session_state and st.session_state.gemini_api_key:
                    params["api_key"] = st.session_state.gemini_api_key
                res = requests.get(f"{API_URL}/api/ai/risk", params=params).json()
                st.markdown(res["risk_report"])
            except Exception as e:
                st.error(f"Lỗi khi lấy báo cáo đánh giá rủi ro AI: {e}")
