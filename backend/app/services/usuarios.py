"""Administración de usuarios y roles (HU-06.2, solo coordinador)."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errores import ErrorApi
from app.core.paginacion import paginar
from app.models import Usuario


def listar_usuarios(db: Session, q: str | None, rol: str | None, pagina: int, tam: int) -> dict:
    """Personas en orden alfabético. `q` busca en el nombre o en el correo, sin distinguir mayúsculas."""
    consulta = select(Usuario).order_by(func.lower(Usuario.nombre), Usuario.id)
    if q and q.strip():
        # Parámetro de SQLAlchemy (autoescape trata % y _ como texto): el texto nunca se pega a mano en el SQL
        texto = q.strip().lower()
        consulta = consulta.where(
            or_(
                func.lower(Usuario.nombre).contains(texto, autoescape=True),
                func.lower(Usuario.correo).contains(texto, autoescape=True),
            )
        )
    if rol:
        consulta = consulta.where(Usuario.rol == rol)
    return paginar(db, consulta, pagina, tam)


def cambiar_rol(db: Session, usuario_id: int, rol: str) -> Usuario:
    """El cambio surte efecto en la siguiente petición de esa persona: usuario_actual lee el rol de la base."""
    usuario = _usuario_o_404(db, usuario_id)
    if usuario.rol == "coordinador" and rol != "coordinador":
        _exigir_otro_coordinador(db, usuario)
    usuario.rol = rol
    db.commit()
    db.refresh(usuario)
    return usuario


def cambiar_suspension(db: Session, usuario_id: int, suspendido: bool) -> Usuario:
    """Suspender (activo=False) impide entrar y conserva los reportes. Reactivar vuelve a dar acceso."""
    usuario = _usuario_o_404(db, usuario_id)
    if suspendido:
        _exigir_otro_coordinador(db, usuario)
    usuario.activo = not suspendido
    db.commit()
    db.refresh(usuario)
    return usuario


def _usuario_o_404(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ErrorApi(404, "NO_ENCONTRADO", "Esa cuenta no existe")
    return usuario


def _exigir_otro_coordinador(db: Session, usuario: Usuario) -> None:
    """Si `usuario` es un coordinador activo, tiene que quedar otro coordinador activo (409 ULTIMO_COORDINADOR).

    Sin esto la plataforma se quedaría sin nadie que administre. Aplica también a quien se lo hace a sí mismo.
    with_for_update bloquea esas filas en PostgreSQL para que dos coordinadores no se quiten el acceso a la vez.
    """
    if usuario.rol != "coordinador" or not usuario.activo:
        return  # una cuenta que no es coordinadora activa no cuenta como "el último"
    activos = db.scalars(
        select(Usuario.id).where(Usuario.rol == "coordinador", Usuario.activo.is_(True)).with_for_update()
    ).all()
    if len(activos) <= 1:
        raise ErrorApi(
            409,
            "ULTIMO_COORDINADOR",
            "Es el último coordinador activo. Nombra o reactiva a otro coordinador antes de quitarle el rol "
            "o suspenderlo",
        )
