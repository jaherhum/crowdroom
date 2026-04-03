# Modelos de Base de Datos — CrowdRoom TFG

Documentación de los modelos de la base de datos para el sistema de música colaborativa.

---

## 🎯 Arquitectura General

| Componente | Responsable de |
|------------|----------------|
| **RPi (Backend)** | Coordinar cola de música, usuarios, salas (sin internet) |
| **Móvil (Frontend)** | Acceder Spotify/Tidal/Deezer API y reproducir música (con 4G/5G) |

---

## 📋 Modelos

---

### 1️⃣ User (Usuario)

**Descripción:** Representa un usuario del sistema.

| Campo | Tipo | Requerido | Por qué |
|-------|------|-----------|----------|
| `id` | UUID | Sí | Identificador único no predecible, más seguro que int autoincremental |
| `username` | String (3-50 chars) | Sí | Nombre de usuario único para login y referencias |
| `email` | String (email) | Sí | Email único para recuperación de contraseña y notificaciones |
| `hashed_password` | String | Sí | Password hasheado (nunca en texto plano) por seguridad |
| `is_active` | Boolean | Sí | Permitir desactivar usuarios sin eliminarlos (soft disable) |
| `is_admin` | Boolean | Sí | Distinguir administradores del sistema |
| `created_at` | DateTime | Sí | Timestamp de creación para auditoría |
| `updated_at` | DateTime | Sí | Timestamp de última modificación para caché y sincronización |

**Relaciones:**
- `rooms[]` — Salas creadas por el usuario (uno a muchos)
- `queue_items[]` — Items de cola agregados por el usuario (uno a muchos)

---

### 2️⃣ Room (Sala)

**Descripción:** Representa una sala de música compartida.

| Campo | Tipo | Requerido | Por qué |
|-------|------|-----------|----------|
| `id` | UUID | Sí | Identificador único de la sala |
| `name` | String (2-100 chars) | Sí | Nombre visible de la sala (ej: "Viaje Madrid-Barcelona") |
| `description` | String (max 500) | No | Descripción opcional de la sala |
| `owner_id` | UUID (FK → User) | Sí | Propietario de la sala (puede eliminarla) |
| `max_users` | Integer (2-50) | Sí | Límite de usuarios concurrentes en la sala |
| `is_public` | Boolean | Sí | Sala pública (visible) o privada (solo con invite) |
| `password` | String | No | Password opcional para salas privadas |
| `current_song_id` | UUID (FK → Song) | No | Canción que se está reproduciendo actualmente |
| `created_at` | DateTime | Sí | Timestamp de creación |
| `updated_at` | DateTime | Sí | Timestamp de última modificación |

**Relaciones:**
- `owner` — Usuario propietario de la sala (muchos a uno)
- `queue_items[]` — Cola de canciones de la sala (uno a muchos)
- `current_song` — Canción actual en reproducción (muchos a uno)

---

### 3️⃣ Song (Canción)

**Descripción:** Representa una canción de un servicio de streaming.

| Campo | Tipo | Requerido | Por qué |
|-------|------|-----------|----------|
| `id` | UUID | Sí | Identificador único local de la canción |
| `title` | String (1-200 chars) | Sí | Título de la canción |
| `artist` | String (1-100 chars) | Sí | Artista o banda |
| `album` | String (max 150) | No | Álbum de origen (opcional) |
| `duration` | Integer (segundos) | Sí | Duración para cálculo de tiempo restante y autoplay |
| `service` | Enum (StreamingService) | Sí | Servicio de origen (Spotify, Tidal, Deezer, Apple Music) |
| `external_id` | String | Sí | ID externo en el servicio (ej: Spotify track ID) |
| `external_url` | String (URL) | Sí | URL directa para acceso desde el móvil |
| `created_at` | DateTime | Sí | Timestamp de creación |

**Enum: StreamingService**

