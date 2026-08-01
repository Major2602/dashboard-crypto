"""Application configuration using Pydantic."""
import logging
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """Static, process-wide configuration validated by Pydantic."""
    
    target_tickers: tuple[str, ...] = Field(default=("BTC", "ETH", "XRP", "SOL", "ADA"))
    default_theme: str = "dark"
    
    data_dir: Path = Field(default=BASE_DIR / "data")
    quotes_filename: str = "cr_quotes_base_24.csv"
    report_filename: str = "cr_report_24.csv"
    csv_separator: str = ";"
    
    debug: bool = Field(default=False, alias="DASH_DEBUG")
    host: str = "0.0.0.0"
    port: int = Field(default=8080)
    log_level: str = "INFO"
    sentry_dsn: str | None = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def ticker_colors(self) -> dict[str, str]:
        return {
            t: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
            for i, t in enumerate(self.target_tickers)
        }

    @property
    def quotes_path(self) -> Path:
        return self.data_dir / self.quotes_filename

    @property
    def report_path(self) -> Path:
        return self.data_dir / self.report_filename

settings = Settings()

def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
