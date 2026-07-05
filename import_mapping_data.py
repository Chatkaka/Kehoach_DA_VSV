import json
import re
import sys
import models
from database import engine, SessionLocal

sys.stdout.reconfigure(encoding='utf-8')

def clean_wbs(wbs_str):
    if not wbs_str:
        return ""
    # Split by spaces and take the first one
    parts = wbs_str.split()
    if not parts:
        return ""
    # Clean up dots or trailing chars
    wbs = parts[0].strip()
    # Replace spaces inside (like HT 01.01 -> HT01.01)
    wbs = wbs.replace(" ", "")
    return wbs

def infer_dept(wbs):
    wbs_lower = wbs.lower()
    if ".kd." in wbs_lower:
        return "KD"
    elif ".htkt." in wbs_lower:
        return "HTKT"
    elif ".dd.qh" in wbs_lower or ".qh" in wbs_lower:
        return "QHTK"
    elif ".gpmb" in wbs_lower:
        return "GPMB"
    else:
        return "BQLDA"

def main():
    print("=== NẠP DỮ LIỆU CẤU TRÚC MỚI TỪ PDF MAPPING ===")
    
    # Đọc file JSON đã trích xuất từ PDF
    try:
        with open("pdf_extracted_rows.json", "r", encoding="utf-8") as f:
            pdf_rows = json.load(f)
    except FileNotFoundError:
        print("Không tìm thấy file pdf_extracted_rows.json. Vui lòng chạy parse_mapping_tables.py trước.")
        return

    db = SessionLocal()
    try:
        # Xóa dữ liệu cũ
        db.query(models.Task).delete()
        db.query(models.Budget).delete()
        db.query(models.ActualSpending).delete()
        db.commit()
        print("Đã dọn dẹp cơ sở dữ liệu cũ.")

        # Định nghĩa các Level 1 Goals (Mục tiêu chung) và Giai đoạn (Phase ID) tương ứng
        level1_definitions = {
            "7": ("KĐT Ven Sông Vinh (Vốn DN) - Vận hành thiết kế", 1),
            "9": ("Hoàn tất thủ tục pháp lý đủ điều kiện khởi công & mở bán", 1),
            "10": ("Khảo sát, thiết kế và thẩm định kỹ thuật", 1),
            "12": ("Bàn giao mặt bằng các dự án BĐS (GPMB)", 1),
            "2": ("Quản lý thi công xây dựng", 2),
            "1": ("Nghiệm thu hoàn thành bàn giao đưa vào sử dụng", 3),
            "11": ("Bàn giao nhà & cấp GCNQSDĐ cho khách hàng", 4)
        }

        # Tạo và nạp các Level 1 Tasks trước
        level1_tasks = {}
        for stt_l1, (name, phase_id) in level1_definitions.items():
            task = models.Task(
                project_id=1,
                ma_ngan_sach=f"TD.BĐS.{stt_l1}",
                stt=stt_l1,
                phase_id=phase_id,
                ten_cong_viec=name,
                phong_ban_thuc_hien="BQLDA",
                co_quan_giai_quyet="-",
                kpi_trong_yeu="Mục tiêu lớn",
                dieu_kien_ghi_nhan="Hoàn thành các công việc con",
                tien_do=0.0,
                trang_thai="Todo"
            )
            db.add(task)
            db.flush()
            level1_tasks[stt_l1] = task.id

        print(f"Đã tạo {len(level1_tasks)} nhóm công việc Cấp 1.")

        imported_count = 0
        project_total_budget = 0.0

        seen_wbs = set()
        # Duyệt qua các dòng dữ liệu để nạp Cấp 2
        for idx, item in enumerate(pdf_rows):
            row = item["row_data"]
            wbs_raw = row[3].strip()
            name_raw = row[4].strip()
            deadline = row[9].strip()
            condition = row[10].strip()
            outcome = row[11].strip()
            risk = row[12].strip()
            action = row[13].strip()
            result = row[14].strip()

            # Skip if name is empty (sometimes table extracts empty cells)
            if not name_raw:
                continue

            # Skip if it is the parent itself (e.g. Row 2: "7. KĐT Ven Sông Vinh (Vốn DN)")
            if name_raw == "7. KĐT Ven Sông Vinh (Vốn DN)" or name_raw == "1. KĐT Ven Sông Vinh (Vốn DN)" or name_raw == "KĐT Ven Sông Vinh (Vốn DN)":
                continue

            # Bóc tách STT từ Tên công việc (Col 4)
            # ví dụ: "7.1. PLHĐ TVTK: Tư vấn..." -> STT = "7.1", Tên = "PLHĐ TVTK: Tư vấn..."
            match = re.match(r'^(\d+(\.\d+)*)\.?\s*(.*)$', name_raw)
            
            stt_val = ""
            name_val = name_raw
            if match:
                stt_val = match.group(1)
                name_val = match.group(3).strip()
            
            # Gán STT tạm nếu không tự trích xuất được từ câu báo cáo
            if not stt_val:
                # Nếu thuộc nhóm "Chủ trương chuyển NOXH..." (Page 9)
                if "chủ trương" in name_raw.lower() or "đăng ký" in name_raw.lower() or "cấp phép" in name_raw.lower() or "mở bán" in name_raw.lower():
                    # Gán STT phụ thuộc vào dòng trong page 9
                    stt_val = f"9.{idx}"
                elif "gpmb" in name_raw.lower():
                    stt_val = f"12.{idx}"
                elif "thông báo" in name_raw.lower() or "bàn giao" in name_raw.lower():
                    stt_val = f"11.{idx}"
                else:
                    stt_val = f"7.{idx}"

            # Xác định Phase ID và Parent STT dựa trên tiền tố của STT
            stt_parts = stt_val.split('.')
            parent_prefix = stt_parts[0]
            
            if parent_prefix not in level1_definitions:
                # Fallback mapping
                if stt_val.startswith('7.'):
                    parent_prefix = '7'
                elif stt_val.startswith('10.'):
                    parent_prefix = '10'
                elif stt_val.startswith('2.'):
                    parent_prefix = '2'
                elif stt_val.startswith('1.'):
                    parent_prefix = '1'
                else:
                    parent_prefix = '7' # Mặc định giai đoạn 1

            phase_id = level1_definitions[parent_prefix][1]

            # Làm sạch mã ngân sách WBS
            wbs = clean_wbs(wbs_raw)
            if not wbs:
                wbs = f"DA.KĐTVSV.GEN.{stt_val}"
            else:
                wbs = f"{wbs}.{stt_val}"

            if wbs in seen_wbs:
                wbs = f"{wbs}.R{idx}"
            seen_wbs.add(wbs)
            
            # Xác định phòng ban
            phong_ban = infer_dept(wbs)

            # Xác định tiến độ & trạng thái dựa vào kết quả "Theo dõi kết quả" (Col 14)
            tien_do = 0.0
            trang_thai = "Todo"
            if "hoàn thành" in result.lower() or "đã tuyển" in result.lower() or "đã hoàn thành" in result.lower():
                tien_do = 100.0
                trang_thai = "Done"
            elif "đang" in result.lower() or "đã ký" in result.lower():
                tien_do = 50.0
                trang_thai = "In-Progress"

            # Lưu công việc
            task = models.Task(
                project_id=1,
                ma_ngan_sach=wbs,
                stt=stt_val,
                phase_id=phase_id,
                ten_cong_viec=name_val,
                phong_ban_thuc_hien=phong_ban,
                co_quan_giai_quyet="CQNN / CĐT",
                kpi_trong_yeu=outcome or "Đúng thời hạn & Đạt chất lượng",
                dieu_kien_ghi_nhan=condition or "Có hồ sơ bàn giao/Quyết định phê duyệt",
                tien_do=tien_do,
                trang_thai=trang_thai
            )
            db.add(task)
            db.flush()

            # Phân bổ ngân sách giả định
            # Tổng ngân sách: deterministic dummy từ 200 đến 1000 triệu
            ngan_sach_tong = float((idx % 8 + 3) * 100) # 300, 400, ..., 1000
            kh_2026 = ngan_sach_tong * 0.4
            quy_1_2026 = ngan_sach_tong * 0.15
            quy_2_2026 = ngan_sach_tong * 0.15
            t1_2025 = ngan_sach_tong * 0.05
            t2_2025 = ngan_sach_tong * 0.05
            t3_2025 = ngan_sach_tong * 0.05
            t4_2025 = ngan_sach_tong * 0.05
            t5_2026 = ngan_sach_tong * 0.05
            t6_2026 = ngan_sach_tong * 0.05

            budget = models.Budget(
                task_id=task.id,
                ngan_sach_tong=ngan_sach_tong,
                kh_2026=kh_2026,
                quy_1_2026=quy_1_2026,
                quy_2_2026=quy_2_2026,
                thang_01_2025=t1_2025,
                thang_02_2025=t2_2025,
                thang_03_2025=t3_2025,
                thang_04_2025=t4_2025,
                thang_05_2026=t5_2026,
                thang_06_2026=t6_2026
            )
            db.add(budget)
            imported_count += 1

        db.commit()
        print(f"Đã nạp xong {imported_count} công việc Cấp 2. Đang tiến hành Roll-up lên Cấp 1...")

        # 5. Thực hiện Roll-up từ Cấp 2 lên Cấp 1
        remaining_tasks = db.query(models.Task).all()
        task_by_stt = {t.stt: t for t in remaining_tasks}

        # Reset ngân sách của Cấp 1
        for t in remaining_tasks:
            dot_count = len(t.stt.split('.')) - 1
            if dot_count == 0: # Cấp 1
                b = db.query(models.Budget).filter(models.Budget.task_id == t.id).first()
                if not b:
                    b = models.Budget(task_id=t.id)
                b.ngan_sach_tong = 0.0
                b.kh_2026 = 0.0
                b.quy_1_2026 = 0.0
                b.quy_2_2026 = 0.0
                b.thang_01_2025 = 0.0
                b.thang_02_2025 = 0.0
                b.thang_03_2025 = 0.0
                b.thang_04_2025 = 0.0
                b.thang_05_2026 = 0.0
                b.thang_06_2026 = 0.0
                db.add(b)
        db.commit()

        # Cộng ngân sách Cấp 2 vào Cấp 1
        for task in remaining_tasks:
            stt_parts = task.stt.split('.')
            if len(stt_parts) <= 1:
                # Cấp 1
                continue
            
            parent_stt = stt_parts[0]
            parent_task = task_by_stt.get(parent_stt)

            if parent_task:
                child_budget = task.budget
                parent_budget = parent_task.budget
                
                if child_budget and parent_budget:
                    parent_budget.ngan_sach_tong += child_budget.ngan_sach_tong
                    parent_budget.kh_2026 += child_budget.kh_2026
                    parent_budget.quy_1_2026 += child_budget.quy_1_2026
                    parent_budget.quy_2_2026 += child_budget.quy_2_2026
                    parent_budget.thang_01_2025 += child_budget.thang_01_2025
                    parent_budget.thang_02_2025 += child_budget.thang_02_2025
                    parent_budget.thang_03_2025 += child_budget.thang_03_2025
                    parent_budget.thang_04_2025 += child_budget.thang_04_2025
                    parent_budget.thang_05_2026 += child_budget.thang_05_2026
                    parent_budget.thang_06_2026 += child_budget.thang_06_2026
                    db.add(parent_budget)

        db.commit()

        # Tính tổng ngân sách dự án (bằng tổng các Cấp 1)
        level_1_tasks = [t for t in remaining_tasks if len(t.stt.split('.')) == 1]
        project_total = sum(t.budget.ngan_sach_tong for t in level_1_tasks if t.budget)

        project = db.query(models.Project).filter(models.Project.id == 1).first()
        if not project:
            project = models.Project(id=1, ten_du_an="Ven Sông Vinh", tong_ngan_sach=project_total)
        else:
            project.tong_ngan_sach = project_total
        db.add(project)
        db.commit()

        final_count = db.query(models.Task).count()
        print("--------------------------------------------------")
        print("CẤP NHẬT CẤU TRÚC HỆ THỐNG MỚI THÀNH CÔNG!")
        print(f"Tổng số công việc nạp vào DB: {final_count}")
        print(f"Tổng ngân sách dự án sau roll-up: {project_total:,.2f} Trđ")

    except Exception as e:
        db.rollback()
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
