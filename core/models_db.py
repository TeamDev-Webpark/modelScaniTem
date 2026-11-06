"""
SQLAlchemy ORM models for tool scanner system.
Tables:
- users
- tool_classes
- training_images
- image_labels
- trained_models
- tray_templates
- tray_slots
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")  # admin, editor, viewer
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    training_images = relationship("TrainingImage", back_populates="uploader")
    trained_models = relationship("TrainedModel", back_populates="creator")
    tray_templates = relationship("TrayTemplate", back_populates="creator")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class ToolClass(Base):
    __tablename__ = "tool_classes"

    id = Column(Integer, primary_key=True, index=True)
    class_key = Column(String(50), unique=True, nullable=False, index=True)  # e.g., 'combination_pliers'
    name_en = Column(String(100), nullable=False)
    name_th = Column(String(200), nullable=True)
    category = Column(String(50), nullable=True)  # 'Hand Tools', 'Engine Tools', etc.
    description = Column(Text, nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    image_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    labels = relationship("ImageLabel", back_populates="tool_class")
    tray_slots = relationship("TraySlot", back_populates="tool_class")

    def __repr__(self):
        return f"<ToolClass {self.class_key} ({self.name_en})>"


class TrainingImage(Base):
    __tablename__ = "training_images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    split = Column(String(10), default="train")  # train, val, test
    file_hash = Column(String(64), index=True, nullable=True)  # SHA-256 hash to prevent duplicate uploads
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    source = Column(String(50), default="upload")  # upload, camera, roboflow, augmented
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    uploader = relationship("User", back_populates="training_images")
    labels = relationship("ImageLabel", back_populates="image", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TrainingImage {self.filename} ({self.split})>"


class ImageLabel(Base):
    __tablename__ = "image_labels"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("training_images.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(Integer, ForeignKey("tool_classes.id"), nullable=False, index=True)
    
    # YOLO normalized coordinates [0.0 - 1.0]
    center_x = Column(Float, nullable=False)
    center_y = Column(Float, nullable=False)
    bbox_width = Column(Float, nullable=False)
    bbox_height = Column(Float, nullable=False)
    
    confidence = Column(Float, nullable=True)  # None for manual labels
    label_source = Column(String(30), default="manual")  # manual, roboflow, model_predict
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    image = relationship("TrainingImage", back_populates="labels")
    tool_class = relationship("ToolClass", back_populates="labels")

    def to_yolo_str(self, class_idx: int) -> str:
        """Exports to YOLO label format line: class_idx x_center y_center width height"""
        return f"{class_idx} {self.center_x:.6f} {self.center_y:.6f} {self.bbox_width:.6f} {self.bbox_height:.6f}"


class TrainedModel(Base):
    __tablename__ = "trained_models"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(30), nullable=False)  # 'v1.0', 'v2.1'
    model_path = Column(String(500), nullable=False)
    model_type = Column(String(30), default="yolov8m")
    map50 = Column(Float, nullable=True)
    map50_95 = Column(Float, nullable=True)
    num_classes = Column(Integer, nullable=True)
    epochs = Column(Integer, nullable=True)
    image_count_train = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    trained_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    trained_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="trained_models")


class TrayTemplate(Base):
    __tablename__ = "tray_templates"

    id = Column(Integer, primary_key=True, index=True)
    tray_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., 'TRAY_03'
    tray_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    reference_image_path = Column(String(500), nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    slot_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="tray_templates")
    slots = relationship("TraySlot", back_populates="template", cascade="all, delete-orphan", order_by="TraySlot.slot_number", lazy="selectin")


class TraySlot(Base):
    __tablename__ = "tray_slots"

    id = Column(Integer, primary_key=True, index=True)
    tray_template_id = Column(Integer, ForeignKey("tray_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_number = Column(Integer, nullable=False)
    class_id = Column(Integer, ForeignKey("tool_classes.id"), nullable=True)
    item_name = Column(String(200), nullable=True)
    item_code = Column(String(50), nullable=True)
    
    # Normalized bbox for slot area [0.0 - 1.0]
    bbox_x1_norm = Column(Float, nullable=False)
    bbox_y1_norm = Column(Float, nullable=False)
    bbox_x2_norm = Column(Float, nullable=False)
    bbox_y2_norm = Column(Float, nullable=False)
    
    is_required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint per tray slot number
    __table_args__ = (
        UniqueConstraint("tray_template_id", "slot_number", name="uq_tray_slot_number"),
    )

    # Relationships
    template = relationship("TrayTemplate", back_populates="slots")
    tool_class = relationship("ToolClass", back_populates="tray_slots")
