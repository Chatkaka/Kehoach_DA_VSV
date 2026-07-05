from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    ten_du_an = Column(String, default="Ven Sông Vinh", nullable=False)
    tong_ngan_sach = Column(Float, default=0.0)

    # Relationships
    tasks = relationship("Task", back_populates="project")

class Phase(Base):
    __tablename__ = "phases"

    id = Column(Integer, primary_key=True, index=True) # 1 to 4
    ten_giai_doan = Column(String, nullable=False)
    mo_ta = Column(String, nullable=True)

    # Relationships
    tasks = relationship("Task", back_populates="phase")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), default=1)
    ma_ngan_sach = Column(String, unique=True, index=True, nullable=False)  # WBS code
    stt = Column(String, nullable=True)
    phase_id = Column(Integer, ForeignKey("phases.id"), nullable=False)
    ten_cong_viec = Column(String, nullable=False)
    phong_ban_thuc_hien = Column(String, nullable=True)
    co_quan_giai_quyet = Column(String, nullable=True)
    kpi_trong_yeu = Column(String, nullable=True)
    dieu_kien_ghi_nhan = Column(String, nullable=True)
    tien_do = Column(Float, default=0.0)  # 0 to 100
    trang_thai = Column(String, default="Todo")  # Todo/In-Progress/Done/Delayed

    # Relationships
    project = relationship("Project", back_populates="tasks")
    phase = relationship("Phase", back_populates="tasks")
    budget = relationship("Budget", uselist=False, back_populates="task", cascade="all, delete-orphan")
    actual_spendings = relationship("ActualSpending", back_populates="task", cascade="all, delete-orphan")

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), unique=True, nullable=False)
    ngan_sach_tong = Column(Float, default=0.0)
    kh_2026 = Column(Float, default=0.0)
    quy_1_2026 = Column(Float, default=0.0)
    quy_2_2026 = Column(Float, default=0.0)
    thang_01_2025 = Column(Float, default=0.0)
    thang_02_2025 = Column(Float, default=0.0)
    thang_03_2025 = Column(Float, default=0.0)
    thang_04_2025 = Column(Float, default=0.0)
    thang_05_2026 = Column(Float, default=0.0)
    thang_06_2026 = Column(Float, default=0.0)
    is_locked = Column(Boolean, default=False)

    # Relationships
    task = relationship("Task", back_populates="budget")

class ActualSpending(Base):
    __tablename__ = "actual_spending"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    so_tien_chi = Column(Float, nullable=False)
    ngay_chi = Column(Date, default=datetime.date.today, nullable=False)
    nguoi_cap_nhat = Column(String, nullable=False)
    chung_tu_kem_theo = Column(String, nullable=True)  # URL to document/invoice
    trang_thai_duyet = Column(String, default="Pending")  # Pending/Approved/Rejected

    # Relationships
    task = relationship("Task", back_populates="actual_spendings")
