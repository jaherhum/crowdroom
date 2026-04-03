---
tags: [tfg]
---

---
tags:
  - tfg
  - tfg/crowdroom
  - backend
  - fastapi
  - sqlmodel
  - websocket
  - docker
  - streaming
  - spotify
  - tidal
  - arquitectura
created: 2026-03-15
updated: 2026-04-03
---

## Concepto

Webapp de cola colaborativa donde el host pone música desde su plataforma de streaming y los guests pueden añadir canciones y votar para saltarlas. Funciona tanto en red local (coche, casa) como selfhosteado en servidor propio.

---

## Decisiones Arquitectónicas

### Primary Keys

**UUID** para todas las claves primarias.

- No secuencial $\rightarrow$ no enumerable
- Futuro-proof para distribuidos
- Tradeoff: más almacenamiento, joins ligeramente más lentos

### Password Hashing

**Argon2id** (vía `argon2-cffi`)

- Ganador Password Hashing Competition 2015
- Memory-hard $\rightarrow$ resistente a GPU/ASIC
- Variant "id" optimizada contra side-channel attacks
- Recomendado por OWASP, NIST, Cloudflare

### Password Policy

**NIST SP 800-63B-4**

- Mínimo **8 caracteres**, máximo **128+**
- Aceptar **cualquier Unicode** (sin forzar complejidad)
- ❌ Sin reglas de complejidad (no forzar mayúsculas/símbolos)
- ❌ Sin expiración periódica
- ✅ Memory check contra contraseñas comprometidas (HaveIBeenPwned API)
- Filosofía: passphrase de 12 caracteres > "Tr0ub4dor&3"

### Schema Layer (Pydantic)

Schemas separados por operación:

| Schema | Propósito | Campos |
|--------|-----------|--------|
| `UserCreate` | Registro | username, email, password |
| `UserUpdate` | Edición perfil | username?, email? (opcionales) |
| `UserLogin` | Autenticación | email/username, password |
| `UserResponse` | Respuestas API | id, username, email, is_admin, timestamps |
| `UserInDB` | Interno | + hashed_password |

**Motivo**: seguridad (nunca exponer password), flexibilidad, claridad

### Platform Storage

**Enum** (no tabla)

```python
class StreamingService(str, Enum):
    spotify = "spotify"
    deezer = "deezer"
    tidal = "tidal"
    ytmusic = "ytmusic"
    applemusic = "applemusic"
```

- Valores fijos $\rightarrow$ simpler, más rápido (sin JOINs)
- Migrar a tabla si en el futuro usuarios añaden plataformas

### Host Identification

**`Session.host_user_id`** (no `UserSession.is_host`)

- Host definido al crear sesión
- Ya necesitas Session object para operaciones
- Simplicidad = menos bugs

### Auth Layer Separation

```
Request $\rightarrow$ Pydantic Schema (valida formato/longitud)
        $\downarrow$
        Service Layer (rate limiting, logging, orchestration)
        $\downarrow$
        Model Method (verifica hash con Argon2)
```

---

## Modos de uso

- **Online** — desplegado en servidor, acceso por internet, Spotify/Deezer/Tidal funcionan completos
- **Offline/Local** — crea su propia red WiFi, los guests no necesitan internet, solo el host necesita conexión para el streaming

---

## Flujo de la aplicación

### Tipos de sesión

- **Personal** — sin salas, acceso por link directo
- **Compartida** — salas con PIN

### Host

- Crea la sesión y elige el tipo
- Conecta su cuenta de streaming (Spotify, Deezer, Tidal, YT Music, Apple Music)
- Controla la reproducción
- Puede hacer skip directo sin votos
- Puede votar como un usuario más
- Puede finalizar la sesión cuando quiera

### Guests

- Entran con link o PIN, sin necesidad de cuenta
- Eligen modo:
    - **Queue-only** — sólo añaden canciones y votan, sin cuenta de streaming
    - **Sync** — conectan su propia plataforma y escuchan sincronizado con el host
- Pueden añadir canciones a la cola
- Pueden votar skip

### Voteskip

- Se skipea al llegar al % configurado por el host (default 50%)
- Un usuario sólo puede votar una vez por canción
- El host puede saltarla directamente

### Cola

- Orden por timestamp de cuando se añadió
- Cuando una canción se reproduce, se elimina de la cola
- Los votos de skip se eliminan también al cambiar de canción

### Búsqueda de canciones

- Búsqueda neutral por metadatos (título + artista)
- La app resuelve el ID en cada plataforma conectada
- Sólo muestra resultados disponibles en todas las plataformas activas en la sesión
- Si una canción no está disponible en la plataforma de un guest en modo sync $\rightarrow$ aviso "canción no disponible en tu plataforma", sin sync para esa canción

### Fallback offline (ELIMINADO)
- *Nota: Se ha decidido eliminar el modo fallback para centrar el proyecto en la sincronización de plataformas de streaming y reducir la complejidad técnica.*

---

## Stack

- **Backend** — FastAPI + SQLModel
- **Base de datos** — SQLite (desarrollo) $\rightarrow$ PostgreSQL (producción)
- **WebSockets** — nativos de FastAPI
- **Auth** — JWT con blacklist en DB
- **Password hashing** — Argon2id (`argon2-cffi`)
- **Reverse proxy** — Caddy (ya configurado)
- **Contenedores** — Docker + docker-compose
- **Frontend** — JavaScript vanilla (mínimo, el proyecto es backend)

---

## Modelos de base de datos

*(Se mantienen los modelos SQL de la versión anterior)*

---

## Routers y Endpoints

*(Se mantienen los endpoints de la versión anterior)*

---

## Roadmap de Implementación (Estrategia de Arquitectura por Drivers)

Para asegurar la escalabilidad y cumplir con el TFG en junio, el desarrollo se ha reestructurado para priorizar una arquitectura de **Drivers/Adapters**.

### Fase 1: Core & Playback Engine (Hitos v0.4 - v0.8)
*Objetivo: Construir el cerebro del sistema antes de integrar servicios específicos.*
- [ ] Implementación de `PlaybackEngine` (Orquestador).
- [ ] Definición de `BasePlaybackDriver` (Interfaz abstracta).
- [ ] Implementación de `SpotifyDriver` (Primer servicio para la demo).
- [ ] Integración de `PlaybackEngine` con `RoomService` y `MusicService`.

### Fase 2: Conectividad y Tiempo Real (Hitos v0.7 - v0.8)
*Objetivo: Lograr que el control del host se propague a los clientes.*
- [ ] Implementación de WebSockets para eventos de reproducción (`play`, `pause`, `seek`, `skip`).
- [ ] Sincronización de timestamps mediante el Orquestador.

### Fase 3: Interfaz y Búsqueda (Hitos v0.6 - v1.0)
*Objetivo: Completar la experiencia de usuario.*
- [ ] Implementación de `SearchService` basado en Drivers (búsqueda agnóstica).
- [ ] Desarrollo de UI para gestión de cola y búsqueda.

### Fase 4: Escalabilidad (Hitos v0.9+)
*Objetivo: Demostrar la potencia de la arquitectura.*
- [ ] Implementación de `TidalDriver`.
- [ ] Implementación de `DeezerDriver`.
- [ ] Sincronización entre diferentes servicios (Sync mode).

---

## Pendiente

- [ ] Integración HaveIBeenPwned API para check de contraseñas
- [ ] Account lockout tras N intentos fallidos
- [ ] Email verification (future)
- [ ] 2FA (future)