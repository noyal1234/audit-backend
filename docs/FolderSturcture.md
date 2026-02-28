audit_backend/
│
├── alembic.ini
├── postgres_migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── docs/
│   ├── ProductRequirementDocument.txt
│   ├── AppFlowDocument.txt
│   └── FinalAPIList.txt
│
├── src/
│   │
│   ├── __init__.py
│   ├── app.py
│   ├── main.py
│
│   ├── api/                        # 🚦 HTTP Layer
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── routers/
│   │       ├── auth_router.py
│   │       ├── company_router.py
│   │       ├── dealer_router.py
│   │       ├── staff_router.py
│   │       ├── audit_router.py
│   │       ├── template_router.py
│   │       ├── media_router.py
│   │       ├── ai_router.py
│   │       ├── dashboard_router.py
│   │       ├── incident_router.py
│   │       ├── notification_router.py
│   │       ├── settings_router.py
│   │       └── app_config_router.py
│
│   ├── business_services/          # 🧠 Domain Logic Layer
│   │   ├── base.py
│   │   ├── auth_service.py
│   │   ├── company_service.py
│   │   ├── dealer_service.py
│   │   ├── staff_service.py
│   │   ├── user_service.py
│   │   ├── audit_service.py
│   │   ├── template_service.py
│   │   ├── media_service.py
│   │   ├── ai_service.py
│   │   ├── dashboard_service.py
│   │   ├── incident_service.py
│   │   ├── notification_service.py
│   │   ├── settings_service.py
│   │   └── app_config_service.py
│
│   ├── database/                   # 🗄 Persistence Layer
│   │
│   │   ├── base.py                 # Declarative Base
│   │   ├── session.py              # Engine + session factory
│   │
│   │   ├── models/                 # ORM ONLY (SQLAlchemy)
│   │   │   ├── __init__.py
│   │   │   ├── company.py
│   │   │   ├── dealer.py
│   │   │   ├── user.py
│   │   │   ├── auth_session.py
│   │   │   ├── audit.py
│   │   │   ├── audit_history.py
│   │   │   ├── audit_template.py
│   │   │   ├── audit_template_section.py
│   │   │   ├── audit_template_item.py
│   │   │   ├── audit_item_answer.py
│   │   │   ├── audit_section_status.py
│   │   │   ├── audit_final_result.py
│   │   │   ├── media_evidence.py
│   │   │   ├── ai_analysis_job.py
│   │   │   ├── ai_override.py
│   │   │   ├── incident.py
│   │   │   ├── notification.py
│   │   │   ├── user_settings.py
│   │   │   └── app_config.py
│   │
│   │   └── repositories/           # 🧱 Repo Layer (owns schemas)
│   │       │
│   │       ├── base_repository.py
│   │       │
│   │       ├── schemas/            # 🔐 REPO-OWNED Pydantic
│   │       │   ├── __init__.py
│   │       │   ├── company_schema.py
│   │       │   ├── dealer_schema.py
│   │       │   ├── staff_schema.py
│   │       │   ├── user_schema.py
│   │       │   ├── audit_schema.py
│   │       │   ├── audit_list_schema.py
│   │       │   ├── template_schema.py
│   │       │   ├── media_schema.py
│   │       │   ├── ai_schema.py
│   │       │   ├── dashboard_schema.py
│   │       │   ├── incident_schema.py
│   │       │   ├── notification_schema.py
│   │       │   ├── settings_schema.py
│   │       │   └── app_config_schema.py
│   │       │
│   │       ├── company_repository.py
│   │       ├── dealer_repository.py
│   │       ├── staff_repository.py
│   │       ├── user_repository.py
│   │       ├── auth_repository.py
│   │       ├── audit_repository.py
│   │       ├── template_repository.py
│   │       ├── media_repository.py
│   │       ├── ai_repository.py
│   │       ├── dashboard_repository.py
│   │       ├── incident_repository.py
│   │       ├── notification_repository.py
│   │       ├── settings_repository.py
│   │       └── app_config_repository.py
│
│   ├── infra_services/             # 🔌 External Systems
│   │   ├── base.py
│   │   ├── postgres_service.py
│   │   ├── storage_service.py
│   │   ├── email_service.py
│   │   └── ai_provider_service.py
│
│   ├── clients/                    # External API wrappers
│   │   ├── ai_client.py
│   │   ├── storage_client.py
│   │   └── email_client.py
│
│   ├── di/                         # 🧩 Dependency Injection
│   │   ├── container.py
│   │   ├── config_module.py
│   │   ├── infra_module.py
│   │   ├── repository_module.py
│   │   └── business_module.py
│
│   ├── configs/
│   │   ├── settings.py
│   │   └── logging_config.py
│
│   ├── logging/
│   │   └── logger.py
│
│   ├── exceptions/
│   │   ├── domain_exceptions.py
│   │   └── api_exceptions.py
│
│   └── utils/
│       ├── datetime_utils.py
│       ├── pagination.py
│       └── validators.py
│
└── tests/