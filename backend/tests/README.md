# Unit Tests for Clip Generation Pipeline

## Overview

Comprehensive unit test suite for clip creation, moment detection, authentication, and clip management APIs. Tests are organized by module and use pytest framework with SQLite in-memory database for fast execution.

## Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication tests (15+ tests)
├── test_clip_apis.py        # Clip CRUD and access control (20+ tests)
├── test_moment_detection.py # Moment detection algorithm (15+ tests)
└── README.md               # This file
```

## Test Categories

### Unit Tests (50+ tests) ✅
Fast, isolated tests that validate individual components:

- **test_auth.py** - Token creation, validation, expiry
  - Token generation and hashing
  - Session verification
  - User identification
  - Security properties

- **test_clip_apis.py** - Clip CRUD and access control
  - Input validation (title, description, tags)
  - Create, read, update operations
  - Common queries (pending, recent, approved)
  - OWASP #1 access control enforcement

- **test_moment_detection.py** - Moment detection algorithm
  - Score calculation logic
  - Sensitivity parameter impact
  - Threshold detection
  - Data model validation

## Running Tests

### Run All Tests
```bash
pytest backend/tests/
```

### Run Specific Test File
```bash
pytest backend/tests/test_auth.py
```

### Run Specific Test Class
```bash
pytest backend/tests/test_auth.py::TestTokenCreation
```

### Run Specific Test
```bash
pytest backend/tests/test_auth.py::TestTokenCreation::test_create_session_token_returns_string
```

### Run with Markers
```bash
# Run only unit tests (fast)
pytest backend/tests/ -m unit

# Run only auth tests
pytest backend/tests/ -m auth

# Run only security tests
pytest backend/tests/ -m security

# Run unit AND auth tests
pytest backend/tests/ -m "unit and auth"
```

### Run with Coverage
```bash
pytest backend/tests/ --cov=backend --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`

### Run with Parallel Execution (faster)
```bash
pytest backend/tests/ -n auto
```

Distributes tests across CPU cores

### Run with Timeout (prevent hanging tests)
```bash
pytest backend/tests/ --timeout=300
```

### Run with Verbose Output
```bash
pytest backend/tests/ -v
```

### Run with Short Traceback
```bash
pytest backend/tests/ --tb=short
```

## Test Fixtures

All tests use shared fixtures from `conftest.py`:

### Database Fixtures
- `test_db_engine` - In-memory SQLite database
- `db_session` - Fresh database session per test (auto-rollback)

### User/Streamer Fixtures
- `test_user` - Standard test user (role="streamer")
- `test_streamer` - Associated streamer record
- `test_stream_session` - Active stream session
- `test_clip` - Sample clip for testing

### Auth Fixtures
- `auth_token` - Valid 24-hour session token
- `expired_token` - Expired token for testing

### Example Test Using Fixtures
```python
def test_something(db_session: Session, test_user, test_streamer, test_clip):
    """Fixtures are automatically injected"""
    assert test_user.role == "streamer"
    assert test_clip.streamer_id == test_streamer.id
    
    # Database changes are automatically rolled back
    test_user.email = "new@example.com"
    db_session.commit()
```

## Test Patterns

### Testing Database Operations
```python
@pytest.mark.unit
class TestClipCRUD:
    def test_create_clip_basic(self, db_session, test_clip):
        """Should create clip with basic fields"""
        assert test_clip.id is not None
        assert test_clip.status == "pending"
```

### Testing Security (OWASP #1)
```python
@pytest.mark.security
def test_clip_scoped_to_streamer(self, db_session, test_streamer):
    """Clips should be scoped to streamer"""
    # Should find with correct streamer_id
    retrieved = db_session.query(Clip).filter(
        Clip.id == clip.id,
        Clip.streamer_id == test_streamer.id
    ).first()
    assert retrieved is not None
    
    # Should NOT find with wrong streamer_id
    not_retrieved = db_session.query(Clip).filter(
        Clip.id == clip.id,
        Clip.streamer_id == 99999
    ).first()
    assert not_retrieved is None
```

### Testing Validation
```python
def test_validate_clip_title_too_long(self):
    """Title exceeding max length should be truncated"""
    long_title = "A" * 300
    validated = validate_clip_title(long_title)
    assert len(validated) <= 255
```

## Test Markers

Mark tests to organize by category:

```python
@pytest.mark.unit           # Fast, isolated
@pytest.mark.integration    # Slower, full workflow
@pytest.mark.auth           # Authentication
@pytest.mark.security       # Security-related
@pytest.mark.clip           # Clip management
@pytest.mark.moment         # Moment detection
class TestMyFeature:
    pass
```

## Coverage Goals

Target coverage by module:

| Module | Target | Current |
|--------|--------|---------|
| auth.py | 95%+ | -% |
| clip_apis | 90%+ | -% |
| moment_detection | 85%+ | -% |
| security.py | 95%+ | -% |
| **Overall** | **90%+** | **-%** |

Generate coverage report:
```bash
pytest --cov=backend --cov-report=term-missing --cov-report=html
```

## Common Issues

### Test Database Not Found
```
sqlite3.OperationalError: unable to open database file
```
Solution: `conftest.py` uses `:memory:` SQLite, no files needed. Check Python path.

### Import Errors
```
ModuleNotFoundError: No module named 'backend'
```
Solution: Run pytest from project root. Ensure `PYTHONPATH` includes project directory:
```bash
cd /path/to/kazumi
export PYTHONPATH=$PWD
pytest backend/tests/
```

### Async Test Timeout
```
pytest.PytestUnraisableExceptionWarning: Exception ignored in asyncio
```
Solution: Tests use `asyncio_mode = auto`. Ensure `pytest-asyncio` is installed.

### Fixture Not Found
```
fixture 'db_session' not found
```
Solution: Fixtures are in `conftest.py`. Ensure test file imports from same directory or `conftest.py` is in parent.

## Integration Tests (Coming Next)

After unit tests pass, add integration tests for:

- Full clip creation workflow (detect → create → store → export)
- End-to-end API testing
- Database transaction handling
- File I/O operations
- Error recovery scenarios

## Performance Testing (After Load Testing)

Benchmark critical paths:

```python
@pytest.mark.benchmark
def test_clip_query_performance(benchmark):
    """Benchmark common clip query"""
    def query():
        return db.query(Clip).filter_by(streamer_id=1).all()
    
    result = benchmark(query)
    assert len(result) > 0
```

Run with:
```bash
pytest backend/tests/ --benchmark-only
```

## CI/CD Integration

Add to CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run Unit Tests
  run: |
    pip install -r requirements-test.txt
    pytest backend/tests/ -m unit --cov=backend --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Next Steps

1. ✅ Create unit test suite (THIS STEP)
2. → Add integration tests
3. → Add load/stress testing
4. → Set up CI/CD integration
5. → Achieve 90%+ code coverage

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#using-the-session-in-concurrent-or-multiple-threaded-environments)
- [Fixture Best Practices](https://docs.pytest.org/en/stable/fixture.html)
