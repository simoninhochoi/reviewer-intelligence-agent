"""로깅 설정"""
import logging
from rich.logging import RichHandler


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Rich 핸들러를 사용한 프로젝트 로거 설정"""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )
    logger = logging.getLogger("ria")
    logger.setLevel(level)
    return logger


logger = setup_logging()
