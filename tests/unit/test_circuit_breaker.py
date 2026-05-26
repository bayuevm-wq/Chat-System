import pytest
import asyncio
import time
from unittest.mock import AsyncMock
from src.shared.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError

@pytest.mark.asyncio
async def test_closed_state_passes():
    breaker = CircuitBreaker("test-cb", failure_threshold=2, recovery_timeout=0.1)
    
    mock_func = AsyncMock(return_value="success")
    
    res = await breaker(mock_func)
    assert res == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0

@pytest.mark.asyncio
async def test_opens_after_threshold():
    breaker = CircuitBreaker("test-cb", failure_threshold=2, recovery_timeout=0.1)
    mock_func = AsyncMock(side_effect=ValueError("fail"))

    # Failure 1
    with pytest.raises(ValueError):
        await breaker(mock_func)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 1

    # Failure 2 (trips circuit)
    with pytest.raises(ValueError):
        await breaker(mock_func)
    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 2

@pytest.mark.asyncio
async def test_open_rejects_calls():
    breaker = CircuitBreaker("test-cb", failure_threshold=1, recovery_timeout=60.0)
    mock_func = AsyncMock(side_effect=ValueError("fail"))
    
    # Trip it
    with pytest.raises(ValueError):
        await breaker(mock_func)
        
    assert breaker.state == CircuitState.OPEN
    
    # Next call should be rejected immediately without invoking the mock function
    mock_func2 = AsyncMock(return_value="should-not-run")
    with pytest.raises(CircuitBreakerOpenError):
        await breaker(mock_func2)
        
    mock_func2.assert_not_called()

@pytest.mark.asyncio
async def test_half_open_after_timeout():
    # Set tiny recovery timeout
    breaker = CircuitBreaker("test-cb", failure_threshold=1, recovery_timeout=0.01)
    mock_func = AsyncMock(side_effect=ValueError("fail"))
    
    # Trip it
    with pytest.raises(ValueError):
        await breaker(mock_func)
        
    assert breaker.state == CircuitState.OPEN
    
    # Sleep to exceed recovery timeout
    await asyncio.sleep(0.015)
    
    mock_func_probe = AsyncMock(return_value="probe-success")
    res = await breaker(mock_func_probe)
    
    assert res == "probe-success"
    # Success in half-open state should transition back to CLOSED
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0

@pytest.mark.asyncio
async def test_half_open_failure_reopens():
    breaker = CircuitBreaker("test-cb", failure_threshold=1, recovery_timeout=0.01)
    mock_func = AsyncMock(side_effect=ValueError("fail"))
    
    # Trip it
    with pytest.raises(ValueError):
        await breaker(mock_func)
        
    assert breaker.state == CircuitState.OPEN
    await asyncio.sleep(0.015)
    
    # Fail during HALF_OPEN probe
    mock_func_probe_fail = AsyncMock(side_effect=ValueError("probe-fail"))
    with pytest.raises(ValueError):
        await breaker(mock_func_probe_fail)
        
    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 2
