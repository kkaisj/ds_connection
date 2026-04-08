from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DC 数据连接器"
    debug: bool = True

    # MySQL
    db_host: str = "172.16.11.148"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "J9@A#uE9zcP!whb"
    db_name: str = "dc_connection"

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return f"mysql+aiomysql://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        """Alembic 迁移使用的同步连接串。"""
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return f"mysql+pymysql://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "DC_", "env_file": ".env"}


settings = Settings()
