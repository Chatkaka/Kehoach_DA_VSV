from sqlalchemy.orm import Session
import models

class BudgetExceededException(Exception):
    pass

class PhaseGateException(Exception):
    pass

def execute_hard_budget_gate(db: Session, task_id: int, new_spending: float):
    """
    Layer 4: Hard Budget Gate
    Chốt chặn Ngân sách: Lũy kế thực chi + Số tiền mới không vượt quá Ngân sách tổng được duyệt.
    Nếu vượt quá: Lock ngân sách, trigger Red Alert, và raise exception để rollback.
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise ValueError(f"Task ID {task_id} không tồn tại.")

    budget = task.budget
    if not budget:
        # Nếu task không có ngân sách được khai báo, cho phép chi nhưng cảnh báo
        return

    if budget.is_locked:
        raise BudgetExceededException(
            f"Mã ngân sách {task.ma_ngan_sach} ĐÃ BỊ KHÓA do vượt chi trước đó. Không thể duyệt chi thêm."
        )

    # Tính tổng thực chi hiện tại (chỉ tính các khoản đã được Approved)
    current_approved_spending = db.query(models.ActualSpending).filter(
        models.ActualSpending.task_id == task_id,
        models.ActualSpending.trang_thai_duyet == "Approved"
    ).all()
    
    total_spent = sum(spend.so_tien_chi for spend in current_approved_spending)
    new_total = total_spent + new_spending

    if new_total > budget.ngan_sach_tong:
        # Kích hoạt trạng thái khóa ngân sách và báo động đỏ
        budget.is_locked = True
        db.add(budget)
        db.commit() # Lưu trạng thái khóa trước khi rollback giao dịch chính
        
        log_message = (
            f" [RED ALERT] Task {task.ma_ngan_sach} vượt chi! "
            f"Tổng ngân sách: {budget.ngan_sach_tong:,.2f}, "
            f"Lũy kế đề xuất: {new_total:,.2f} (Vượt: {(new_total - budget.ngan_sach_tong):,.2f}). "
            f"Mã ngân sách này đã bị khóa duyệt chi."
        )
        print(log_message)
        raise BudgetExceededException(log_message)

def execute_phase_gate_loop(db: Session, task_id: int, new_status: str):
    """
    Layer 4: Phase Gate Loop
    Chốt chặn Chuyển Giai Đoạn: Công việc thuộc Phase N (N > 1) chỉ được chuyển sang "In-Progress"
    khi tất cả các công việc ở Phase N-1 đã hoàn thành 100% tiến độ và có điều kiện ghi nhận kết quả.
    """
    if new_status != "In-Progress":
        return

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise ValueError(f"Task ID {task_id} không tồn tại.")

    current_phase_id = task.phase_id
    if current_phase_id <= 1:
        # Giai đoạn 1 không có giai đoạn trước đó, cho phép bắt đầu tự do
        return

    # Tìm các công việc chưa hoàn thành ở giai đoạn trước đó (Phase N-1)
    previous_phase_id = current_phase_id - 1
    incomplete_prev_tasks = db.query(models.Task).filter(
        models.Task.phase_id == previous_phase_id,
        (models.Task.tien_do < 100) | (models.Task.dieu_kien_ghi_nhan == None) | (models.Task.dieu_kien_ghi_nhan == "")
    ).all()

    if incomplete_prev_tasks:
        incomplete_details = [
            f"Task {t.ma_ngan_sach} (Tiến độ: {t.tien_do}%, Điều kiện ghi nhận: {t.dieu_kien_ghi_nhan or 'Chưa đạt'})"
            for t in incomplete_prev_tasks[:3]
        ]
        detail_str = "; ".join(incomplete_details)
        if len(incomplete_prev_tasks) > 3:
            detail_str += f" và {len(incomplete_prev_tasks) - 3} công việc khác"

        raise PhaseGateException(
            f" [PHASE GATE LOOP BLOCK] Không thể chuyển task {task.ma_ngan_sach} sang 'In-Progress'. "
            f"Các công việc ở Giai đoạn trước (Phase {previous_phase_id}) chưa hoàn tất 100% hoặc thiếu điều kiện ghi nhận: {detail_str}."
        )
