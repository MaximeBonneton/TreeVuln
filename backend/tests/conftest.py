"""
Pytest test configuration.
"""

import os

# DATABASE_URL doit être défini AVANT tout import de `app` : app.database crée
# l'engine à l'import (settings.database_url est validé non-vide). En tests
# d'intégration, l'engine réel est fourni par la fixture `db_engine`
# (testcontainers) et get_db est surchargé ; ce placeholder ne sert qu'à la
# validation à l'import et ne se connecte jamais.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://placeholder:placeholder@localhost:5432/placeholder",
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.schemas.tree import (  # noqa: E402
    ConditionOperator,
    EdgeSchema,
    NodeCondition,
    NodeSchema,
    NodeType,
    SimpleConditionCriteria,
    TreeStructure,
)

# ----------------------------------------------------------------------
# Fixture base de données éphémère (T-3) : PostgreSQL réel via testcontainers.
# Débloque les tests d'intégration API (T-1/T-2). Skip gracieux si Docker ou
# testcontainers ne sont pas disponibles, pour que la suite unitaire tourne
# partout.
# ----------------------------------------------------------------------

try:
    from testcontainers.postgres import PostgresContainer

    _HAS_TESTCONTAINERS = True
except ImportError:  # pragma: no cover - dépend de l'environnement
    _HAS_TESTCONTAINERS = False


def _to_async_url(sync_url: str) -> str:
    """Convertit l'URL testcontainers (psycopg2) en URL asyncpg."""
    return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )


@pytest.fixture(scope="session")
def pg_url() -> str:
    """Démarre un PostgreSQL éphémère et y crée le schéma (une fois par session)."""
    if not _HAS_TESTCONTAINERS:
        pytest.skip("testcontainers indisponible")

    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    import app.models  # noqa: F401  (peuple Base.metadata)
    from app.database import Base

    try:
        container = PostgresContainer("postgres:15-alpine")
        container.start()
    except Exception as exc:  # pragma: no cover - Docker absent
        pytest.skip(f"Impossible de démarrer PostgreSQL (Docker requis) : {exc}")

    url = _to_async_url(container.get_connection_url())

    async def _create_schema() -> None:
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_create_schema())

    try:
        yield url
    finally:
        container.stop()


