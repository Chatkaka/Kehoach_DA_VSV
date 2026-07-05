import openpyxl
import models
from database import engine, SessionLocal
import sys

sys.stdout.reconfigure(encoding='utf-8')

def to_float(val):
    if val is None:
        return 0.0
    try:
        if isinstance(val, str):
            val = val.replace(',', '').strip()
        return float(val)
    except ValueError:
        return 0.0

def parse_phase_from_stt(stt_val):
    if not stt_val:
        return 1
    
    stt_str = str(stt_val).strip()
    parts = stt_str.split('.')
    if not parts or not parts[0].isdigit():
        return 1
    
    try:
        prefix = int(parts[0])
        if 1 <= prefix <= 15:
            return 1
        elif 16 <= prefix <= 18:
            return 2
        elif 19 <= prefix <= 26:
            return 3
        elif 27 <= prefix <= 28:
            return 4
        else:
            return 1
    except ValueError:
        return 1

def main():
    print("Khởi tạo cấu trúc các bảng trong cơ sở dữ liệu...")
    models.Base.metadata.drop_all(bind=engine) # Drop first to rebuild with new STT column
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Thêm dự án mặc định
        project = models.Project(id=1, ten_du_an="Ven Sông Vinh", tong_ngan_sach=0.0)
        db.add(project)
        print("Đã khởi tạo dự án mặc định: Ven Sông Vinh")

        # 2. Thêm 4 Giai đoạn cốt lõi
        phases_data = [
            (1, "Hoàn thành pháp lý đủ điều kiện khởi công", "Pháp lý, quy hoạch, thiết kế cơ sở, cấp phép, lập tổng mức đầu tư."),
            (2, "Quản lý thi công", "Đấu thầu, cung ứng, thi công xây dựng, hạ tầng, cơ điện, nghiệm thu giai đoạn."),
            (3, "Nghiệm thu bàn giao đưa vào sử dụng", "Bàn giao đưa vào sử dụng, quyết toán dự án, kiểm toán, tất toán hợp đồng."),
            (4, "Bàn giao, cấp GCNQSDĐ cho khách hàng", "Bàn giao, cấp GCNQSDĐ và tài sản gắn liền với đất cho khách hàng.")
        ]

        for p_id, name, desc in phases_data:
            phase = models.Phase(id=p_id, ten_giai_doan=name, mo_ta=desc)
            db.add(phase)
            print(f"Đã thêm Giai đoạn {p_id}: {name}")
        
        db.commit()

        # 3. Đọc dữ liệu từ file Excel
        file_path = r"d:\AI Thực chiến\Kế hoạch DA VSV\Vòng đời dự án Bất động sản.xlsx"
        print(f"Đang đọc file Excel từ: {file_path}...")
        
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb.active

        print(f"Bắt đầu phân tích dữ liệu...")

        r = 0
        imported_count = 0
        seen_wbs = set()

        tasks_list = []

        for row in sheet.iter_rows(values_only=True):
            r += 1
            if r < 5:  # Bỏ qua 4 dòng đầu
                continue
            
            level = row[0]
            wbs = row[1]
            stt = row[2]
            name = row[3]
            
            if not name or name == "TỔNG DỰ ÁN":
                continue
            
            # Làm sạch dữ liệu CẤP
            level_val = None
            if level is not None:
                try:
                    level_val = int(level)
                except ValueError:
                    pass
            
            if level_val not in [1, 2, 3]:
                if stt:
                    parts = str(stt).strip().split('.')
                    level_val = min(len(parts), 3)
                else:
                    level_val = 3

            # Chuẩn hóa mã ngân sách (WBS)
            if not wbs:
                if stt:
                    wbs_candidate = f"TD.BĐS.GEN.{stt}"
                else:
                    wbs_candidate = f"TD.BĐS.GEN.ROW{r}"
            else:
                wbs_candidate = str(wbs).strip()

            if wbs_candidate in seen_wbs:
                wbs_candidate = f"{wbs_candidate}-R{r}"
            seen_wbs.add(wbs_candidate)

            phase_id = parse_phase_from_stt(stt)

            phong_ban = str(row[4]).strip() if row[4] else None
            co_quan = str(row[6]).strip() if row[6] else None
            kpi = str(row[7]).strip() if row[7] else None
            dieu_kien = str(row[11]).strip() if row[11] else None

            # Tạo đối tượng Task
            task = models.Task(
                project_id=1,
                ma_ngan_sach=wbs_candidate,
                stt=str(stt).strip() if stt else f"ROW{r}",
                phase_id=phase_id,
                ten_cong_viec=str(name).strip(),
                phong_ban_thuc_hien=phong_ban,
                co_quan_giai_quyet=co_quan,
                kpi_trong_yeu=kpi,
                dieu_kien_ghi_nhan=dieu_kien,
                tien_do=0.0,
                trang_thai="Todo"
            )
            db.add(task)
            db.flush()

            # Tạo ngân sách
            # Nếu excel có budget, dùng nó. Nếu không, gán dummy budget cho Level 3 tasks.
            excel_budget = max(to_float(row[25]), to_float(row[26]))
            
            ngan_sach_tong = 0.0
            kh_2026 = 0.0
            quy_1_2026 = 0.0
            quy_2_2026 = 0.0
            t1_2025 = 0.0
            t2_2025 = 0.0
            t3_2025 = 0.0
            t4_2025 = 0.0
            t5_2026 = 0.0
            t6_2026 = 0.0

            if excel_budget > 0:
                ngan_sach_tong = excel_budget
                kh_2026 = to_float(row[43])
                quy_1_2026 = to_float(row[53])
                quy_2_2026 = to_float(row[97])
                t1_2025 = to_float(row[64])
                t2_2025 = to_float(row[75])
                t3_2025 = to_float(row[86])
                t4_2025 = to_float(row[108])
                t5_2026 = to_float(row[119])
                t6_2026 = to_float(row[130])
            elif level_val == 3:
                # Gán dummy budget ngẫu nhiên nhưng nhất quán cho các công việc cấp 3
                # Ví dụ: từ 200 đến 1000 triệu đồng
                ngan_sach_tong = float((r % 9 + 2) * 100) # 200, 300, ..., 1000
                kh_2026 = ngan_sach_tong * 0.40
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
            
            # Lưu lại thông tin để xử lý cấp bậc sau này
            tasks_list.append({
                "id": task.id,
                "stt": task.stt,
                "level": level_val
            })

            if imported_count % 100 == 0:
                print(f"Đã nạp {imported_count} công việc vào DB...")

        db.commit()
        print("Đã nhập xong các tasks cấp 3 và khởi tạo. Đang thực hiện Roll-up ngân sách lên cấp 2 và cấp 1...")

        # 4. Thực hiện Roll-up ngân sách dựa trên cây STT
        # Load tất cả các tasks kèm budgets
        all_tasks = db.query(models.Task).all()
        task_by_stt = {t.stt: t for t in all_tasks}

        # Sắp xếp các tasks theo chiều dài STT giảm dần để tính toán từ dưới lên
        # Ví dụ: '1.1.1' -> '1.1' -> '1'
        sorted_tasks = sorted(all_tasks, key=lambda t: len(t.stt.split('.')), reverse=True)

        for task in sorted_tasks:
            stt_parts = task.stt.split('.')
            if len(stt_parts) <= 1:
                # Đây là cấp 1, không có parent để cộng lên nữa, ngân sách cấp 1 sẽ được cộng lên dự án sau
                continue
            
            # Parent STT là phần trước của dấu chấm cuối cùng
            parent_stt = ".".join(stt_parts[:-1])
            parent_task = task_by_stt.get(parent_stt)

            if parent_task:
                # Cộng ngân sách của con vào cha
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

        # Tính tổng ngân sách cho Dự án = tổng ngân sách của tất cả tasks Cấp 1
        level_1_tasks = db.query(models.Task).filter(models.Task.stt.like('%')).all()
        # filter out STTs with dots to keep only Level 1
        level_1_tasks = [t for t in level_1_tasks if len(t.stt.split('.')) == 1]
        
        project_total = sum(t.budget.ngan_sach_tong for t in level_1_tasks if t.budget)
        
        project = db.query(models.Project).filter(models.Project.id == 1).first()
        project.tong_ngan_sach = project_total
        db.add(project)
        db.commit()

        print("--------------------------------------------------")
        print(f"NHẬP DỮ LIỆU VÀ ROLL-UP THÀNH CÔNG!")
        print(f"Tổng số công việc đã nhập: {imported_count}")
        print(f"Tổng ngân sách toàn dự án: {project_total:,.2f} Trđ")

    except Exception as e:
        db.rollback()
        print(f"LỖI trong quá trình nhập dữ liệu: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
