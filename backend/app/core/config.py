"""Configuración de la aplicación.

Todo viene de variables de entorno (factor III de The Twelve-Factor App). En desarrollo se pueden poner en el
archivo `.env` de la raíz del repositorio; en producción las pone la plataforma (Render, Docker...).
"""

from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

# backend/app/core/config.py -> subimos 3 niveles para llegar a la raíz del repositorio
RAIZ = Path(__file__).resolve().parents[3]

# Clave pública de ejemplo: sirve para desarrollar, pero en producción el backend se niega a arrancar con ella
SECRET_KEY_EJEMPLO = "cambia-esta-clave-de-ejemplo-solo-para-desarrollo"

ENTORNOS = ("desarrollo", "produccion")


class Settings(BaseSettings):
    # hide_input_in_errors: si la configuración es inválida, el error NO imprime los valores recibidos
    # (podrían ser la SECRET_KEY o la contraseña de la base, y los errores terminan en los logs del servidor).
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore", hide_input_in_errors=True)

    # Cadena de conexión. Neon/Render la entregan completa; en la laptop apunta al PostgreSQL de Docker.
    # 127.0.0.1 y no "localhost": en Windows "localhost" resuelve primero a IPv6 y tarda.
    database_url: str = "postgresql+psycopg://liebre:liebre@127.0.0.1:5432/liebre_urbana"

    # "desarrollo" o "produccion". En producción se exigen valores seguros (ver _validar_produccion).
    entorno: str = "desarrollo"

    secret_key: str = SECRET_KEY_EJEMPLO
    jwt_algorithm: str = "HS256"

    # Dominios del frontend que pueden llamar a la API, separados por comas. Nunca "*".
    cors_origins: str = "http://localhost:5173"

    # Contraseñas de las cuentas de demostración que crea db/seed.py (en producción son obligatorias)
    seed_ciudadano_password: str | None = None
    seed_moderador_password: str | None = None
    seed_coordinador_password: str | None = None

    @field_validator("entorno")
    @classmethod
    def _entorno_valido(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ENTORNOS:
            raise ValueError(f"ENTORNO debe ser uno de: {', '.join(ENTORNOS)}")
        return v

    @model_validator(mode="after")
    def _validar_produccion(self) -> "Settings":
        """En producción no se acepta la clave de ejemplo (es pública: está en el repositorio)."""
        if self.es_produccion and (self.secret_key == SECRET_KEY_EJEMPLO or len(self.secret_key) < 32):
            raise ValueError("En producción SECRET_KEY debe ser aleatoria y de 32 caracteres o más (no la de ejemplo)")
        return self

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "produccion"

    @property
    def sqlalchemy_url(self) -> URL:
        """URL para SQLAlchemy. Neon entrega "postgresql://..." y hay que indicar el driver psycopg 3."""
        url = self.database_url
        for prefijo in ("postgres://", "postgresql://"):
            if url.startswith(prefijo):
                url = "postgresql+psycopg://" + url[len(prefijo):]
        return make_url(url)

    @property
    def cors_origins_lista(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
