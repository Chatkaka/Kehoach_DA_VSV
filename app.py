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
            
            # Button to export WBS tasks to Excel from Streamlit
            try:
                export_res = requests.get(f"{API_URL}/api/tasks/export")
                if export_res.status_code == 200:
                    st.download_button(
                        label="📥 Xuất Cấu trúc WBS sang file Excel (Giữ nguyên cấu trúc)",
                        data=export_res.content,
                        file_name="VenSongVinh_WBS_KeHoach.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="streamlit_export_excel"
                    )
            except Exception as e:
                st.warning("Không thể tạo liên kết tải file Excel từ backend.")
            
            # Select task
            task_options = {f"{t['stt']} - {t['ten_cong_viec'][:50]}...": t["id"] for t in tasks if t["level"] in [2, 3]}
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
            st.markdown("---")
            st.markdown("### ➕ Thêm công việc Cấp 3 mới vào sau công việc Cấp 2")
            
            # Select parent Level 2 task
            parent_options = {f"{t['stt']} - {t['ten_cong_viec'][:50]}...": t["stt"] for t in tasks if t["level"] == 2}
            
            if parent_options:
                selected_parent_label = st.selectbox("Chọn công việc Cấp 2 cha:", list(parent_options.keys()), key="select_parent_task")
                selected_parent_stt = parent_options[selected_parent_label]
                
                new_task_name = st.text_input("Tên công việc Cấp 3 mới:", placeholder="Ví dụ: Lập và trình duyệt báo cáo đánh giá tác động môi trường chi tiết")
                
                c_add1, c_add2, c_add3 = st.columns(3)
                with c_add1:
                    new_task_pb = st.text_input("Đơn vị/Phòng ban thực hiện:", value="PTDA")
                with c_add2:
                    new_task_cq = st.text_input("Cơ quan giải quyết/phê duyệt:", value="-")
                with c_add3:
                    new_task_kpi = st.text_input("KPI trọng yếu:", value="1")
                    
                c_add4, c_add5 = st.columns(2)
                with c_add4:
                    new_task_dk = st.text_input("Điều kiện ghi nhận kết quả:", value="-")
                with c_add5:
                    new_task_budget = st.number_input("Ngân sách tổng đề xuất (Trđ):", min_value=0.0, value=0.0, step=10.0)
                    
                if st.button("➕ Thêm công việc Cấp 3"):
                    if not new_task_name.strip():
                        st.warning("Vui lòng nhập tên công việc.")
                    else:
                        try:
                            add_res = requests.post(
                                f"{API_URL}/api/tasks",
                                json={
                                    "parent_stt": selected_parent_stt,
                                    "ten_cong_viec": new_task_name,
                                    "phong_ban_thuc_hien": new_task_pb,
                                    "co_quan_giai_quyet": new_task_cq,
                                    "kpi_trong_yeu": new_task_kpi,
                                    "dieu_kien_ghi_nhan": new_task_dk,
                                    "ngan_sach": new_task_budget
                                }
                            )
                            if add_res.status_code == 200:
                                st.success(f"Đã thêm mới thành công công việc Cấp 3 dưới mục {selected_parent_stt}!")
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {add_res.json()['detail']}")
                        except Exception as ex:
                            st.error(f"Lỗi kết nối máy chủ: {ex}")
            else:
                st.warning("Không tìm thấy công việc Cấp 2 nào để làm cha.")
                
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
    st.markdown("### 📁 Tải dữ liệu báo cáo để AI bóc tách & điền tự động (Excel / Txt)")
    
    # Select run mode
    run_mode = st.radio(
        "Chọn hình thức bóc tách dữ liệu:",
        [
            "Bóc tách bằng AI Gemini (Báo cáo tiến độ tự do)",
            "Đọc trực tiếp từ cột Excel (Bảng đã có Mã WBS/STT và Tiến độ %)"
        ]
    )
    
    if run_mode == "Bóc tách bằng AI Gemini (Báo cáo tiến độ tự do)":
        st.info("Tải lên tệp tin văn bản (.txt) hoặc bảng tính Excel (.xlsx, .xls) chứa các câu báo cáo tiến độ thô để AI bóc tách hàng loạt.")
        uploaded_file = st.file_uploader("Chọn tệp báo cáo tiến độ tự do:", type=["txt", "xlsx", "xls"], key="gemini_uploader")
        
        if uploaded_file is not None:
            lines = []
            is_excel = uploaded_file.name.endswith(('.xlsx', '.xls'))
            
            if is_excel:
                try:
                    df_upload = pd.read_excel(uploaded_file)
                    st.success("Tải tệp Excel thành công!")
                    st.write("Xem thử dữ liệu bảng tính:")
                    st.dataframe(df_upload.head(5), use_container_width=True)
                    
                    col_options = list(df_upload.columns)
                    selected_col = st.selectbox(
                        "Chọn cột chứa câu báo cáo tiến độ thô để AI đọc:",
                        col_options,
                        key="gemini_excel_col"
                    )
                    lines = df_upload[selected_col].dropna().astype(str).str.strip().tolist()
                    lines = [line for line in lines if line]
                except Exception as e:
                    st.error(f"Lỗi đọc file Excel: {e}")
            else:
                file_contents = uploaded_file.read().decode("utf-8")
                lines = [line.strip() for line in file_contents.split("\n") if line.strip()]
            
            if lines:
                st.write(f"Tìm thấy {len(lines)} dòng báo cáo trong tệp:")
                st.code("\n".join(lines[:10]) + ("\n..." if len(lines) > 10 else ""))
                
                if st.button("🚀 Bắt đầu AI đọc, bóc tách và điền dữ liệu", key="run_ai_batch"):
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
                    
    else:
        st.info("Tải lên tệp Excel (.xlsx, .xls) đã phân cột rõ ràng để đồng bộ trực tiếp tiến độ mà không cần AI.")
        uploaded_file = st.file_uploader("Chọn tệp Excel tiến độ cấu trúc:", type=["xlsx", "xls"], key="direct_uploader")
        
        if uploaded_file is not None:
            try:
                df_upload = pd.read_excel(uploaded_file)
                st.success("Tải tệp Excel thành công!")
                st.write("Xem thử dữ liệu bảng tính:")
                st.dataframe(df_upload.head(5), use_container_width=True)
                
                col_options = list(df_upload.columns)
                
                c_col1, c_col2, c_col3 = st.columns(3)
                with c_col1:
                    wbs_col = st.selectbox("Chọn cột chứa Mã WBS hoặc STT:", col_options, key="direct_wbs_col")
                with c_col2:
                    prog_col = st.selectbox("Chọn cột chứa Tiến độ (%):", col_options, key="direct_prog_col")
                with c_col3:
                    status_col = st.selectbox("Chọn cột chứa Trạng thái (Nếu có):", ["-"] + col_options, key="direct_status_col")
                
                if st.button("🔄 Bắt đầu Đồng bộ dữ liệu trực tiếp", key="run_direct_batch"):
                    # Fetch all tasks to map WBS/STT to DB ID
                    all_tasks = requests.get(f"{API_URL}/api/tasks").json()
                    task_map = {}
                    for t in all_tasks:
                        task_map[str(t["ma_ngan_sach"]).strip()] = t["id"]
                        task_map[str(t["stt"]).strip()] = t["id"]
                    
                    results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    total_rows = len(df_upload)
                    for idx, row in df_upload.iterrows():
                        wbs_val = str(row[wbs_col]).strip()
                        prog_val = float(row[prog_col]) if pd.notna(row[prog_col]) else 0.0
                        
                        # Determine status
                        status_val = "Todo"
                        if status_col != "-":
                            status_val = str(row[status_col]).strip()
                        else:
                            if prog_val >= 100.0:
                                status_val = "Done"
                            elif prog_val > 0.0:
                                status_val = "In-Progress"
                        
                        status_text.text(f"Đang xử lý dòng {idx+1}/{total_rows}: WBS/STT '{wbs_val}' -> {prog_val}%")
                        
                        # Lookup Task ID
                        task_id = task_map.get(wbs_val)
                        if not task_id:
                            # Try fuzzy match
                            matched = [tid for wbs_key, tid in task_map.items() if wbs_key.startswith(wbs_val) or wbs_val in wbs_key]
                            if matched:
                                task_id = matched[0]
                                
                        if task_id:
                            try:
                                res = requests.put(
                                    f"{API_URL}/api/tasks/{task_id}/progress?user_role={user_role}",
                                    json={
                                        "tien_do": prog_val,
                                        "trang_thai": status_val,
                                        "dieu_kien_ghi_nhan": "Cập nhật hàng loạt từ tệp Excel"
                                    }
                                )
                                if res.status_code == 200:
                                    results.append({
                                        "Mã WBS/STT": wbs_val,
                                        "Tiến độ mới": f"{prog_val}%",
                                        "Trạng thái": status_val,
                                        "Kết quả": "Thành công ✅"
                                    })
                                else:
                                    results.append({
                                        "Mã WBS/STT": wbs_val,
                                        "Tiến độ mới": f"{prog_val}%",
                                        "Trạng thái": status_val,
                                        "Kết quả": f"Thất bại: {res.json()['detail']} ❌"
                                    })
                            except Exception as ex:
                                results.append({
                                    "Mã WBS/STT": wbs_val,
                                    "Tiến độ mới": f"{prog_val}%",
                                    "Trạng thái": status_val,
                                    "Kết quả": f"Lỗi kết nối: {ex} ❌"
                                })
                        else:
                            results.append({
                                "Mã WBS/STT": wbs_val,
                                "Tiến độ mới": f"{prog_val}%",
                                "Trạng thái": status_val,
                                "Kết quả": "Không tìm thấy Mã WBS/STT ❌"
                            })
                        
                        progress_bar.progress((idx + 1) / total_rows)
                    
                    status_text.success("Hoàn thành đồng bộ trực tiếp tiến độ hàng loạt!")
                    df_results = pd.DataFrame(results)
                    st.dataframe(df_results, use_container_width=True)
            except Exception as e:
                st.error(f"Lỗi xử lý file Excel: {e}")

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

    st.markdown("---")
    st.markdown("### 💬 Phân tích & Hỏi đáp AI Gemini về Dự án")
    st.info("Nhập câu hỏi của bạn về dự án (ví dụ: 'Công việc nào đang trễ hạn?', 'Tóm tắt tình hình các Phase'). AI sẽ phân tích dữ liệu thực tế và phản hồi.")
    
    ai_question = st.text_input("Nhập câu hỏi cho AI Gemini:")
    if st.button("Hỏi AI Gemini", key="run_ai_chat"):
        if ai_question.strip():
            with st.spinner("AI đang phân tích dữ liệu dự án..."):
                try:
                    # 1. Fetch current WBS stats and tasks to build context
                    stats_res = requests.get(f"{API_URL}/api/stats").json()
                    all_tasks = requests.get(f"{API_URL}/api/tasks").json()
                    
                    # Format a concise context for Gemini
                    tasks_summary = []
                    for t in all_tasks[:85]:  # Limit to 85 tasks
                        tasks_summary.append(f"- STT {t['stt']} | WBS {t['ma_ngan_sach']} | {t['ten_cong_viec']} | Tiến độ: {t['tien_do']}% | Trạng thái: {t['trang_thai']}")
                    
                    context = f"""
Thông tin dự án Ven Sông Vinh:
- Tổng ngân sách: {stats_res['tong_ngan_sach']:,.2f} Trđ
- Lũy kế thực chi: {stats_res['tong_thuc_chi']:,.2f} Trđ
- Ngân sách còn lại: {stats_res['con_lai']:,.2f} Trđ
- Tiến độ trung bình: {stats_res['tien_do_trung_binh']:.2f}%
- Trạng thái công việc: Todo ({stats_res['trang_thai_tasks']['Todo']}), In-Progress ({stats_res['trang_thai_tasks']['In-Progress']}), Done ({stats_res['trang_thai_tasks']['Done']}), Delayed ({stats_res['trang_thai_tasks']['Delayed']})
- Số mã ngân sách bị khóa do vượt chi: {stats_res['so_wbs_bi_khoa']}

Danh sách một số công việc tiêu biểu:
{chr(10).join(tasks_summary)}
"""
                    payload = {
                        "question": ai_question,
                        "context": context
                    }
                    if "gemini_api_key" in st.session_state and st.session_state.gemini_api_key:
                        payload["api_key"] = st.session_state.gemini_api_key
                        
                    res = requests.post(f"{API_URL}/api/ai/chat", json=payload)
                    if res.status_code == 200:
                        st.markdown("**Phản hồi của AI Gemini:**")
                        st.markdown(res.json()["response"])
                    else:
                        st.error(f"Lỗi phân tích AI: {res.json()['detail']}")
                except Exception as e:
                    st.error(f"Lỗi kết nối AI: {e}")
        else:
            st.warning("Vui lòng nhập câu hỏi.")
