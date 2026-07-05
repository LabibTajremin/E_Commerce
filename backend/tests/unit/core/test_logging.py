from src.core.logging import configure_logging, get_logger


def test_get_logger_returns_bound_logger_with_expected_methods() -> None:
    configure_logging(debug=True)
    logger = get_logger("test")
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
