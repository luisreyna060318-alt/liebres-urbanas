import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { ErrorApi } from '../api/cliente.ts'
import Alerta from '../componentes/Alerta.tsx'
import Boton from '../componentes/Boton.tsx'
import Campo from '../componentes/Campo.tsx'
import CampoCasilla from '../componentes/CampoCasilla.tsx'
import { useAuth } from '../context/AuthContexto.ts'
import { useReglas } from '../hooks/useReglas.ts'
import { useTitulo } from '../hooks/useTitulo.ts'
import { validarAceptaPrivacidad, validarCorreo, validarNombre, validarPassword } from '../utils/validaciones.ts'

// Los nombres coinciden con los campos de la entrada del servidor (así se pueden mostrar sus `campos` tal cual)
type Campos = 'nombre' | 'correo' | 'password' | 'acepta_privacidad'
type Errores = Partial<Record<Campos, string>>

// Orden en que aparecen en pantalla: el foco va al primero que tenga error
const ORDEN: Campos[] = ['nombre', 'correo', 'password', 'acepta_privacidad']

export default function Registro() {
  useTitulo('Crear cuenta')
  const { usuario, registro } = useAuth()
  const { password_min } = useReglas() // el mínimo de la contraseña lo manda el servidor

  const [nombre, setNombre] = useState('')
  const [correo, setCorreo] = useState('')
  const [password, setPassword] = useState('')
  const [acepta, setAcepta] = useState(false)
  const [errores, setErrores] = useState<Errores>({})
  const [errorServidor, setErrorServidor] = useState('')
  const [enviando, setEnviando] = useState(false)

  // Quien ya tiene sesión (también justo después de crear la cuenta, que deja a la persona dentro) va al inicio
  if (usuario) return <Navigate to="/" replace />

  function mostrarErrores(nuevos: Errores) {
    setErrores(nuevos)
    const primero = ORDEN.find((campo) => nuevos[campo])
    if (primero) document.getElementById(primero)?.focus()
  }

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    setErrorServidor('')

    // 1) Validar en el cliente con las mismas reglas del servidor.
    //    Lo capturado no se borra aunque haya errores (HU-01.1 CA3): los valores viven en el estado.
    const nuevos: Errores = {
      nombre: validarNombre(nombre) || undefined,
      correo: validarCorreo(correo) || undefined,
      password: validarPassword(password, password_min) || undefined,
      acepta_privacidad: validarAceptaPrivacidad(acepta) || undefined,
    }
    if (ORDEN.some((campo) => nuevos[campo])) {
      mostrarErrores(nuevos)
      return
    }
    setErrores({})

    // 2) Mandar los datos a la API
    setEnviando(true)
    try {
      await registro({ nombre: nombre.trim(), correo: correo.trim(), password, acepta_privacidad: acepta })
      // Con la cuenta creada, AuthProvider ya guardó la sesión y esta pantalla redirige
    } catch (e) {
      if (!(e instanceof ErrorApi)) {
        setErrorServidor('No se pudo crear la cuenta. Inténtalo de nuevo.')
        return
      }
      // Mensajes del servidor junto a su campo: los de `campos` (422) y el de correo repetido (409)
      const delServidor: Errores = {}
      for (const campo of ORDEN) {
        if (e.campos[campo]) delServidor[campo] = e.campos[campo]
      }
      if (e.codigo === 'CORREO_REGISTRADO') delServidor.correo = e.detail
      if (ORDEN.some((campo) => delServidor[campo])) {
        mostrarErrores(delServidor)
      } else {
        setErrorServidor(e.detail) // cualquier otro error (sin conexión, límite, etc.) va arriba del botón
      }
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section>
      <h1>Crear cuenta</h1>
      <p>Con tu cuenta puedes reportar baches y encharcamientos y darles seguimiento.</p>

      {/* noValidate: los mensajes los muestra nuestra validación, no el navegador */}
      <form className="formulario" onSubmit={enviar} noValidate>
        <Campo
          id="nombre"
          etiqueta="Nombre"
          autoComplete="name"
          valor={nombre}
          onCambio={setNombre}
          error={errores.nombre}
          requerido
        />
        <Campo
          id="correo"
          etiqueta="Correo electrónico"
          tipo="email"
          autoComplete="email"
          valor={correo}
          onCambio={setCorreo}
          error={errores.correo}
          requerido
        />
        <Campo
          id="password"
          etiqueta="Contraseña"
          tipo="password"
          autoComplete="new-password"
          valor={password}
          onCambio={setPassword}
          ayuda={`Mínimo ${password_min} caracteres, con letras y números.`}
          error={errores.password}
          requerido
        />
        <CampoCasilla
          id="acepta_privacidad"
          etiqueta={
            <span>
              Acepto el{' '}
              <Link to="/privacidad" target="_blank" rel="noopener">
                aviso de privacidad<span className="solo-lectores"> (se abre en otra pestaña)</span>
              </Link>
              .
            </span>
          }
          marcada={acepta}
          onCambio={setAcepta}
          error={errores.acepta_privacidad}
        />

        {errorServidor && <Alerta tipo="error">{errorServidor}</Alerta>}

        <Boton type="submit" cargando={enviando} textoCargando="Creando cuenta…">
          Crear cuenta
        </Boton>
      </form>

      <p className="enlace-aparte">
        ¿Ya tienes cuenta? <Link to="/login">Iniciar sesión</Link>
      </p>
    </section>
  )
}
