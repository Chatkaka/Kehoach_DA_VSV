import sys
# Add workspace directory to python path
sys.path.append(r"d:\AI Thực chiến\Kế hoạch DA VSV")

import database
import models

sys.stdout.reconfigure(encoding='utf-8')

def main():
    db = database.SessionLocal()
    try:
        print("=== BẮT ĐẦU DỌN DẸP & XÓA CÔNG VIỆC THEO YÊU CẦU ===")
        
        # 1. Lấy tổng số task ban đầu
        initial_count = db.query(models.Task).count()
        print(f"Tổng số công việc ban đầu trong cơ sở dữ liệu: {initial_count}")

        # 2. Xóa các công việc Cấp 4 trở lên (STT có >= 3 dấu chấm, nghĩa là split theo '.' có >= 4 phần tử)
        all_tasks = db.query(models.Task).all()
        to_delete_lvl4 = []
        for t in all_tasks:
            if len(t.stt.split('.')) >= 4:
                to_delete_lvl4.append(t)
        
        print(f"Số lượng công việc Cấp 4+ phát hiện cần xóa: {len(to_delete_lvl4)}")
        
        # 3. Xóa các công việc thuộc phòng KD và QLVH & CT
        # Chúng ta lọc các task chưa bị đưa vào danh sách xóa cấp 4
        to_delete_dept = db.query(models.Task).filter(
            models.Task.phong_ban_thuc_hien.in_(['KD', 'QLVH & CT'])
        ).all()
        
        # Lọc trùng lặp giữa 2 danh sách
        to_delete_lvl4_ids = {t.id for t in to_delete_lvl4}
        to_delete_dept_unique = [t for t in to_delete_dept if t.id not in to_delete_lvl4_ids]
        print(f"Số lượng công việc thuộc phòng Kinh Doanh / QLVH & CT cần xóa (không trùng với Cấp 4+): {len(to_delete_dept_unique)}")

        # Tổng hợp các tasks cần xóa
        final_delete_list = to_delete_lvl4 + to_delete_dept_unique
        print(f"Tổng số công việc sẽ bị xóa khỏi cơ sở dữ liệu: {len(final_delete_list)}")

        # Tiến hành xóa trong Session (gồm cả cascade delete cho Budgets & Actual Spendings)
        for t in final_delete_list:
            db.delete(t)
        
        db.commit()
        print("Đã thực hiện xóa các công việc khỏi DB.")

        # 4. Thực hiện tái tính toán (Recalculate) Roll-up ngân sách cho các công việc còn lại
        print("\nĐang tính toán lại (Roll-up) ngân sách cho các công việc còn lại...")
        
        # Reset ngân sách của tất cả các công việc Cấp 1 và Cấp 2 về 0 để cộng dồn lại
        remaining_tasks = db.query(models.Task).all()
        task_by_stt = {t.stt: t for t in remaining_tasks}

        for t in remaining_tasks:
            dot_count = len(t.stt.split('.')) - 1
            # Nếu là Cấp 1 hoặc Cấp 2, reset ngân sách về 0
            if dot_count < 2 and t.budget:
                b = t.budget
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

        # Thực hiện cộng dồn ngược từ dưới lên (Cấp 3 -> Cấp 2 -> Cấp 1)
        sorted_tasks = sorted(remaining_tasks, key=lambda t: len(t.stt.split('.')), reverse=True)

        for task in sorted_tasks:
            stt_parts = task.stt.split('.')
            if len(stt_parts) <= 1:
                # Cấp 1, không có parent
                continue
            
            parent_stt = ".".join(stt_parts[:-1])
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

        # Cập nhật tổng ngân sách dự án (bằng tổng các task Cấp 1)
        level_1_tasks = [t for t in remaining_tasks if len(t.stt.split('.')) == 1]
        project_total = sum(t.budget.ngan_sach_tong for t in level_1_tasks if t.budget)

        project = db.query(models.Project).filter(models.Project.id == 1).first()
        project.tong_ngan_sach = project_total
        db.add(project)
        db.commit()

        final_count = db.query(models.Task).count()
        print("--------------------------------------------------")
        print("CẬP NHẬT CƠ SỞ DỮ LIỆU THÀNH CÔNG!")
        print(f"Số lượng công việc còn lại trong DB: {final_count} (Đã xóa {initial_count - final_count} công việc)")
        print(f"Tổng ngân sách dự án mới sau khi tính toán lại: {project_total:,.2f} Trđ")

    except Exception as e:
        db.rollback()
        print(f"Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