async def _truncate_all(engine) -> None:
    """Vide toutes les tables (isolation entre tests)."""
    import app.models  # noqa: F401
    from app.database import Base

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    if not tables:
        return
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def db_engine(pg_url: str):
    """Engine async lié au conteneur, recréé par test (isolation de boucle)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(pg_url)
    await _truncate_all(engine)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Session ORM directe sur la base de test (tests de services)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    """
    Client HTTP d'intégration : app FastAPI réelle avec get_db surchargé vers
    la base de test. Le lifespan (migrations) n'est PAS déclenché par
    ASGITransport — le schéma est déjà créé par la fixture pg_url.
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.database import get_db
    from app.main import app

    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db_override():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as http_client:
            yield http_client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(client):
    """Client authentifié en tant qu'admin (setup initial + session cookie)."""
    resp = await client.post(
        "/api/v1/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200, resp.text
    return client


@pytest.fixture
def simple_tree_structure() -> TreeStructure:
    """
    Simple test tree:
    - INPUT node checks cvss_score
    - If >= 9.0 -> Act
    - If >= 7.0 -> Attend
    - Otherwise -> Track
    """
    nodes = [
        NodeSchema(
            id="input-cvss",
            type=NodeType.INPUT,
            label="CVSS Score",
            config={"field": "cvss_score"},
            conditions=[
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9.0, label="Critical"),
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=7.0, label="High"),
                NodeCondition(operator=ConditionOperator.LESS_THAN, value=7.0, label="Low"),
            ],
        ),
        NodeSchema(
            id="output-act",
            type=NodeType.OUTPUT,
            label="Act",
            config={"decision": "Act", "color": "#ff0000"},
        ),
        NodeSchema(
            id="output-attend",
            type=NodeType.OUTPUT,
            label="Attend",
            config={"decision": "Attend", "color": "#ff9900"},
        ),
        NodeSchema(
            id="output-track",
            type=NodeType.OUTPUT,
            label="Track",
            config={"decision": "Track", "color": "#00ff00"},
        ),
    ]

    edges = [
        EdgeSchema(id="e1", source="input-cvss", target="output-act", label="Critical"),
        EdgeSchema(id="e2", source="input-cvss", target="output-attend", label="High"),
        EdgeSchema(id="e3", source="input-cvss", target="output-track", label="Low"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)


@pytest.fixture
def tree_with_lookup() -> TreeStructure:
    """
    Test tree with asset lookup:
    - INPUT node checks cvss_score (>= 7.0 -> asset lookup)
    - LOGIC node looks up asset criticality
    - Decision based on criticality
    """
    nodes = [
        NodeSchema(
            id="input-cvss",
            type=NodeType.INPUT,
            label="CVSS Score",
            config={"field": "cvss_score"},
            conditions=[
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=7.0, label="High"),
                NodeCondition(operator=ConditionOperator.LESS_THAN, value=7.0, label="Low"),
            ],
        ),
        NodeSchema(
            id="lookup-asset",
            type=NodeType.LOOKUP,
            label="Asset Criticality",
            config={
                "lookup_table": "assets",
                "lookup_key": "asset_id",
                "lookup_field": "criticality",
                "default_branch": 0,
            },
            conditions=[
                NodeCondition(operator=ConditionOperator.EQUALS, value="Critical", label="Critical"),
                NodeCondition(operator=ConditionOperator.EQUALS, value="High", label="High"),
                NodeCondition(operator=ConditionOperator.IN, value=["Medium", "Low"], label="Normal"),
            ],
        ),
        NodeSchema(
            id="output-act",
            type=NodeType.OUTPUT,
            label="Act",
            config={"decision": "Act", "color": "#ff0000"},
        ),
        NodeSchema(
            id="output-attend",
            type=NodeType.OUTPUT,
            label="Attend",
            config={"decision": "Attend", "color": "#ff9900"},
        ),
        NodeSchema(
            id="output-track",
            type=NodeType.OUTPUT,
            label="Track",
            config={"decision": "Track", "color": "#00ff00"},
        ),
    ]

    edges = [
        EdgeSchema(id="e1", source="input-cvss", target="lookup-asset", label="High"),
        EdgeSchema(id="e2", source="input-cvss", target="output-track", label="Low"),
        EdgeSchema(id="e3", source="lookup-asset", target="output-act", label="Critical"),
        EdgeSchema(id="e4", source="lookup-asset", target="output-attend", label="High"),
        EdgeSchema(id="e5", source="lookup-asset", target="output-track", label="Normal"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)


@pytest.fixture
def compound_condition_tree() -> TreeStructure:
    """
    Test tree with compound conditions:
    - INPUT node checks cvss_av AND cvss_ac in compound mode
    - If cvss_av=Network AND cvss_ac=Low -> Act
    - If cvss_av=Network OR cvss_ac=Low -> Attend
    - Otherwise -> Track
    """
    nodes = [
        NodeSchema(
            id="input-compound",
            type=NodeType.INPUT,
            label="CVSS Compound",
            config={"field": "cvss_av"},
            conditions=[
                NodeCondition(
                    label="Network+Low",
                    logic="AND",
                    criteria=[
                        SimpleConditionCriteria(field="cvss_av", operator=ConditionOperator.EQUALS, value="Network"),
                        SimpleConditionCriteria(field="cvss_ac", operator=ConditionOperator.EQUALS, value="Low"),
                    ],
                ),
                NodeCondition(
                    label="Network OR Low",
                    logic="OR",
                    criteria=[
                        SimpleConditionCriteria(field="cvss_av", operator=ConditionOperator.EQUALS, value="Network"),
                        SimpleConditionCriteria(field="cvss_ac", operator=ConditionOperator.EQUALS, value="Low"),
                    ],
                ),
                NodeCondition(
                    label="Other",
                    operator=ConditionOperator.IS_NOT_NULL,
                    value=None,
                ),
            ],
        ),
        NodeSchema(
            id="output-act",
            type=NodeType.OUTPUT,
            label="Act",
            config={"decision": "Act", "color": "#ff0000"},
        ),
        NodeSchema(
            id="output-attend",
            type=NodeType.OUTPUT,
            label="Attend",
            config={"decision": "Attend", "color": "#ff9900"},
        ),
        NodeSchema(
            id="output-track",
            type=NodeType.OUTPUT,
            label="Track",
            config={"decision": "Track", "color": "#00ff00"},
        ),
    ]

    edges = [
        EdgeSchema(id="e1", source="input-compound", target="output-act", source_handle="handle-0", label="Network+Low"),
        EdgeSchema(id="e2", source="input-compound", target="output-attend", source_handle="handle-1", label="Network OR Low"),
        EdgeSchema(id="e3", source="input-compound", target="output-track", source_handle="handle-2", label="Other"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)


@pytest.fixture
def multi_input_tree() -> TreeStructure:
    """
    Test tree with multi-input node (input_count=2):
    - INPUT node "kev" (2 outputs: true/false)
    - INPUT node "Technical Impact" (input_count=2, 2 conditions each: >=9 / <9)
    - 4 output nodes
    """
    nodes = [
        NodeSchema(
            id="input-kev",
            type=NodeType.INPUT,
            label="KEV",
            config={"field": "kev"},
            conditions=[
                NodeCondition(operator=ConditionOperator.EQUALS, value=True, label="Active"),
                NodeCondition(operator=ConditionOperator.EQUALS, value=False, label="None"),
            ],
        ),
        NodeSchema(
            id="input-impact",
            type=NodeType.INPUT,
            label="Technical Impact",
            config={"field": "cvss_score", "input_count": 2},
            conditions=[
                NodeCondition(operator=ConditionOperator.GREATER_THAN_OR_EQUAL, value=9.0, label="Total"),
                NodeCondition(operator=ConditionOperator.LESS_THAN, value=9.0, label="Partial"),
            ],
        ),
        NodeSchema(
            id="output-act",
            type=NodeType.OUTPUT,
            label="Act",
            config={"decision": "Act", "color": "#ff0000"},
        ),
        NodeSchema(
            id="output-attend",
            type=NodeType.OUTPUT,
            label="Attend",
            config={"decision": "Attend", "color": "#ff9900"},
        ),
        NodeSchema(
            id="output-track-star",
            type=NodeType.OUTPUT,
            label="Track*",
            config={"decision": "Track*", "color": "#ffff00"},
        ),
        NodeSchema(
            id="output-track",
            type=NodeType.OUTPUT,
            label="Track",
            config={"decision": "Track", "color": "#00ff00"},
        ),
    ]

    edges = [
        # kev=true -> input-impact input 0
        EdgeSchema(id="e1", source="input-kev", target="input-impact", source_handle="handle-0", target_handle="input-0", label="Active"),
        # kev=false -> input-impact input 1
        EdgeSchema(id="e2", source="input-kev", target="input-impact", source_handle="handle-1", target_handle="input-1", label="None"),
        # input-impact, input 0 (kev=true), cvss>=9 -> Act
        EdgeSchema(id="e3", source="input-impact", target="output-act", source_handle="handle-0-0"),
        # input-impact, input 0 (kev=true), cvss<9 -> Attend
        EdgeSchema(id="e4", source="input-impact", target="output-attend", source_handle="handle-0-1"),
        # input-impact, input 1 (kev=false), cvss>=9 -> Track*
        EdgeSchema(id="e5", source="input-impact", target="output-track-star", source_handle="handle-1-0"),
        # input-impact, input 1 (kev=false), cvss<9 -> Track
        EdgeSchema(id="e6", source="input-impact", target="output-track", source_handle="handle-1-1"),
    ]

    return TreeStructure(nodes=nodes, edges=edges)
