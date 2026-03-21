from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "BVBB_"}

    base_url: str = "https://bvbb-badminton.liga.nu/cgi-bin/WebObjects/nuLigaBADDE.woa/wa"
    rate_limit_delay: float = 0.5
    max_concurrent: int = 5
    log_level: str = "INFO"
    db_path: str = "data/bvbb.db"


settings = Settings()


def derive_season(championship_code: str) -> str:
    """Derive the season string from a championship code.

    ``"BBMM 25/26"`` -> ``"2025/26"``
    """
    parts = championship_code.split()
    if len(parts) < 2 or "/" not in parts[1]:
        raise ValueError(f"Cannot derive season from {championship_code!r}")
    short = parts[1]  # "25/26"
    start, end = short.split("/", 1)
    return f"20{start}/{end}"