| Valor | Descripción |
|-------|-------------|
| `spotify` | Spotify |
| `tidal` | Tidal |
| `deezer` | Deezer |
| `apple_music` | Apple Music |

**Relaciones:**
- `queue_items[]` — Items de cola que contienen esta canción (uno a muchos)

---

### 4️⃣ QueueItem (Item de Cola)

**Descripción:** Representa una canción en la cola de reproducción de una sala.

| Campo | Tipo | Requerido | Por qué |
|-------|------|-----------|----------|
| `id` | UUID | Sí | Identificador único del item |
| `song_id` | UUID (FK → Song) | Sí | Canción que se va a reproducir |
| `room_id` | UUID (FK → Room) | Sí | Sala donde está en cola |
| `user_id` | UUID (FK → User) | Sí | Usuario que agregó la canción (para atribución y skip) |
| `position` | Integer | Sí | Posición en la cola para ordenar reproducción |
| `status` | Enum (QueueStatus) | Sí | Estado del item (pending, playing, completed, etc.) |
| `created_at` | DateTime | Sí | Timestamp cuando se agregó a la cola |
| `updated_at` | DateTime | Sí | Timestamp de última modificación (cambio de status) |

**Enum: QueueStatus**

| Valor | Descripción |
|-------|-------------|
| `pending` | Esperando en cola |
| `playing` | Reproduciéndose actualmente |
| `completed` | Reproducción finalizada |
| `skipped` | Saltado por un usuario |
| `removed` | Eliminado manualmente |

**Relaciones:**
- `song` — Canción del item (muchos a uno)
- `room` — Sala del item (muchos a uno)
- `user` — Usuario que agregó el item (muchos a uno)

---

## 🔗 Diagrama de Relaciones

```
┌─────────────┐       ┌─────────────┐
│    User     │──┐    │    Room     │
│  (UUID)     │  │    │  (UUID)     │
│ - username  │  │    │ - name      │
│ - email     │  │    │ - owner_id──┘
│ - password  │  │    │ - is_public │
└─────────────┘  │    └─────────────┘
      │          │           │
      │          │           │
      │          │           │
      └──────────┼───────────┼───────┐
                 │           │       │
                 │           │       │
                 ▼           ▼       ▼
            ┌─────────────────────────────┐
            │        QueueItem             │
            │      (UUID)                  │
            │ - song_id ───────────────┐  │
            │ - room_id ───────────────┼──┤
            │ - user_id ───────────────┼──┤
            │ - position              │  │
            │ - status                │  │
            └─────────────────────────┼──┘
                                      │
                                      │
                                      ▼
                                ┌─────────────┐
                                │    Song     │
                                │   (UUID)    │
                                │ - title     │
                                │ - artist    │
                                │ - service   │
                                └─────────────┘
```

---

## 📊 Resumen de Entidades

| Modelo | Campos | Relaciones | Enums |
|--------|--------|------------|-------|
| **User** | 8 | 2 (rooms, queue_items) | — |
| **Room** | 10 | 3 (owner, queue_items, current_song) | — |
| **Song** | 9 | 1 (queue_items) | StreamingService |
| **QueueItem** | 8 | 3 (song, room, user) | QueueStatus |

**Total:** 35 campos, 9 relaciones, 2 enums

---

## 🔐 Consideraciones de Seguridad

1. **UUID en lugar de int:** IDs no predecibles, difícil adivinar `user_id=123`
2. **Password hasheado:** Nunca almacenar en texto plano
3. **Soft delete:** `is_active` en User permite desactivar sin perder datos
4. **Validaciones:** Longitudes máximas para prevenir ataques de buffer overflow

---

## 🚀 Escalabilidad

- **UUID:** Únicos globalmente, facilita futura distribución en múltiples BD
- **Timestamps:** Permiten caché con ETags y sincronización optimista
- **Enums:** Flexibles para añadir nuevos servicios/streaming sin migraciones mayores

---

*Última actualización: 2026-04-02* 
