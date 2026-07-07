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

# Fetch users list from Backend for dynamic human resources permissions
try:
    res = requests.get(f"{API_URL}/api/users", timeout=3)
    if res.status_code == 200:
        db_users = res.json()
    else:
        db_users = []
except Exception:
    db_users = []

st.sidebar.header("🔑 PHÂN QUYỀN NHÂN SỰ & PHÒNG BAN")

if db_users:
    user_options = []
    user_map = {}
    for u in db_users:
        role_label = "Admin" if u["role"] == "Admin" else ("PM" if u["role"] == "PM" else ("Trưởng phòng" if u["role"] == "TruongPhong" else "Nhân viên"))
        dept_label = "Tất cả" if u["phong_ban"] == "All" else u["phong_ban"]
        display_name = f"{u['ho_ten']} ({role_label} - Phòng {dept_label})"
        user_options.append(display_name)
        user_map[display_name] = u
        
    selected_display = st.sidebar.selectbox("Chọn nhân sự thao tác:", user_options)
    active_user = user_map[selected_display]
    active_username = active_user["username"]
    active_role = active_user["role"]
    active_dept = active_user["phong_ban"]
else:
    # Fallback to default options if database/API is offline or empty
    st.sidebar.warning("Không thể tải danh sách nhân sự từ Backend.")
    selected_role = st.sidebar.selectbox(
        "Chọn vai trò mặc định:",
        ["Nhân viên thực hiện", "Ban Quản lý Dự án (PM / Phòng ban)", "Admin / C-Level"]
    )
    if selected_role == "Nhân viên thực hiện":
        active_username = "nv_ptda"
        active_role = "NhanVien"
        active_dept = "PTDA"
    elif selected_role == "Admin / C-Level":
        active_username = "admin"
        active_role = "Admin"
        active_dept = "All"
    else:
        active_username = "pm_dung"
        active_role = "PM"
        active_dept = "All"

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
    "📅 Báo cáo & Phê duyệt Tuần",
    "💸 Quản lý Giải ngân", 
    "🤖 Trợ lý AI & Rủi ro",
    "👥 Quản lý Nhân sự"
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
            status_mapping = {
                "Chưa thực hiện": "Todo",
                "Đang triển khai": "In-Progress",
                "Hoàn thành": "Done",
                "Trễ hạn": "Delayed"
            }
            reverse_status_mapping = {v: k for k, v in status_mapping.items()}

            df_tasks = pd.DataFrame([{
                "ID": t["id"],
                "STT": t["stt"],
                "Mã WBS": t["ma_ngan_sach"],
                "Cấp": t["level"],
                "Tên công việc": t["ten_cong_viec"],
                "Phòng ban thực hiện": t["phong_ban_thuc_hien"] or "-",
                "Hồ sơ đầu ra": t["ho_so_dau_ra"] or "-",
                "Thời hạn": t["thoi_han_hoan_thanh"] or "Tháng 06/2026",
                "Ngân sách (Trđ)": t["budget"]["ngan_sach_tong"] if t["budget"] else 0.0,
                "Tiến độ (%)": t["tien_do"],
                "Trạng thái": reverse_status_mapping.get(t["trang_thai"], t["trang_thai"]),
                "Kế hoạch tuần": t.get("ke_hoach_tuan") or "-",
                "Kết quả tuần": t.get("ket_qua_tuan") or "-",
                "Vướng mắc": t.get("vuong_mac_tuan") or "-",
                "Cách giải quyết": t.get("cach_giai_quyet") or "-",
                "Duyệt tuần": t.get("duyet_tuan") or "Chưa duyệt",
                "Bị khóa": "Bị khóa 🔒" if t["budget"] and t["budget"]["is_locked"] else "Bình thường"
            } for t in tasks])
            
            # Sort by STT hierarchically
            df_tasks = df_tasks.sort_values(
                by="STT", 
                key=lambda x: x.str.split('.').str.len()
            )
            
            # Dynamic styling based on hierarchical level
            def style_by_stt(row):
                stt = str(row["STT"])
                lv = len(stt.split('.'))
                if lv == 1:
                    return ['color: #38bdf8; font-weight: bold; background-color: rgba(56, 189, 248, 0.08)'] * len(row)
                elif lv == 2:
                    return ['color: #c084fc; font-weight: bold; background-color: rgba(168, 85, 247, 0.04)'] * len(row)
                elif lv == 3:
                    return ['color: #fb923c; font-weight: bold;'] * len(row)
                elif lv == 4:
                    return ['color: #e2e8f0;'] * len(row)
                else:
                    return ['color: #94a3b8; font-style: italic;'] * len(row)

            st.dataframe(
                df_tasks.style.apply(style_by_stt, axis=1), 
                use_container_width=True, 
                hide_index=True
            )
            
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
                    selected_status_vn = st.selectbox(
                        "Trạng thái mới:",
                        list(status_mapping.keys()),
                        index=list(status_mapping.values()).index(curr_task["trang_thai"])
                    )
                    new_status = status_mapping[selected_status_vn]
                with c_p3:
                    new_cond = st.text_input(
                        "Điều kiện ghi nhận kết quả:",
                        value=curr_task["dieu_kien_ghi_nhan"] or ""
                    )
                
                st.markdown("##### 📅 Báo cáo & Phê duyệt tuần")
                c_w1, c_w2 = st.columns(2)
                with c_w1:
                    new_ke_hoach_tuan = st.text_input("Kế hoạch tuần:", value=curr_task.get("ke_hoach_tuan") or "")
                    new_vuong_mac_tuan = st.text_input("Vướng mắc tuần:", value=curr_task.get("vuong_mac_tuan") or "")
                with c_w2:
                    new_ket_qua_tuan = st.text_input("Kết quả tuần:", value=curr_task.get("ket_qua_tuan") or "")
                    new_cach_giai_quyet = st.text_input("Cách thức giải quyết của CBQL/Phòng ban:", value=curr_task.get("cach_giai_quyet") or "")
                
                approval_options = ["Chưa duyệt", "Đã duyệt", "Không duyệt"]
                curr_approval = curr_task.get("duyet_tuan") if curr_task.get("duyet_tuan") in approval_options else "Chưa duyệt"
                new_duyet_tuan = st.selectbox(
                    "Trạng thái duyệt tuần (Dành cho CBQL/Phòng ban):",
                    approval_options,
                    index=approval_options.index(curr_approval)
                )
                
                if st.button("Cập nhật tiến độ & tuần"):
                    # Call API to update full task details including weekly data
                    res = requests.put(
                        f"{API_URL}/api/tasks/{selected_task_id}?username={active_username}",
                        json={
                            "ma_ngan_sach": curr_task["ma_ngan_sach"],
                            "ten_cong_viec": curr_task["ten_cong_viec"],
                            "phong_ban_thuc_hien": curr_task["phong_ban_thuc_hien"] or "-",
                            "co_quan_giai_quyet": curr_task["co_quan_giai_quyet"] or "-",
                            "ho_so_dau_ra": curr_task["ho_so_dau_ra"] or "-",
                            "dieu_kien_ghi_nhan": new_cond,
                            "thoi_han_hoan_thanh": curr_task["thoi_han_hoan_thanh"] or "2026-06-30",
                            "tien_do": new_progress,
                            "trang_thai": new_status,
                            "ngan_sach": curr_task["budget"]["ngan_sach_tong"] if curr_task["budget"] else 0.0,
                            "ke_hoach_tuan": new_ke_hoach_tuan,
                            "ket_qua_tuan": new_ket_qua_tuan,
                            "vuong_mac_tuan": new_vuong_mac_tuan,
                            "cach_giai_quyet": new_cach_giai_quyet,
                            "duyet_tuan": new_duyet_tuan
                        }
                    )
                    
                    if res.status_code == 200:
                        st.success(f"Cập nhật công việc {curr_task['stt']} thành công!")
                        st.rerun()
                    else:
                        st.error(f"LỖI HỆ THỐNG: {res.json()['detail']}")
            st.markdown("---")
            st.markdown("### ➕ Thêm công việc con chi tiết (Mọi Cấp độ)")
            
            # Select parent task (Any level is allowed now)
            parent_options = {f"{t['stt']} - {t['ten_cong_viec'][:50]}...": t["stt"] for t in tasks}
            
            if parent_options:
                selected_parent_label = st.selectbox("Chọn công việc cha:", list(parent_options.keys()), key="select_parent_task")
                selected_parent_stt = parent_options[selected_parent_label]
                
                new_task_name = st.text_input("Tên công việc con mới:", placeholder="Ví dụ: Báo cáo kỹ thuật chi tiết")
                
                c_add1, c_add2, c_add3 = st.columns(3)
                with c_add1:
                    new_task_pb = st.selectbox(
                        "Đơn vị/Phòng ban thực hiện:",
                        ["PTDA", "QHTK", "BQLDA", "GPMB", "KTKH"]
                    )
                with c_add2:
                    new_task_cq = st.text_input("Cơ quan giải quyết/phê duyệt:", value="-")
                with c_add3:
                    new_task_deliverables = st.text_input("Hồ sơ đầu ra:", value="-")
                    
                c_add4, c_add5, c_add6 = st.columns(3)
                with c_add4:
                    new_task_dk = st.text_input("Điều kiện ghi nhận kết quả:", value="-")
                with c_add5:
                    new_task_deadline_date = st.date_input("Thời hạn hoàn thành:", value=datetime.date(2026, 6, 30))
                    new_task_deadline = new_task_deadline_date.strftime("%Y-%m-%d")
                with c_add6:
                    new_task_budget = st.number_input("Ngân sách tổng đề xuất (Trđ):", min_value=0.0, value=0.0, step=10.0)
                    
                if st.button("➕ Thêm công việc con"):
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
                                    "ho_so_dau_ra": new_task_deliverables,
                                    "dieu_kien_ghi_nhan": new_task_dk,
                                    "thoi_han_hoan_thanh": new_task_deadline,
                                    "ngan_sach": new_task_budget
                                }
                            )
                            if add_res.status_code == 200:
                                st.success(f"Đã thêm mới thành công công việc con dưới mục {selected_parent_stt}!")
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {add_res.json()['detail']}")
                        except Exception as ex:
                            st.error(f"Lỗi kết nối máy chủ: {ex}")
            else:
                st.warning("Không tìm thấy công việc nào để làm cha.")
                
    except Exception as e:
        st.error(f"Lỗi: {e}")

