# GigGuard AI Testing Suite

Comprehensive automated testing framework with unit, integration, and performance tests.

## Running Tests

### All Tests
```bash
pytest tests/
```

### Unit Tests Only
```bash
pytest tests/ -m unit
```

### Integration Tests Only
```bash
pytest tests/ -m integration
```

### With Coverage Report
```bash
pytest tests/ --cov=backend --cov-report=html
```

### Specific Test File
```bash
pytest tests/test_monitoring.py -v
```

### Run and Stop on First Failure
```bash
pytest tests/ -x
```

## Test Structure

- `test_monitoring.py`: Metrics and health monitoring tests
- `test_database.py`: Database pooling and optimization tests
- `test_caching.py`: Caching layer functionality tests
- `test_load_balancer.py`: Load balancing strategy tests
- `test_api_integration.py`: API endpoint integration tests
- `conftest.py`: Pytest configuration and fixtures

## Test Markers

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests for API endpoints
- `@pytest.mark.slow`: Long-running tests
- `@pytest.mark.cache`: Cache-related tests
- `@pytest.mark.database`: Database-related tests
- `@pytest.mark.async`: Asynchronous tests

## Coverage Requirements

Minimum 80% code coverage is required for all merges. Check coverage with:

```bash
pytest tests/ --cov=backend --cov-report=term-missing
```

## CI/CD Pipeline

The automated CI/CD pipeline runs:

1. Unit and integration tests (Python 3.10, 3.11, 3.12)
2. Code formatting checks (black, isort)
3. Linting (flake8)
4. Security scanning (bandit, safety)
5. Docker build validation
6. Coverage validation (>80%)

Tests must pass before merging to main branch.

## Writing Tests

### Example Unit Test

```python
@pytest.mark.unit
class TestMyComponent:
    def test_something(self):
        result = my_function()
        assert result == expected_value
```

### Example Integration Test

```python
@pytest.mark.integration
def test_api_endpoint(test_client):
    response = test_client.get("/api/endpoint")
    assert response.status_code == 200
```

## Fixtures

Available fixtures in conftest.py:

- `test_client`: FastAPI test client
- `clean_cache`: Fresh cache instance
- `test_connection_pool`: Test database connection pool
- `test_load_balancer`: Test load balancer
- `sample_calculate_payload`: Sample API request data
- `sample_risk_payload`: Sample risk assessment data
- `sample_simulate_payload`: Sample simulation data
