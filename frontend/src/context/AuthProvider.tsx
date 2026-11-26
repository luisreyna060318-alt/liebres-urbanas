import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { iniciarSesion, pedirYo, registrar, renovarSesion } from '../api/auth.ts'
import { ErrorApi, registrarAlExpirarSesion } from '../api/cliente.ts'
import { borrarSesion, guardarSesion, leerToken, leerUsuarioGuardado } from '../api/sesion.ts'
import type { DatosRegistro, Rol, SesionRespuesta, UsuarioPublico } from '../api/tipos.ts'
import { useReglas } from '../hooks/useReglas.ts'
import { AuthContext } from './AuthContexto.ts'

// El token se renueva con POST /auth/refresh mientras la persona está activa, pero como máximo una vez cada 5 minutos
const ENTRE_RENOVACIONES_MS = 5 * 60_000
// Cada cuánto se revisa si ya pasó el tiempo de inactividad
const REVISION_INACTIVIDAD_MS = 15_000
// Acciones que cuentan como "actividad" de la persona
const EVENTOS_ACTIVIDAD = ['pointerdown', 'keydown', 'scroll', 'touchstart'] as const

const AVISO_CADUCADA = 'Tu sesión caducó. Inicia sesión de nuevo para continuar.'
const AVISO_INACTIVIDAD = 'Cerramos tu sesión por inactividad. Inicia sesión de nuevo para continuar.'

export function AuthProvider({ children }: { children: ReactNode }) {
  // Si hay un token guardado, se muestra de inmediato el usuario guardado y en segundo plano se confirma con la API
  const [usuario, setUsuario] = useState<UsuarioPublico | null>(() => (leerToken() ? leerUsuarioGuardado() : null))
  const [cargando, setCargando] = useState(() => leerToken() !== null)
  const [aviso, setAviso] = useState<string | null>(null)
  const [salioPorSuCuenta, setSalioPorSuCuenta] = useState(false)

  // Valor de GET /api/reglas (30 minutos si la API aún no responde)
  const { inactividad_min } = useReglas()

  // Datos para los temporizadores: son refs porque cambian muy seguido y no deben redibujar la pantalla
  const hayUsuario = useRef(usuario !== null)
  const ultimaActividad = useRef(0) // se pone al día con cada acción de la persona
  const ultimaRenovacion = useRef(0) // 0 = token de edad desconocida: se renueva con la primera actividad
  const renovando = useRef(false)

  // Guarda la sesión que devuelve el servidor (registro, login o refresh)
  const abrirSesion = useCallback((sesion: SesionRespuesta) => {
    guardarSesion(sesion.access_token, sesion.usuario)
    hayUsuario.current = true
    ultimaActividad.current = Date.now()
    ultimaRenovacion.current = Date.now()
    setUsuario(sesion.usuario)
    setAviso(null)
    setSalioPorSuCuenta(false)
  }, [])

  // Cierra la sesión (a mano, por inactividad o porque el servidor respondió 401)
  const cerrar = useCallback((mensaje: string | null) => {
    borrarSesion()
    hayUsuario.current = false
    setUsuario(null)
    setAviso(mensaje)
  }, [])

  // Al abrir la app: confirmar la sesión guardada y traer el rol actual (puede haber cambiado)
  useEffect(() => {
    const token = leerToken()
    if (token === null) return

    let vigente = true
    pedirYo()
      .then((u) => {
        if (!vigente) return
        guardarSesion(token, u)
        setUsuario(u)
      })
      .catch((e: unknown) => {
        // Sin conexión no se puede saber: se conserva lo guardado. Con cualquier otro error la sesión ya no sirve.
        if (!vigente || (e instanceof ErrorApi && e.status === 0)) return
        borrarSesion()
        hayUsuario.current = false
        setUsuario(null)
      })
      .finally(() => {
        if (vigente) setCargando(false)
      })

    return () => {
      vigente = false
    }
  }, [])

  // Si la API responde 401 NO_AUTENTICADO en cualquier petición, se cierra la sesión con un aviso.
  // Las rutas privadas ven usuario = null y mandan a /login.
  useEffect(() => {
    registrarAlExpirarSesion(() => {
      if (!hayUsuario.current) return
      cerrar(AVISO_CADUCADA)
    })
    return () => registrarAlExpirarSesion(null)
  }, [cerrar])

  // Mientras hay sesión: renovar el token con la actividad y cerrar por inactividad (HU-01.2 CA4)
  const haySesion = usuario !== null
  useEffect(() => {
    if (!haySesion) return

    const limiteMs = inactividad_min * 60_000
    ultimaActividad.current = Date.now()

    function alActividad() {
      const ahora = Date.now()
      ultimaActividad.current = ahora
      if (renovando.current || ahora - ultimaRenovacion.current < ENTRE_RENOVACIONES_MS) return

      renovando.current = true
      ultimaRenovacion.current = ahora // se anota antes: si falla, no se reintenta en cada clic
      renovarSesion()
        .then((sesion) => {
          // Si la persona salió mientras llegaba la respuesta, no se vuelve a abrir su sesión
          if (hayUsuario.current) abrirSesion(sesion)
        })
        .catch(() => {
          // Un 401 ya cerró la sesión en el cliente de la API; cualquier otro fallo se ignora y se reintenta después
        })
        .finally(() => {
          renovando.current = false
        })
    }

    for (const evento of EVENTOS_ACTIVIDAD) window.addEventListener(evento, alActividad, { passive: true })
    const reloj = window.setInterval(() => {
      if (Date.now() - ultimaActividad.current >= limiteMs) cerrar(AVISO_INACTIVIDAD)
    }, REVISION_INACTIVIDAD_MS)

    return () => {
      for (const evento of EVENTOS_ACTIVIDAD) window.removeEventListener(evento, alActividad)
      window.clearInterval(reloj)
    }
  }, [haySesion, inactividad_min, abrirSesion, cerrar])

  const login = useCallback(
    async (correo: string, password: string) => {
      abrirSesion(await iniciarSesion({ correo, password }))
    },
    [abrirSesion],
  )

  const registro = useCallback(
    async (datos: DatosRegistro) => {
      abrirSesion(await registrar(datos))
    },
    [abrirSesion],
  )

  const logout = useCallback(() => {
    setSalioPorSuCuenta(true)
    cerrar(null)
  }, [cerrar])
  const descartarAviso = useCallback(() => setAviso(null), [])

  const tienePermiso = useCallback(
    (roles: readonly Rol[]) => usuario !== null && roles.includes(usuario.rol),
    [usuario],
  )

  return (
    <AuthContext.Provider
      value={{ usuario, cargando, aviso, descartarAviso, login, registro, logout, salioPorSuCuenta, tienePermiso }}
    >
      {children}
    </AuthContext.Provider>
  )
}