# ----------------- TAB 3: KHAI BÁO & DUYỆT TUẦN -----------------
with tabs[2]:
    st.subheader("📅 Khai báo Kế hoạch tuần, Kết quả tuần và Giải quyết vướng mắc")
    st.info("Nhân viên thực hiện khai báo kế hoạch, kết quả và vướng mắc tuần. Cấp quản lý/CBQL duyệt và đưa ra cách thức giải quyết.")
    
    try:
        all_tasks = requests.get(f"{API_URL}/api/tasks").json()
        # Filter level >= 2
        weekly_tasks = [t for t in all_tasks if t["level"] >= 2]
        
        # Filters
        c_f1, c_f2 = st.columns([1, 2])
        with c_f1:
            weekly_status_filter = st.selectbox(
                "Lọc trạng thái duyệt tuần:",
                ["Tất cả", "Chưa duyệt", "Đã duyệt", "Không duyệt"],
                key="weekly_status_filter"
            )
        with c_f2:
            weekly_search = st.text_input("Tìm kiếm tên công việc / WBS:", value="", key="weekly_search")
            
        # Apply filters
        if weekly_status_filter != "Tất cả":
            weekly_tasks = [t for t in weekly_tasks if (t.get("duyet_tuan") or "Chưa duyệt") == weekly_status_filter]
        if weekly_search:
            weekly_tasks = [t for t in weekly_tasks if weekly_search.lower() in t["ten_cong_viec"].lower() or weekly_search.lower() in t["ma_ngan_sach"].lower() or weekly_search.lower() in t["stt"].lower()]
            
        # Display table
        if not weekly_tasks:
            st.info("Không có báo cáo tuần nào phù hợp.")
        else:
            df_weekly = pd.DataFrame([{
                "STT": t["stt"],
                "Mã WBS": t["ma_ngan_sach"],
                "Tên công việc": t["ten_cong_viec"],
                "Đơn vị": t["phong_ban_thuc_hien"] or "-",
                "Kế hoạch tuần": t.get("ke_hoach_tuan") or "-",
                "Kết quả tuần": t.get("ket_qua_tuan") or "-",
                "Vướng mắc": t.get("vuong_mac_tuan") or "-",
                "Giải quyết của CBQL": t.get("cach_giai_quyet") or "-",
                "Trạng thái duyệt": t.get("duyet_tuan") or "Chưa duyệt"
            } for t in weekly_tasks])
            
            # Sort by STT hierarchically
            df_weekly = df_weekly.sort_values(
                by="STT", 
                key=lambda x: x.str.split('.').str.len()
            )
            
            st.dataframe(
                df_weekly.style.apply(style_by_stt, axis=1), 
                use_container_width=True, 
                hide_index=True
            )
            
            # Form to update weekly info
            st.markdown("### 📝 Cập nhật Báo cáo & Phê duyệt Tuần")
            task_options_weekly = {f"{t['stt']} - {t['ten_cong_viec'][:50]}...": t["id"] for t in weekly_tasks}
            
            if task_options_weekly:
                selected_t_label = st.selectbox("Chọn công việc cần cập nhật báo cáo tuần:", list(task_options_weekly.keys()), key="select_task_weekly")
                selected_t_id = task_options_weekly[selected_t_label]
                curr_t = next(t for t in all_tasks if t["id"] == selected_t_id)
                
                # Role check
                is_manager = active_role in ("Admin", "PM", "TruongPhong")
                
                c_edit1, c_edit2 = st.columns(2)
                with c_edit1:
                    w_plan = st.text_input("Kế hoạch tuần:", value=curr_t.get("ke_hoach_tuan") or "", key=f"w_plan_{selected_t_id}")
                    w_obs = st.text_input("Vướng mắc tuần:", value=curr_t.get("vuong_mac_tuan") or "", key=f"w_obs_{selected_t_id}")
                with c_edit2:
                    w_result = st.text_input("Kết quả tuần:", value=curr_t.get("ket_qua_tuan") or "", key=f"w_result_{selected_t_id}")
                    w_sol = st.text_input(
                        "Cách thức giải quyết của CBQL/Phòng ban:", 
                        value=curr_t.get("cach_giai_quyet") or "", 
                        disabled=not is_manager,
                        key=f"w_sol_{selected_t_id}"
                    )
                
                app_options = ["Chưa duyệt", "Đã duyệt", "Không duyệt"]
                curr_app = curr_t.get("duyet_tuan") if curr_t.get("duyet_tuan") in app_options else "Chưa duyệt"
                w_app = st.selectbox(
                    "Trạng thái duyệt tuần (Chỉ dành cho Cấp quản lý/CBQL):",
                    app_options,
                    index=app_options.index(curr_app),
                    disabled=not is_manager,
                    key=f"w_app_{selected_t_id}"
                )
                
                if st.button("Lưu báo cáo tuần", key=f"save_weekly_{selected_t_id}"):
                    res = requests.put(
                        f"{API_URL}/api/tasks/{selected_t_id}?username={active_username}",
                        json={
                            "ma_ngan_sach": curr_t["ma_ngan_sach"],
                            "ten_cong_viec": curr_t["ten_cong_viec"],
                            "phong_ban_thuc_hien": curr_t["phong_ban_thuc_hien"] or "-",
                            "co_quan_giai_quyet": curr_t["co_quan_giai_quyet"] or "-",
                            "ho_so_dau_ra": curr_t["ho_so_dau_ra"] or "-",
                            "dieu_kien_ghi_nhan": curr_t["dieu_kien_ghi_nhan"] or "-",
                            "thoi_han_hoan_thanh": curr_t["thoi_han_hoan_thanh"] or "2026-06-30",
                            "tien_do": curr_t["tien_do"],
                            "trang_thai": curr_t["trang_thai"],
                            "ngan_sach": curr_t["budget"]["ngan_sach_tong"] if curr_t["budget"] else 0.0,
                            "ke_hoach_tuan": w_plan,
                            "ket_qua_tuan": w_result,
                            "vuong_mac_tuan": w_obs,
                            "cach_giai_quyet": w_sol,
                            "duyet_tuan": w_app
                        }
                    )
                    if res.status_code == 200:
                        st.success("Cập nhật báo cáo tuần thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {res.json()['detail']}")
                        
    except Exception as e:
        st.error(f"Lỗi kết nối tới backend: {e}")

