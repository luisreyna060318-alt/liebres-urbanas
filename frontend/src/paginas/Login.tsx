import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import Alerta from '../componentes/Alerta.tsx'
import Boton from '../componentes/Boton.tsx'
import Campo from '../componentes/Campo.tsx'
import { useAuth } from '../context/AuthContexto.ts'
import { useTitulo } from '../hooks/useTitulo.ts'
import { validarCorreo, validarPasswordLogin } from '../utils/validaciones.ts'

interface Errores {
  correo?: string
  password?: string
}

// Estado que otras pantallas mandan al navegar a /login
interface EstadoNavegacion {
  desde?: string // la ruta privada a la que se quería entrar
}

export default function Login() {
  useTitulo('Iniciar sesión')
  const { usuario, login } = useAuth()
  const estado = useLocation().state as EstadoNavegacion | null

  const [correo, setCorreo] = useState('')
  const [password, setPassword] = useState('')
  const [errores, setErrores] = useState<Errores>({})
  const [errorServidor, setErrorServidor] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Con sesión iniciada se vuelve a donde se quería entrar (o al inicio)
  if (usuario) return <Navigate to={estado?.desde ?? '/'} replace />

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault() // evita que el navegador recargue la página
    setErrorServidor('')

    // 1) Validar en el cliente, con el mensaje junto a cada campo
    const nuevos: Errores = {
      correo: validarCorreo(correo) || undefined,
      password: validarPasswordLogin(password) || undefined,
    }
    setErrores(nuevos)
    if (nuevos.correo || nuevos.password) {
      // El foco va al primer campo con error (también ayuda a quien usa lector de pantalla)
      document.getElementById(nuevos.correo ? 'correo' : 'password')?.focus()
      return
    }

    // 2) Mandar los datos a la API. Si sale bien, AuthProvider guarda al usuario y esta pantalla redirige.
    setEnviando(true)
    try {
      await login(correo.trim(), password)
    } catch (e) {
      // El mensaje viene del servidor: es el mismo si falla el correo o la contraseña (CREDENCIALES),
      // y explica el motivo si la cuenta está suspendida (CUENTA_SUSPENDIDA)
      setErrorServidor(e instanceof Error ? e.message : 'No se pudo iniciar sesión.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section>
      <h1>Iniciar sesión</h1>

      {estado?.desde && (
        <Alerta tipo="info">Inicia sesión para continuar con lo que estabas haciendo.</Alerta>
      )}

      {/* noValidate: los mensajes los muestra nuestra validación, no el navegador */}
      <form className="formulario" onSubmit={enviar} noValidate>
        <Campo
          id="correo"
          etiqueta="Correo electrónico"
          tipo="email"
          autoComplete="email"
          valor={correo}
          onCambio={setCorreo}
          error={errores.correo}
        />
        <Campo
          id="password"
          etiqueta="Contraseña"
          tipo="password"
          autoComplete="current-password"
          valor={password}
          onCambio={setPassword}
          error={errores.password}
        />

        {errorServidor && <Alerta tipo="error">{errorServidor}</Alerta>}

        <Boton type="submit" cargando={enviando} textoCargando="Entrando…">
          Entrar
        </Boton>
      </form>

      <p className="enlace-aparte">
        ¿No tienes cuenta? <Link to="/registro">Crear cuenta</Link>
      </p>
    </section>
  )
}
