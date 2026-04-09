"""
DC 数据连接器 ORM 模型
对照 docs/data-model/schema.sql，使用 SQLAlchemy 2.x 声明式映射。

设计要点：
- 业务表均使用软删除（is_deleted 字段），不做物理删除
- 敏感字段使用 LargeBinary 存储加密数据
- 所有表包含 created_at / updated_at 时间戳
- TaskRun / TaskRunLog / AuditLog 为日志表，不使用软删除
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class Platform(Base):
    """平台定义表，如淘宝天猫、京东、拼多多、抖音"""
    __tablename__ = "platform"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("idx_platform_parent_id", "parent_id"),)

    apps: Mapped[list["ConnectorApp"]] = relationship(back_populates="platform")
    accounts: Mapped[list["ShopAccount"]] = relationship(back_populates="platform")


class ConnectorApp(Base):
    """
    连接应用定义表，每个应用绑定一个平台。
    adapter_key 标识对应的 DrissionPage 浏览器自动化适配器，
    与 infrastructure/connectors/<platform>/ 目录下的适配器模块一一对应。
    """
    __tablename__ = "connector_app"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("platform.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    adapter_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="DrissionPage 适配器标识，如 taobao.order_sync"
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="connector_app_status"), nullable=False, default="active"
    )
    param_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_connector_app_platform_id", "platform_id"),
        Index("idx_connector_app_status", "status"),
    )

    platform: Mapped["Platform"] = relationship(back_populates="apps")
    task_instances: Mapped[list["TaskInstance"]] = relationship(back_populates="app")


class AdapterRelease(Base):
    """
    适配器发布表。
    用于管理 DrissionPage 适配器从开发到发版的状态流转，
    并作为“应用上架”“任务执行”的统一发布依据。
    """
    __tablename__ = "adapter_release"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    adapter_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="适配器标识")
    version: Mapped[str] = mapped_column(String(64), nullable=False, comment="发布版本")
    status: Mapped[str] = mapped_column(
        Enum("draft", "testing", "released", "deprecated", name="adapter_release_status"),
        nullable=False,
        default="draft",
        comment="发布状态",
    )
    qa_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="QA 是否通过")
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="发布包校验值")
    release_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="发布说明")
    released_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="发布人")
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发布时间")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("adapter_key", "version", name="uk_adapter_release_key_version"),
        Index("idx_adapter_release_status", "status"),
        Index("idx_adapter_release_adapter_key", "adapter_key"),
    )


class ShopAccount(Base):
    """
    店铺账号表，敏感字段加密存储。
    captcha_method: 验证码转发方式（none 表示不需要验证码）
    captcha_config: 按转发方式存储不同参数的 JSON 配置
    captcha_enabled: 验证码转发开关，方便临时禁用而不丢配置
    """
    __tablename__ = "shop_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("platform.id"), nullable=False)
    shop_name: Mapped[str] = mapped_column(String(128), nullable=False)
    username_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    password_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    extra_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", "disabled", name="shop_account_status"),
        nullable=False,
        default="active",
    )
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    captcha_method: Mapped[str] = mapped_column(
        Enum("none", "sms_forward", "email_forward", "email_auth_code", "manual",
             name="captcha_method"),
        nullable=False,
        default="none",
        comment="验证码转发方式",
    )
    captcha_config: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="验证码转发配置参数"
    )
    captcha_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="验证码转发开关"
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_shop_account_platform_id", "platform_id"),
        Index("idx_shop_account_status", "status"),
    )

    platform: Mapped["Platform"] = relationship(back_populates="accounts")
    task_instances: Mapped[list["TaskInstance"]] = relationship(back_populates="account")


class StorageConfig(Base):
    """
    存储配置表
    支持 MySQL / 飞书多维表 / 钉钉表格 / 邮箱存储
    type 使用 String 存储，方便后续扩展新类型
    """
    __tablename__ = "storage_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, comment="存储类型: mysql/feishu_bitable/dingtalk_sheet/email")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="storage_config_status"), nullable=False, default="active"
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_storage_config_type", "type"),
        Index("idx_storage_config_status", "status"),
    )

    task_instances: Mapped[list["TaskInstance"]] = relationship(back_populates="storage_config")


class NotificationConfig(Base):
    """通知配置表，支持飞书 / 钉钉 / 企微 Webhook"""
    __tablename__ = "notification_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(
        Enum("feishu", "dingtalk", "wechat_work", name="notification_channel"), nullable=False
    )
    webhook_url_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    notify_on_fail: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)
    notify_on_retry_fail: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)
    notify_on_account_invalid: Mapped[bool] = mapped_column(Integer, nullable=False, default=1)
    dedupe_window_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="notification_config_status"),
        nullable=False,
        default="active",
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_notification_config_channel", "channel"),
        Index("idx_notification_config_status", "status"),
    )

    task_instances: Mapped[list["TaskInstance"]] = relationship(back_populates="notification_config")


class TaskInstance(Base):
    """任务实例表，绑定应用 + 店铺 + 存储 + 通知"""
    __tablename__ = "task_instance"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("connector_app.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("shop_account.id"), nullable=False
    )
    storage_config_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("storage_config.id"), nullable=False
    )
    notification_config_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("notification_config.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cron_expr: Mapped[str] = mapped_column(String(64), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Shanghai")
    status: Mapped[str] = mapped_column(
        Enum("enabled", "paused", name="task_instance_status"), nullable=False, default="enabled"
    )
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="软删除标记")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_task_instance_app_id", "app_id"),
        Index("idx_task_instance_account_id", "account_id"),
        Index("idx_task_instance_status", "status"),
        Index("idx_task_instance_next_run_at", "next_run_at"),
    )

    app: Mapped["ConnectorApp"] = relationship(back_populates="task_instances")
    account: Mapped["ShopAccount"] = relationship(back_populates="task_instances")
    storage_config: Mapped["StorageConfig"] = relationship(back_populates="task_instances")
    notification_config: Mapped["NotificationConfig"] = relationship(
        back_populates="task_instances"
    )
    runs: Mapped[list["TaskRun"]] = relationship(back_populates="task")


class TaskRun(Base):
    """任务运行记录表（日志表，不使用软删除）"""
    __tablename__ = "task_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_instance.id"), nullable=False)
    trigger_type: Mapped[str] = mapped_column(
        Enum("scheduler", "manual", "retry", name="trigger_type"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "success", "failed", "cancelled", name="task_run_status"),
        nullable=False,
        default="pending",
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uk_task_run_idempotency_key"),
        Index("idx_task_run_task_id", "task_id"),
        Index("idx_task_run_status", "status"),
        Index("idx_task_run_started_at", "started_at"),
    )

    task: Mapped["TaskInstance"] = relationship(back_populates="runs")
    logs: Mapped[list["TaskRunLog"]] = relationship(back_populates="run")


class TaskRunLog(Base):
    """运行步骤日志表（日志表，不使用软删除）"""
    __tablename__ = "task_run_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_run.id"), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(
        Enum("INFO", "WARN", "ERROR", name="log_level"), nullable=False
    )
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    ext: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_task_run_log_run_id", "run_id"),
        Index("idx_task_run_log_level", "level"),
    )

    run: Mapped["TaskRun"] = relationship(back_populates="logs")


class AuditLog(Base):
    """操作审计日志表（日志表，不使用软删除）"""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_audit_log_actor_id", "actor_id"),
        Index("idx_audit_log_target", "target_type", "target_id"),
        Index("idx_audit_log_created_at", "created_at"),
    )

