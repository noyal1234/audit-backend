"""FastAPI application. Register routers and exception handlers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from src.configs.settings import get_settings

from src.api.routers import admin_router, audit_router, auth_router, company_router, country_router, dashboard_router, dealer_router, health_router, media_router, search_router, shift_router, staff_router, template_router, users_router
from src.di.container import configure_container, get_container
from fastapi.exceptions import RequestValidationError

from src.exceptions.api_exceptions import (
    domain_exception_handler,
    integrity_error_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from src.exceptions.domain_exceptions import DomainError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, close on shutdown."""
    configure_container()
    container = get_container()
    from src.business_services.auth_service import get_auth_service
    from src.business_services.audit_service import get_audit_service
    from src.business_services.company_service import get_company_service
    from src.business_services.country_service import get_country_service
    from src.business_services.dashboard_service import get_dashboard_service
    from src.business_services.dealer_service import get_dealer_service
    from src.business_services.media_service import get_media_service
    from src.business_services.shift_service import get_shift_service
    from src.business_services.staff_service import get_staff_service
    from src.business_services.template_service import get_template_service
    from src.business_services.user_service import get_user_service
    from src.business_services.report_service import get_report_service
    for getter in [
        get_auth_service,
        get_user_service,
        get_company_service,
        get_country_service,
        get_dealer_service,
        get_staff_service,
        get_template_service,
        get_shift_service,
        get_audit_service,
        get_dashboard_service,
        get_media_service,
        get_report_service,
    ]:
        container.register_business_service(getter())
    container.initialize_all_services()
    yield
    container.close_all_services()


app = FastAPI(
    title="Dealer Hygiene Compliance Backend",
    description="Multi-tenant RBAC, audit checklist, shift-based audits, analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=("*" not in origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(DomainError, domain_exception_handler)
app.add_exception_handler(IntegrityError, integrity_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(country_router.router)
app.include_router(company_router.router)
app.include_router(dealer_router.router)
app.include_router(staff_router.router)
app.include_router(template_router.router)
app.include_router(shift_router.router)
app.include_router(audit_router.router)
app.include_router(dashboard_router.router)
app.include_router(search_router.router)
app.include_router(users_router.router)
app.include_router(media_router.router)
app.include_router(health_router.router)