# ----------------- TAB 4: QUẢN LÝ GIẢI NGÂN -----------------
with tabs[3]:
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
            f"{API_URL}/api/spending?user_role={active_role}",
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

# ----------------- TAB 5: TRỢ LÝ AI & RỦI RO -----------------
with tabs[4]:
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
                                    f"{API_URL}/api/tasks/{task_id}/progress?username={active_username}",
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

# ----------------- TAB 6: QUẢN LÝ NHÂN SỰ -----------------
with tabs[5]:
    st.subheader("👥 Hệ thống Quản trị & Phân quyền Nhân sự")
    
    if active_role != "Admin":
        st.error("🔒 Quyền hạn bị từ chối: Mục này chỉ dành cho Admin hệ thống.")
        st.info("Chỉ tài khoản có vai trò 'Admin' mới được quyền Thêm, Sửa, Xóa nhân sự.")
    else:
        st.success(f"🔓 Xin chào Admin: {active_user['ho_ten']}. Bạn có toàn quyền quản lý nhân sự.")
        
        try:
            users_res = requests.get(f"{API_URL}/api/users")
            if users_res.status_code == 200:
                current_users = users_res.json()
            else:
                current_users = []
        except Exception as e:
            st.error(f"Không thể kết nối đến Backend: {e}")
            current_users = []
            
        if current_users:
            df_users = pd.DataFrame([{
                "ID": u["id"],
                "Tên đăng nhập (Username)": u["username"],
                "Họ tên": u["ho_ten"],
                "Phòng ban": "Tất cả" if u["phong_ban"] == "All" else u["phong_ban"],
                "Vai trò": "Admin" if u["role"] == "Admin" else ("PM" if u["role"] == "PM" else ("Trưởng phòng" if u["role"] == "TruongPhong" else "Nhân viên"))
            } for u in current_users])
            
            st.markdown("### 📋 Danh sách nhân sự hiện tại")
            st.dataframe(df_users, use_container_width=True, hide_index=True)
            
            c_crud1, c_crud2 = st.columns(2)
            
            with c_crud1:
                st.markdown("#### ➕ Thêm nhân sự mới")
                new_username = st.text_input("Tên đăng nhập (username):", key="new_user_name").strip()
                new_fullname = st.text_input("Họ tên nhân sự:", key="new_user_fullname").strip()
                new_dept = st.selectbox("Phòng ban thực hiện:", ["PTDA", "QHTK", "BQLDA", "GPMB", "KTKH", "All"], key="new_user_dept")
                new_role = st.selectbox("Vai trò & Quyền hạn:", ["NhanVien", "TruongPhong", "PM", "Admin"], format_func=lambda x: "Nhân viên" if x=="NhanVien" else ("Trưởng phòng" if x=="TruongPhong" else ("PM" if x=="PM" else "Admin")), key="new_user_role")
                
                if st.button("Thêm nhân viên", key="btn_add_user"):
                    if not new_username or not new_fullname:
                        st.error("Vui lòng điền đầy đủ Tên đăng nhập và Họ tên.")
                    else:
                        res_add = requests.post(
                            f"{API_URL}/api/users?admin_username={active_username}",
                            json={
                                "username": new_username,
                                "ho_ten": new_fullname,
                                "phong_ban": new_dept,
                                "role": new_role
                            }
                        )
                        if res_add.status_code == 200:
                            st.success(f"Đã thêm nhân sự '{new_fullname}' thành công!")
                            st.rerun()
                        else:
                            st.error(f"Lỗi: {res_add.json()['detail']}")
                            
            with c_crud2:
                st.markdown("#### ⚙️ Điều chỉnh hoặc Xóa nhân sự")
                user_edit_options = {f"{u['ho_ten']} ({u['username']})": u for u in current_users}
                selected_edit_label = st.selectbox("Chọn nhân sự cần sửa/xóa:", list(user_edit_options.keys()))
                user_to_edit = user_edit_options[selected_edit_label]
                
                edit_username = st.text_input("Sửa Tên đăng nhập:", value=user_to_edit["username"], key="edit_user_name").strip()
                edit_fullname = st.text_input("Sửa Họ tên:", value=user_to_edit["ho_ten"], key="edit_user_fullname").strip()
                edit_dept = st.selectbox(
                    "Sửa Phòng ban:", 
                    ["PTDA", "QHTK", "BQLDA", "GPMB", "KTKH", "All"], 
                    index=["PTDA", "QHTK", "BQLDA", "GPMB", "KTKH", "All"].index(user_to_edit["phong_ban"]),
                    key="edit_user_dept"
                )
                edit_role = st.selectbox(
                    "Sửa Vai trò:", 
                    ["NhanVien", "TruongPhong", "PM", "Admin"], 
                    index=["NhanVien", "TruongPhong", "PM", "Admin"].index(user_to_edit["role"]),
                    format_func=lambda x: "Nhân viên" if x=="NhanVien" else ("Trưởng phòng" if x=="TruongPhong" else ("PM" if x=="PM" else "Admin")),
                    key="edit_user_role"
                )
                
                c_sub1, c_sub2 = st.columns(2)
                with c_sub1:
                    if st.button("Lưu Thay Đổi", key="btn_save_user"):
                        if not edit_username or not edit_fullname:
                            st.error("Tên đăng nhập và Họ tên không được để trống.")
                        else:
                            res_edit = requests.put(
                                f"{API_URL}/api/users/{user_to_edit['id']}?admin_username={active_username}",
                                json={
                                    "username": edit_username,
                                    "ho_ten": edit_fullname,
                                    "phong_ban": edit_dept,
                                    "role": edit_role
                                }
                            )
                            if res_edit.status_code == 200:
                                st.success("Cập nhật thông tin nhân sự thành công!")
                                st.rerun()
                            else:
                                st.error(f"Lỗi: {res_edit.json()['detail']}")
                                
                with c_sub2:
                    if st.button("🔴 Xóa Nhân Sự", key="btn_delete_user"):
                        res_del = requests.delete(
                            f"{API_URL}/api/users/{user_to_edit['id']}?admin_username={active_username}"
                        )
                        if res_del.status_code == 200:
                            st.success("Đã xóa nhân sự thành công!")
                            st.rerun()
                        else:
                            st.error(f"Lỗi: {res_del.json()['detail']}")
