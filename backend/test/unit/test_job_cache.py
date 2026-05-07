"""
Tests for TICKET-029: Cache de resultados por hash del código
"""

from unittest.mock import AsyncMock, patch

import pytest

from models.model import Job, Status
from services.jobs_services import JobService
from services.redis_service import RedisService


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def mock_redis_service() -> AsyncMock:
    """Create a mock RedisService."""
    redis = AsyncMock(spec=RedisService)
    redis.get = AsyncMock()
    redis.set = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    return redis


def make_job(
    job_id: int = 1,
    code: str = "def test():\n    pass",
    filename: str = "test.py",
    status: Status = Status.PENDING,
) -> Job:
    """Create a mock Job."""
    job = Job(
        id=job_id,
        user_id=1,
        filename=filename,
        code=code,
        status=status,
        result=None,
        error_message=None,
    )
    return job


# ============================================================================
# TEST 1: Cache miss ejecuta el agente y guarda el resultado
# ============================================================================


@pytest.mark.asyncio
async def test_cache_miss_executes_agent_and_saves_result(
    mock_db_session: AsyncMock, mock_redis_service: AsyncMock
) -> None:
    """
    Cuando no hay resultado en caché (cache MISS):
    1. Debe ejecutar el agente
    2. Debe guardar el resultado en caché
    3. Debe actualizar el job a COMPLETED
    """
    # Arrange
    job = make_job(job_id=1, code="print('hello')", filename="test.py")
    mock_db_session.get = AsyncMock(return_value=job)

    # Cache MISS - No hay resultado en caché
    mock_redis_service.get = AsyncMock(return_value=None)
    mock_redis_service.set = AsyncMock(return_value=True)

    agent_result = "# Test\ndef test_hello():\n    assert True"

    service = JobService(mock_db_session, mock_redis_service)

    # Mock del agente
    with patch("services.jobs_services.chat", AsyncMock(return_value=agent_result)) as mock_chat:
        # Act
        await service.run_analysis(1)

        # Assert
        # 1. El agente fue ejecutado
        mock_chat.assert_awaited_once_with(code="print('hello')", filename="test.py")

    # 2. El resultado se guardó en caché
    assert mock_redis_service.set.await_count == 1
    cache_key_arg = mock_redis_service.set.call_args[0][0]
    assert cache_key_arg.startswith("agent_result:")
    assert mock_redis_service.set.call_args[0][1] == agent_result

    # 3. El job se actualizó a COMPLETED
    assert job.status == Status.COMPLETED
    assert job.result == agent_result


# ============================================================================
# TEST 2: Cache hit retorna el resultado sin llamar al agente
# ============================================================================


@pytest.mark.asyncio
async def test_cache_hit_returns_result_without_calling_agent(
    mock_db_session: AsyncMock, mock_redis_service: AsyncMock
) -> None:
    """
    Cuando hay resultado en caché (cache HIT):
    1. NO debe ejecutar el agente
    2. Debe usar el resultado del caché
    3. Debe actualizar el job a COMPLETED con resultado cacheado
    """
    # Arrange
    job = make_job(job_id=1, code="print('hello')", filename="test.py")
    mock_db_session.get = AsyncMock(return_value=job)

    cached_result = "# Cached Test\ndef test_cached():\n    pass"

    # Cache HIT - Hay resultado en caché
    mock_redis_service.get = AsyncMock(return_value=cached_result)

    service = JobService(mock_db_session, mock_redis_service)

    # Mock del agente (no debería ser llamado)
    with patch("services.jobs_services.chat", AsyncMock()) as mock_chat:
        # Act
        await service.run_analysis(1)

        # Assert
        # 1. El agente NO fue ejecutado
        mock_chat.assert_not_awaited()

    # 2. El resultado del caché fue usado
    assert job.status == Status.COMPLETED
    assert job.result == cached_result

    # 3. Se llamó a redis.get para obtener del caché
    mock_redis_service.get.assert_awaited_once()


# ============================================================================
# TEST 3: Dos inputs idénticos producen la misma clave de caché
# ============================================================================


@pytest.mark.asyncio
async def test_identical_inputs_produce_same_cache_key(
    mock_db_session: AsyncMock, mock_redis_service: AsyncMock
) -> None:
    """
    El mismo código y filename deben producir el mismo hash/clave de caché.
    """
    # Arrange
    code = "def hello():\n    print('world')"
    filename = "hello.py"

    job1 = make_job(job_id=1, code=code, filename=filename)
    job2 = make_job(job_id=2, code=code, filename=filename)

    mock_redis_service.get = AsyncMock(return_value=None)
    mock_redis_service.set = AsyncMock(return_value=True)

    service = JobService(mock_db_session, mock_redis_service)

    # Track the cache keys used
    cache_keys = []

    async def track_cache_key(*args, **kwargs):
        cache_keys.append(args[0])
        return None

    mock_redis_service.get = track_cache_key

    # Act - Process first job
    mock_db_session.get = AsyncMock(return_value=job1)
    with patch("services.jobs_services.chat", AsyncMock(return_value="result1")):
        await service.run_analysis(1)

    # Act - Process second job
    mock_db_session.get = AsyncMock(return_value=job2)
    with patch("services.jobs_services.chat", AsyncMock(return_value="result2")):
        await service.run_analysis(2)

    # Assert - Both jobs produced the same cache key
    assert len(cache_keys) == 2
    assert cache_keys[0] == cache_keys[1]
    assert cache_keys[0].startswith("agent_result:")


