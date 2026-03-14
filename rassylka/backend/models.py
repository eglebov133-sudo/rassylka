import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from backend.database import Base
import enum


class BidStatus(str, enum.Enum):
    NEW = "new"
    DISTRIBUTING = "distributing"
    FULLY_NOTIFIED = "fully_notified"
    EXPIRED = "expired"


class BatchStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    WAITING = "waiting"
    TIMEOUT = "timeout"
    ESCALATED = "escalated"


class EmailStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    OPENED = "opened"
    RESPONDED = "responded"


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    brand = Column(String(200), default="")
    model = Column(String(200), default="")
    year = Column(String(50), default="")
    spare_part_type = Column(String(300), default="")
    count = Column(Integer, default=1)
    delivery_place = Column(String(300), default="")
    description = Column(Text, default="")
    buyer_name = Column(String(300), default="")
    delivery_method = Column(String(100), default="")
    taxation = Column(String(100), default="")
    validity_days = Column(Integer, default=5)
    status = Column(String(50), default=BidStatus.NEW.value)
    source_url = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    parsed_at = Column(DateTime, default=datetime.datetime.utcnow)

    batches = relationship("DistributionBatch", back_populates="bid", cascade="all, delete-orphan")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(500), nullable=False)
    email = Column(String(300), nullable=False)
    phone = Column(String(100), default="")
    contact_person = Column(String(300), default="")
    categories = Column(JSON, default=list)
    regions = Column(JSON, default=list)
    description = Column(Text, default="")
    source = Column(String(50), default="manual")  # manual / ai
    ai_search_query = Column(Text, default="")
    website = Column(String(500), default="")
    active = Column(Boolean, default=True)
    unsubscribe_token = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    distribution_logs = relationship("DistributionLog", back_populates="supplier")


class DistributionBatch(Base):
    __tablename__ = "distribution_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bid_id = Column(Integer, ForeignKey("bids.id"), nullable=False)
    batch_number = Column(Integer, default=1)
    status = Column(String(50), default=BatchStatus.PENDING.value)
    sent_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    bid = relationship("Bid", back_populates="batches")
    logs = relationship("DistributionLog", back_populates="batch", cascade="all, delete-orphan")


class DistributionLog(Base):
    __tablename__ = "distribution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(Integer, ForeignKey("distribution_batches.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    email_status = Column(String(50), default=EmailStatus.PENDING.value)
    error_message = Column(Text, default="")
    sent_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    click_token = Column(String(100), unique=True, nullable=True, index=True)
    clicked_at = Column(DateTime, nullable=True)
    search_priority = Column(Integer, default=0)  # P1-P8 priority level

    batch = relationship("DistributionBatch", back_populates="logs")
    supplier = relationship("Supplier", back_populates="distribution_logs")


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, default=1)
    batch_size = Column(Integer, default=5)
    batch_timeout_minutes = Column(Integer, default=30)
    matching_sensitivity = Column(Float, default=0.75)
    filter_keywords = Column(JSON, default=list)
    auto_parse = Column(Boolean, default=True)
    auto_distribute = Column(Boolean, default=True)
    parse_interval_minutes = Column(Integer, default=5)
    email_delay_seconds = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class SmtpAccount(Base):
    __tablename__ = "smtp_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(300), nullable=False)
    password = Column(String(300), nullable=False)
    smtp_host = Column(String(300), default="smtp.mail.ru")
    smtp_port = Column(Integer, default=465)
    use_tls = Column(Boolean, default=True)
    active = Column(Boolean, default=True)
    send_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ── Manual Campaign (Newsletter) ──

class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SENDING = "sending"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    subject = Column(String(500), nullable=False, default="")
    html_body = Column(Text, default="")
    status = Column(String(50), default=CampaignStatus.DRAFT.value)
    delay_seconds = Column(Integer, default=30)
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")
    attachments = relationship("CampaignAttachment", back_populates="campaign", cascade="all, delete-orphan")


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    email = Column(String(300), nullable=False)
    name = Column(String(300), default="")
    status = Column(String(50), default="pending")  # pending/sent/failed/opened/clicked
    error_message = Column(Text, default="")
    sent_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    track_token = Column(String(100), unique=True, nullable=True, index=True)

    campaign = relationship("Campaign", back_populates="recipients")


class CampaignAttachment(Base):
    __tablename__ = "campaign_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    filepath = Column(String(1000), nullable=False)
    size_bytes = Column(Integer, default=0)

    campaign = relationship("Campaign", back_populates="attachments")


# ═══════════════════════════════════════════════════
#  Monitoring & Testing
# ═══════════════════════════════════════════════════

class MonitorTest(Base):
    __tablename__ = "monitor_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group = Column(String(50), nullable=False, default="public")  # public, buyer, seller
    code = Column(String(10), unique=True, nullable=False)        # T01, T02, ...
    name = Column(String(500), nullable=False)
    description = Column(Text, default="")
    enabled = Column(Boolean, default=True)
    order = Column(Integer, default=0)

    results = relationship("MonitorResult", back_populates="test", cascade="all, delete-orphan")


class MonitorRun(Base):
    __tablename__ = "monitor_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger = Column(String(20), default="manual")   # auto / manual
    status = Column(String(20), default="running")    # running, completed, failed
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    total = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)

    results = relationship("MonitorResult", back_populates="run", cascade="all, delete-orphan")


class MonitorResult(Base):
    __tablename__ = "monitor_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("monitor_runs.id"), nullable=False)
    test_id = Column(Integer, ForeignKey("monitor_tests.id"), nullable=False)
    status = Column(String(20), default="pending")    # pass, fail, skip, error
    duration_ms = Column(Integer, default=0)
    response_code = Column(Integer, nullable=True)
    error_message = Column(Text, default="")
    details_json = Column(Text, default="{}")
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)

    run = relationship("MonitorRun", back_populates="results")
    test = relationship("MonitorTest", back_populates="results")
