import { Link } from 'react-router-dom'
import Alerta from '../componentes/Alerta.tsx'
import { useTitulo } from '../hooks/useTitulo.ts'

// Aviso de privacidad integral, conforme a la Ley Federal de Protección de Datos Personales en Posesión de los Particulares.
// "Calles Seguras Juárez" es una asociación ficticia: el contacto de ejemplo no recibe solicitudes reales.
const CORREO_PRIVACIDAD = 'privacidad@callesseguras.example'

export default function Privacidad() {
  useTitulo('Aviso de privacidad')

  return (
    <article className="texto-largo">
      <h1>Aviso de privacidad</h1>
      <p>Última actualización: 24 de noviembre de 2026.</p>

      <Alerta tipo="aviso">
        La asociación civil “Calles Seguras Juárez” es <strong>ficticia</strong> y esta plataforma es un proyecto académico de
        la materia de Programación Web del Instituto Tecnológico de Ciudad Juárez. El correo de contacto de este aviso es de
        ejemplo y no atiende solicitudes reales.
      </Alerta>

      <section aria-labelledby="priv-responsable">
        <h2 id="priv-responsable">1. Quién es responsable de tus datos</h2>
        <p>
          La asociación civil “Calles Seguras Juárez”, de Ciudad Juárez, Chihuahua, es la responsable de guardar y proteger tus
          datos personales, de acuerdo con la Ley Federal de Protección de Datos Personales en Posesión de los Particulares.
        </p>
      </section>

      <section aria-labelledby="priv-datos">
        <h2 id="priv-datos">2. Qué datos guardamos</h2>
        <ul>
          <li>
            <strong>Nombre y correo electrónico</strong>, que nos das al crear tu cuenta.
          </li>
          <li>
            <strong>Tu contraseña</strong>, que se guarda cifrada: ni el equipo de la plataforma puede leerla.
          </li>
          <li>
            <strong>Tus reportes</strong>: la ubicación del bache o encharcamiento, su descripción y la fecha y hora en que los
            hiciste.
          </li>
          <li>La fecha en que aceptaste este aviso y el rol de tu cuenta (ciudadano, moderador o coordinador).</li>
        </ul>
        <p>
          No pedimos datos personales sensibles (como salud, creencias o datos financieros), ni teléfono, ni fotografías de
          personas. Si usas la ubicación de tu dispositivo para ubicar un reporte, solo se toma en ese momento; no guardamos tus
          recorridos.
        </p>
      </section>

      <section aria-labelledby="priv-finalidad">
        <h2 id="priv-finalidad">3. Para qué los usamos</h2>
        <ul>
          <li>Crear y mantener tu cuenta, y comprobar que eres tú cuando inicias sesión.</li>
          <li>Permitirte reportar baches y encharcamientos, y que veas y corrijas tus reportes.</li>
          <li>Que las personas voluntarias que moderan puedan revisar los reportes y el equipo coordinador administre las cuentas.</li>
        </ul>
        <p>No usamos tus datos para publicidad ni los vendemos.</p>
      </section>

      <section aria-labelledby="priv-publicos">
        <h2 id="priv-publicos">4. Qué no se publica</h2>
        <p>
          Tu nombre y tu correo <strong>no se publican</strong>. Las consultas públicas de reportes, el detalle de cada reporte,
          las cifras y las exportaciones para la autoridad no muestran quién hizo cada reporte. Solo el equipo coordinador ve la
          lista de cuentas (nombre, correo y rol) para poder administrarlas.
        </p>
      </section>

      <section aria-labelledby="priv-terceros">
        <h2 id="priv-terceros">5. Con quién se comparten</h2>
        <p>
          No compartimos tus datos con otras personas u organizaciones. Para funcionar usamos servicios técnicos: el hospedaje de
          la plataforma y de la base de datos (Vercel, Render y Neon) guarda la información por nosotros, y los servicios de
          mapas y de clima (OpenStreetMap y Open-Meteo) reciben únicamente la dirección o las coordenadas que consultas, nunca tu
          nombre ni tu correo.
        </p>
      </section>

      <section aria-labelledby="priv-arco">
        <h2 id="priv-arco">6. Tus derechos ARCO y cómo ejercerlos</h2>
        <p>Tienes derecho a:</p>
        <ul>
          <li>
            <strong>Acceso</strong>: saber qué datos tuyos tenemos y cómo los usamos.
          </li>
          <li>
            <strong>Rectificación</strong>: corregir tus datos si están mal o incompletos.
          </li>
          <li>
            <strong>Cancelación</strong>: pedir que borremos tus datos cuando ya no sean necesarios.
          </li>
          <li>
            <strong>Oposición</strong>: pedir que dejemos de usar tus datos para un fin determinado.
          </li>
        </ul>
        <p>
          También puedes retirar tu consentimiento en cualquier momento. Para ejercer cualquiera de estos derechos, escribe a{' '}
          <a href={`mailto:${CORREO_PRIVACIDAD}`}>{CORREO_PRIVACIDAD}</a> con tu nombre, el correo de tu cuenta, el derecho que
          quieres ejercer y una descripción breve de tu solicitud. Te responderemos en un máximo de 20 días hábiles. Si no
          estás conforme con la respuesta, puedes acudir ante la autoridad de protección de datos personales que señala la ley.
        </p>
      </section>

      <section aria-labelledby="priv-conservacion">
        <h2 id="priv-conservacion">7. Cuánto tiempo los conservamos</h2>
        <p>Guardamos tus datos mientras tu cuenta exista. Si pides cancelarla, dejamos de usar tus datos personales.</p>
      </section>

      <section aria-labelledby="priv-cambios">
        <h2 id="priv-cambios">8. Cambios a este aviso</h2>
        <p>Si este aviso cambia, publicaremos la nueva versión en esta misma página, con su fecha de actualización.</p>
      </section>

      <p>
        <Link to="/">Volver al inicio</Link>
      </p>
    </article>
  )
}
