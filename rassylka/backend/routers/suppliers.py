from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Supplier
from backend.schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    SupplierListResponse, AISearchRequest, AISearchResponse,
)
from backend.services.supplier_ai import search_suppliers, build_search_query

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=SupplierListResponse)
async def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    query = select(Supplier)
    count_query = select(func.count(Supplier.id))

    if active_only:
        query = query.where(Supplier.active == True)
        count_query = count_query.where(Supplier.active == True)

    if search:
        search_filter = Supplier.company_name.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Supplier.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    items = [SupplierResponse.model_validate(s) for s in suppliers]
    return SupplierListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=SupplierResponse)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db)):
    supplier = Supplier(
        company_name=data.company_name,
        email=data.email,
        phone=data.phone,
        contact_person=data.contact_person,
        categories=data.categories,
        regions=data.regions,
        description=data.description,
        website=data.website,
        source="manual",
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return SupplierResponse.model_validate(supplier)


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(supplier_id: int, data: SupplierUpdate, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Поставщик не найден")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)

    supplier.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(supplier)
    return SupplierResponse.model_validate(supplier)


@router.delete("/{supplier_id}")
async def delete_supplier(supplier_id: int, db: AsyncSession = Depends(get_db)):
    supplier = await db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Поставщик не найден")

    await db.delete(supplier)
    await db.commit()
    return {"message": "Поставщик удалён"}


@router.post("/ai-search", response_model=AISearchResponse)
async def ai_search_suppliers(data: AISearchRequest, db: AsyncSession = Depends(get_db)):
    """Search for suppliers using Perplexity AI."""
    query = data.query

    # If bid_id provided, build query from bid data
    if data.bid_id:
        from backend.models import Bid
        bid = await db.get(Bid, data.bid_id)
        if bid:
            query = build_search_query({
                "brand": bid.brand,
                "model": bid.model,
                "spare_part_type": bid.spare_part_type,
                "name": bid.name,
                "delivery_place": bid.delivery_place,
            })

    found = await search_suppliers(query)

    created_suppliers = []
    for s_data in found:
        # Check if supplier already exists by email
        existing = (await db.execute(
            select(Supplier).where(Supplier.email == s_data["email"])
        )).scalar_one_or_none()

        if existing:
            created_suppliers.append(SupplierResponse.model_validate(existing))
            continue

        supplier = Supplier(
            company_name=s_data["company_name"],
            email=s_data["email"],
            phone=s_data.get("phone", ""),
            contact_person=s_data.get("contact_person", ""),
            categories=s_data.get("categories", []),
            regions=s_data.get("regions", []),
            description=s_data.get("description", ""),
            website=s_data.get("website", ""),
            source="ai",
            ai_search_query=query,
        )
        db.add(supplier)
        await db.flush()
        created_suppliers.append(SupplierResponse.model_validate(supplier))

    await db.commit()

    return AISearchResponse(
        suppliers_found=len(created_suppliers),
        suppliers=created_suppliers,
        search_query=query,
    )
