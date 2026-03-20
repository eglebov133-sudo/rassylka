from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ── Bids ──

class BidResponse(BaseModel):
    id: int
    source_id: int
    name: str
    brand: str
    model: str
    year: str
    spare_part_type: str
    count: int
    delivery_place: str
    description: str
    buyer_name: str
    status: str
    validity_days: int
    source_url: str
    created_at: Optional[datetime] = None
    parsed_at: Optional[datetime] = None
    batch_count: int = 0

    class Config:
        from_attributes = True


class BidListResponse(BaseModel):
    items: List[BidResponse]
    total: int
    page: int
    page_size: int


# ── Suppliers ──

class SupplierCreate(BaseModel):
    company_name: str
    email: str
    phone: str = ""
    contact_person: str = ""
    categories: List[str] = []
    regions: List[str] = []
    description: str = ""
    website: str = ""


class SupplierUpdate(BaseModel):
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    categories: Optional[List[str]] = None
    regions: Optional[List[str]] = None
    description: Optional[str] = None
    website: Optional[str] = None
    active: Optional[bool] = None


class SupplierResponse(BaseModel):
    id: int
    company_name: str
    email: str
    phone: str
    contact_person: str
    categories: List[str]
    regions: List[str]
    description: str
    source: str
    website: str
    active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SupplierListResponse(BaseModel):
    items: List[SupplierResponse]
    total: int
    page: int
    page_size: int


# ── Routing Rules ──

class RoutingRuleResponse(BaseModel):
    batch_size: int
    batch_timeout_minutes: int
    matching_sensitivity: float
    filter_keywords: List[str]
    auto_parse: bool
    auto_distribute: bool
    parse_interval_minutes: int = 5
    email_delay_seconds: int = 30
    # Новая схема батчинга
    batch1_size: int = 5
    batch1_delay_seconds: int = 120
    batch2_size: int = 10
    batch2_delay_seconds: int = 120
    escalation_hours: int = 24
    max_no_response: int = 10
    auto_supplier_search: bool = True

    class Config:
        from_attributes = True


class RoutingRuleUpdate(BaseModel):
    batch_size: Optional[int] = None
    batch_timeout_minutes: Optional[int] = None
    matching_sensitivity: Optional[float] = None
    filter_keywords: Optional[List[str]] = None
    auto_parse: Optional[bool] = None
    auto_distribute: Optional[bool] = None
    parse_interval_minutes: Optional[int] = None
    email_delay_seconds: Optional[int] = None
    # Новая схема батчинга
    batch1_size: Optional[int] = None
    batch1_delay_seconds: Optional[int] = None
    batch2_size: Optional[int] = None
    batch2_delay_seconds: Optional[int] = None
    escalation_hours: Optional[int] = None
    max_no_response: Optional[int] = None
    auto_supplier_search: Optional[bool] = None


# ── Dashboard ──

class DashboardStats(BaseModel):
    total_bids: int
    active_mailings: int
    suppliers_notified: int
    total_suppliers: int
    response_rate: float


class RecentBidItem(BaseModel):
    id: int
    source_id: int
    name: str
    spare_part_type: str
    status: str
    parsed_at: Optional[datetime] = None
    batch_status: Optional[str] = None
    batch_number: int = 0


# ── Logs ──

class LogEntry(BaseModel):
    id: int
    bid_id: int = 0
    bid_name: str
    bid_source_id: int
    supplier_name: str
    supplier_email: str
    supplier_website: str = ""
    email_status: str
    batch_number: int
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    error_message: str = ""

    class Config:
        from_attributes = True


class LogListResponse(BaseModel):
    items: List[LogEntry]
    total: int
    page: int
    page_size: int


# ── AI Search ──

class AISearchRequest(BaseModel):
    query: str
    bid_id: Optional[int] = None


class AISearchResponse(BaseModel):
    suppliers_found: int
    suppliers: List[SupplierResponse]
    search_query: str


# ── System Status ──

class SystemStatus(BaseModel):
    parser_running: bool
    distributor_running: bool
    last_parse_at: Optional[datetime] = None
    last_distribution_at: Optional[datetime] = None
    smtp_configured: bool
    openrouter_configured: bool