# ============================================================================
# TEST 4: Dos inputs diferentes producen claves distintas
# ============================================================================


@pytest.mark.asyncio
async def test_different_inputs_produce_different_cache_keys(
    mock_db_session: AsyncMock, mock_redis_service: AsyncMock
) -> None:
    """
    Código diferente o filename diferente deben producir claves de caché diferentes.
    """
    # Arrange
    job1 = make_job(job_id=1, code="print('hello')", filename="test1.py")
    job2 = make_job(job_id=2, code="print('world')", filename="test2.py")

    mock_redis_service.get = AsyncMock(return_value=None)
    mock_redis_service.set = AsyncMock(return_value=True)

    service = JobService(mock_db_session, mock_redis_service)

    cache_keys = []

    async def track_cache_key(*args, **kwargs):
        cache_keys.append(args[0])
        return None

    mock_redis_service.get = track_cache_key

    # Act - Process first job
    mock_db_session.get = AsyncMock(return_value=job1)
    with patch("services.jobs_services.chat", AsyncMock(return_value="result1")):
        await service.run_analysis(1)

    # Act - Process second job
    mock_db_session.get = AsyncMock(return_value=job2)
    with patch("services.jobs_services.chat", AsyncMock(return_value="result2")):
        await service.run_analysis(2)

    # Assert - Both jobs produced different cache keys
    assert len(cache_keys) == 2
    assert cache_keys[0] != cache_keys[1]


# ============================================================================
# TEST 5: Hash computation is deterministic
# ============================================================================


def test_compute_code_hash_is_deterministic() -> None:
    """
    El hash debe ser determinístico: mismo input = mismo hash.
    """
    code = "def test():\n    pass"
    filename = "test.py"

    hash1 = JobService._compute_code_hash(code, filename)
    hash2 = JobService._compute_code_hash(code, filename)

    assert hash1 == hash2


def test_compute_code_hash_different_for_different_inputs() -> None:
    """
    El hash debe ser diferente para inputs diferentes.
    """
    code1 = "def test1():\n    pass"
    code2 = "def test2():\n    pass"
    filename = "test.py"

    hash1 = JobService._compute_code_hash(code1, filename)
    hash2 = JobService._compute_code_hash(code2, filename)

    assert hash1 != hash2


def test_compute_code_hash_includes_filename() -> None:
    """
    El hash debe considerar el filename también.
    """
    code = "def test():\n    pass"
    filename1 = "test1.py"
    filename2 = "test2.py"

    hash1 = JobService._compute_code_hash(code, filename1)
    hash2 = JobService._compute_code_hash(code, filename2)

    assert hash1 != hash2


# ============================================================================
# TEST 6: Service works without Redis (graceful degradation)
# ============================================================================


@pytest.mark.asyncio
async def test_service_works_without_redis(mock_db_session: AsyncMock) -> None:
    """
    El servicio debe funcionar correctamente sin Redis (sin caché).
    """
    # Arrange
    job = make_job(job_id=1, code="print('hello')", filename="test.py")
    mock_db_session.get = AsyncMock(return_value=job)

    # Service without Redis
    service = JobService(mock_db_session, redis_service=None)

    agent_result = "# Test\ndef test_hello():\n    pass"

    # Act
    with patch("services.jobs_services.chat", AsyncMock(return_value=agent_result)):
        await service.run_analysis(1)

    # Assert - Job was processed successfully
    assert job.status == Status.COMPLETED
    assert job.result == agent_result


# ============================================================================
# TEST 7: TTL is configurable from settings
# ============================================================================


@pytest.mark.asyncio
async def test_cache_ttl_from_settings(
    mock_db_session: AsyncMock, mock_redis_service: AsyncMock
) -> None:
    """
    El TTL del caché debe venir de settings.CACHE_TTL.
    """
    # Arrange
    job = make_job(job_id=1)
    mock_db_session.get = AsyncMock(return_value=job)
    mock_redis_service.get = AsyncMock(return_value=None)
    mock_redis_service.set = AsyncMock(return_value=True)

    service = JobService(mock_db_session, mock_redis_service)

    # Act
    with patch("services.jobs_services.chat", AsyncMock(return_value="result")):
        await service.run_analysis(1)

    # Assert - TTL from settings was used
    from core.config import settings

    set_call_args = mock_redis_service.set.call_args
    assert set_call_args[1]["ttl"] == settings.CACHE_TTL