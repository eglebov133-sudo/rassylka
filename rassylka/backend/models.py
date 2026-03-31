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
    no_response_count = Column(Integer, default=0)  # сколько писем без ответа
    archived_at = Column(DateTime, nullable=True)  # дата авто-архивирования
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
    smtp_account_id = Column(Integer, nullable=True)  # с какого SMTP отправлено

    batch = relationship("DistributionBatch", back_populates="logs")
    supplier = relationship("Supplier", back_populates="distribution_logs")


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, default=1)
    batch_size = Column(Integer, default=5)  # legacy, kept for compat
    batch_timeout_minutes = Column(Integer, default=30)  # legacy
    matching_sensitivity = Column(Float, default=0.75)
    filter_keywords = Column(JSON, default=list)
    auto_parse = Column(Boolean, default=True)
    auto_distribute = Column(Boolean, default=True)
    parse_interval_minutes = Column(Integer, default=5)
    email_delay_seconds = Column(Integer, default=30)  # legacy
    # ── Новая схема батчинга (управляемая из панели) ──
    batch1_size = Column(Integer, default=5)       # кол-во писем в 1-м батче
    batch1_delay_seconds = Column(Integer, default=120)  # пауза между письмами в 1-м батче (10мин/5=120с)
    batch2_size = Column(Integer, default=10)      # кол-во писем во 2-м батче
    batch2_delay_seconds = Column(Integer, default=120)  # пауза между письмами во 2-м батче (20мин/10=120с)
    escalation_hours = Column(Integer, default=24)  # пауза между 1-м и 2-м батчем (часы)
    max_no_response = Column(Integer, default=10)  # после скольки писем без ответа → архив
    auto_supplier_search = Column(Boolean, default=True)  # автоматический поиск поставщиков
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
    subgroup = Column(String(200), nullable=True, default="")     # logical section from 123.txt
    code = Column(String(10), unique=True, nullable=False)        # T01, T02, ..., B01, B02, ...
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


# ═══════════════════════════════════════════════════
#  Yandex Direct Promotion
# ═══════════════════════════════════════════════════

class YandexDirectConfig(Base):
    __tablename__ = "yd_config"

    id = Column(Integer, primary_key=True, default=1)
    oauth_token = Column(String(500), default="")
    client_id = Column(String(200), default="")
    client_login = Column(String(200), default="")
    connected = Column(Boolean, default=False)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class YandexDirectCampaign(Base):
    __tablename__ = "yd_campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    yd_campaign_id = Column(Integer, unique=True, nullable=True, index=True)  # ID в Яндекс.Директ
    name = Column(String(500), nullable=False)
    status = Column(String(50), default="draft")  # draft/pending/active/paused/stopped/archived
    yd_status = Column(String(100), default="")    # статус из Директа (ACCEPTED, MODERATION, etc.)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    cost = Column(Float, default=0.0)              # расход в рублях
    ctr = Column(Float, default=0.0)               # CTR в %
    daily_budget = Column(Float, default=300.0)     # дневной бюджет в рублях
    keywords = Column(JSON, default=list)           # ключевые слова
    regions = Column(JSON, default=list)            # регионы таргетинга
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    brand_id = Column(Integer, ForeignKey("car_brands.id"), nullable=True)  # привязка к бренду
    geo_segment = Column(String(50), default="")  # "msk_spb" / "regions"


class CarBrand(Base):
    """Справочник автомобильных марок."""
    __tablename__ = "car_brands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)  # Toyota
    name_ru = Column(String(200), default="")                 # Тойота
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    models = relationship("CarModel", back_populates="brand", cascade="all, delete-orphan")


class CarModel(Base):
    """Справочник моделей автомобилей."""
    __tablename__ = "car_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_id = Column(Integer, ForeignKey("car_brands.id"), nullable=False)
    name = Column(String(200), nullable=False)       # Camry
    name_ru = Column(String(200), default="")         # Камри
    popular = Column(Boolean, default=False)           # топ-модель (для приоритета)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    brand = relationship("CarBrand", back_populates="models")


class PartCategory(Base):
    """Справочник категорий запчастей."""
    __tablename__ = "part_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)   # тормозные колодки
    name_ru = Column(String(200), default="")                  # Тормозные колодки
    cluster = Column(String(100), default="")                  # тормоза / подвеска / фильтры
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ═══════════════════════════════════════════════════
#  Telegram Userbot Mailing
# ═══════════════════════════════════════════════════

class TgCampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SENDING = "sending"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TgCampaign(Base):
    __tablename__ = "tg_campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    message_text = Column(Text, default="")
    source_channel = Column(String(300), default="")       # @channel or numeric ID
    status = Column(String(50), default=TgCampaignStatus.DRAFT.value)
    delay_seconds = Column(Integer, default=35)
    image_path = Column(String(500), default="")        # path to attached image
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    recipients = relationship("TgCampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")


class TgCampaignRecipient(Base):
    __tablename__ = "tg_campaign_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("tg_campaigns.id"), nullable=False)
    tg_user_id = Column(Integer, nullable=False)            # Telegram user ID
    access_hash = Column(String(100), default="")            # For InputPeerUser resolution
    username = Column(String(300), default="")
    first_name = Column(String(300), default="")
    status = Column(String(50), default="pending")          # pending/sent/failed/blocked
    error_message = Column(Text, default="")
    sent_at = Column(DateTime, nullable=True)
    sent_by_account = Column(String(100), default="")       # sender account ID

    campaign = relationship("TgCampaign", back_populates="recipients")


# ═══════════════════════════════════════════════════
#  Auto Parts Landing Orders
# ═══════════════════════════════════════════════════

class PartsOrder(Base):
    """Order from the AI-generated auto parts landing page."""
    __tablename__ = "parts_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_name = Column(String(300), nullable=False)
    customer_phone = Column(String(100), nullable=False)
    customer_email = Column(String(300), default="")
    customer_city = Column(String(200), default="")
    comment = Column(Text, default="")
    items_json = Column(Text, default="[]")       # JSON array of ordered items
    total_price = Column(Float, default=0.0)
    query = Column(Text, default="")               # original search query
    utm_term = Column(String(500), default="")
    utm_source = Column(String(200), default="")
    utm_campaign = Column(String(500), default="")
    status = Column(String(50), default="new")     # new / processing / fulfilled / cancelled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
