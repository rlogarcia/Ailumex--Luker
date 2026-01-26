# Documentación Técnica - API REST Benglish Academy

Yo desarrolle el modulo Benglish Academy y documente este archivo para su operacion en produccion.


## Información General

**Versión de API:** v1  
**Base URL:** `{odoo_server_url}/api/v1`  
**Formato de respuesta:** JSON (default) o CSV  
**Autenticación:** API Key (Bearer Token o Query Parameter)  
**Fecha de documentación:** 2026-01-02

---

## Autenticación

### Métodos de Autenticación

#### 1. Bearer Token (Recomendado)

```http
GET /api/v1/sessions/published
Authorization: Bearer {api_key}
```

#### 2. Query Parameter

```http
GET /api/v1/sessions/published?api_key={api_key}
```

### Configuración de API Key

La API key debe configurarse en:

```
Menú: Configuración > Técnico > Parámetros del Sistema
Clave: benglish.api.key
Valor: {tu_clave_secreta}
```

### Modo Desarrollo vs Producción

| Parámetro                   | Desarrollo                      | Producción                        |
| --------------------------- | ------------------------------- | --------------------------------- |
| `benglish.api.allow_no_key` | `True` (permite acceso sin key) | `False` (require key obligatoria) |
| `benglish.api.key`          | Opcional                        | **Obligatorio**                   |

### Códigos de Error de Autenticación

| Código HTTP | Descripción                              |
| ----------- | ---------------------------------------- |
| 401         | API key inválida o faltante              |
| 403         | Acceso denegado (permisos insuficientes) |

---

## Endpoints Disponibles

### 1. GET /api/v1/sessions/published

Obtiene sesiones académicas publicadas con filtros opcionales.

#### Parámetros Query String

| Parámetro    | Tipo    | Requerido     | Descripción                          | Ejemplo                |
| ------------ | ------- | ------------- | ------------------------------------ | ---------------------- |
| `api_key`    | string  | Condicional\* | Clave de autenticación               | `vX9Kp3mN8qR5tY2wZ7aB` |
| `campus_id`  | integer | No            | Filtrar por ID de sede               | `1`                    |
| `subject_id` | integer | No            | Filtrar por ID de asignatura         | `42`                   |
| `start_date` | date    | No            | Fecha inicio (YYYY-MM-DD)            | `2026-01-01`           |
| `end_date`   | date    | No            | Fecha fin (YYYY-MM-DD)               | `2026-01-31`           |
| `format`     | string  | No            | Formato de respuesta: `json` o `csv` | `json`                 |

\*Si no se usa Bearer Token en headers.

#### Ejemplo de Request (JSON)

```bash
curl -X GET "https://odoo.benglish.com/api/v1/sessions/published?start_date=2026-01-01&end_date=2026-01-31&campus_id=1&format=json" \
  -H "Authorization: Bearer vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL"
```

#### Ejemplo de Response (JSON)

```json
{
  "status": "success",
  "count": 15,
  "timestamp": "2026-01-02T14:30:00",
  "sessions": [
    {
      "id": 123,
      "name": "UNIT 01 - Class 1 - Grammar Focus",
      "subject": {
        "id": 42,
        "name": "UNIT 01 - Grammar & Vocabulary"
      },
      "campus": {
        "id": 1,
        "name": "Sede Centro",
        "code": "CTR"
      },
      "subcampus": {
        "id": 5,
        "name": "Aula 201"
      },
      "teacher": {
        "id": 8,
        "name": "John Smith"
      },
      "coach": {
        "id": 3,
        "name": "Maria Garcia"
      },
      "schedule": {
        "start_datetime": "2026-01-15T09:00:00",
        "end_datetime": "2026-01-15T10:30:00",
        "duration_hours": 1.5
      },
      "delivery": {
        "mode": "virtual",
        "meeting_link": "https://meet.google.com/abc-defg-hij",
        "meeting_platform": "google_meet"
      },
      "session_type": "regular",
      "state": "confirmed",
      "published_at": "2026-01-10T08:00:00"
    }
  ]
}
```

#### Ejemplo de Request (CSV)

```bash
curl -X GET "https://odoo.benglish.com/api/v1/sessions/published?format=csv" \
  -H "Authorization: Bearer vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL" \
  -o sessions.csv
```

#### Ejemplo de Response (CSV)

```csv
ID,Nombre,Asignatura,Sede,Aula,Docente,Inicio,Fin,Duración (hrs),Modalidad,Enlace,Estado,Publicado
123,UNIT 01 - Class 1,UNIT 01 - Grammar,Sede Centro,Aula 201,John Smith,2026-01-15 09:00,2026-01-15 10:30,1.5,virtual,https://meet.google.com/abc-defg-hij,confirmed,2026-01-10 08:00
124,UNIT 02 - Class 1,UNIT 02 - Reading,Sede Norte,Aula 305,Mary Johnson,2026-01-16 14:00,2026-01-16 15:30,1.5,presential,,confirmed,2026-01-10 08:00
```

---

### 2. GET /api/v1/sessions/stats

Obtiene estadísticas agregadas de sesiones publicadas.

#### Parámetros Query String

| Parámetro   | Tipo    | Requerido     | Descripción            | Ejemplo                |
| ----------- | ------- | ------------- | ---------------------- | ---------------------- |
| `api_key`   | string  | Condicional\* | Clave de autenticación | `vX9Kp3mN8qR5tY2wZ7aB` |
| `campus_id` | integer | No            | Filtrar por ID de sede | `1`                    |

#### Ejemplo de Request

```bash
curl -X GET "https://odoo.benglish.com/api/v1/sessions/stats?campus_id=1" \
  -H "Authorization: Bearer vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL"
```

#### Ejemplo de Response

```json
{
  "status": "success",
  "timestamp": "2026-01-02T14:35:00",
  "total_published": 250,
  "by_state": {
    "planned": 180,
    "in_progress": 5,
    "done": 65
  },
  "by_mode": {
    "presential": 100,
    "virtual": 120,
    "hybrid": 30
  }
}
```

---

## Payloads y Esquemas de Datos

### Esquema: Session (JSON)

```json
{
  "id": "integer - ID único de la sesión",
  "name": "string - Nombre descriptivo de la sesión",
  "subject": {
    "id": "integer - ID de la asignatura",
    "name": "string - Nombre de la asignatura"
  },
  "campus": {
    "id": "integer - ID de la sede",
    "name": "string - Nombre de la sede",
    "code": "string - Código de la sede"
  },
  "subcampus": {
    "id": "integer - ID del aula/subcampus",
    "name": "string - Nombre del aula"
  },
  "teacher": {
    "id": "integer - ID del docente",
    "name": "string - Nombre del docente"
  },
  "coach": {
    "id": "integer - ID del coach",
    "name": "string - Nombre del coach"
  },
  "schedule": {
    "start_datetime": "ISO8601 datetime - Inicio de la sesión",
    "end_datetime": "ISO8601 datetime - Fin de la sesión",
    "duration_hours": "float - Duración en horas"
  },
  "delivery": {
    "mode": "string - Modalidad: presential|virtual|hybrid",
    "meeting_link": "string|null - URL de videoconferencia",
    "meeting_platform": "string - Plataforma: google_meet|zoom|teams|jitsi|other"
  },
  "session_type": "string - Tipo de sesión: regular|makeup|review",
  "state": "string - Estado: draft|confirmed|in_progress|done|cancelled",
  "published_at": "ISO8601 datetime - Fecha de publicación"
}
```

---

## Estados del Sistema

### Estados de Sesión Académica (`state`)

| Estado     | Valor         | Descripción                   | Publicable                        |
| ---------- | ------------- | ----------------------------- | --------------------------------- |
| Borrador   | `draft`       | Sesión en proceso de creación | No                                |
| Confirmada | `confirmed`   | Sesión confirmada y lista     | Sí                                |
| En curso   | `in_progress` | Clase en desarrollo           | Sí                                |
| Completada | `done`        | Clase finalizada exitosamente | Sí                                |
| Cancelada  | `cancelled`   | Sesión cancelada              | **No** (excluida automáticamente) |

**Filtro de API:**

```python
domain = [
    ('is_published', '=', True),
    ('state', '!=', 'cancelled')
]
```

### Modalidades de Entrega (`delivery_mode`)

| Valor        | Descripción                          | Requiere `meeting_link` |
| ------------ | ------------------------------------ | ----------------------- |
| `presential` | Clase presencial                     | No                      |
| `virtual`    | Clase 100% virtual                   | Sí                      |
| `hybrid`     | Clase híbrida (presencial + virtual) | Sí                      |

### Plataformas de Videoconferencia (`meeting_platform`)

| Valor         | Nombre          |
| ------------- | --------------- |
| `google_meet` | Google Meet     |
| `zoom`        | Zoom            |
| `teams`       | Microsoft Teams |
| `jitsi`       | Jitsi Meet      |
| `other`       | Otra Plataforma |

### Tipos de Sesión (`session_type`)

| Valor     | Descripción                  |
| --------- | ---------------------------- |
| `regular` | Clase regular del calendario |
| `makeup`  | Clase de recuperación        |
| `review`  | Sesión de repaso             |

---

## Rate Limits (Propuesto)

### Límites por Endpoint

| Endpoint                     | Límite por IP | Ventana Temporal |
| ---------------------------- | ------------- | ---------------- |
| `/api/v1/sessions/published` | 100 requests  | 1 hora           |
| `/api/v1/sessions/stats`     | 50 requests   | 1 hora           |
| **Total general**            | 1000 requests | 1 día            |

### Respuesta al exceder límites

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please try again later.",
  "retry_after": 3600
}
```

**HTTP Status:** `429 Too Many Requests`

**Header de respuesta:**

```
Retry-After: 3600
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1735836000
```

### Implementación Futura

- Usar módulo `web_rate_limit` de OCA
- Implementar middleware personalizado con Redis/Memcached
- Configurar límites por API key (usuarios premium vs free)

---

## Códigos de Respuesta HTTP

### Respuestas Exitosas

| Código         | Descripción                     | Uso                            |
| -------------- | ------------------------------- | ------------------------------ |
| 200 OK         | Solicitud exitosa               | GET de sesiones o estadísticas |
| 204 No Content | Operación exitosa sin contenido | Futuras operaciones DELETE     |

### Respuestas de Error del Cliente

| Código                | Descripción             | Causa común                 |
| --------------------- | ----------------------- | --------------------------- |
| 400 Bad Request       | Parámetros inválidos    | Formato de fecha incorrecto |
| 401 Unauthorized      | Autenticación fallida   | API key inválida o faltante |
| 403 Forbidden         | Acceso denegado         | Permisos insuficientes      |
| 404 Not Found         | Recurso no encontrado   | Endpoint inexistente        |
| 429 Too Many Requests | Límite de tasa excedido | Demasiadas peticiones       |

### Respuestas de Error del Servidor

| Código                    | Descripción                          | Acción                    |
| ------------------------- | ------------------------------------ | ------------------------- |
| 500 Internal Server Error | Error interno del servidor           | Contactar soporte técnico |
| 503 Service Unavailable   | Servicio temporalmente no disponible | Reintentar más tarde      |

---

## Formato de Errores

### Estructura de Error JSON

```json
{
  "error": "string - Tipo de error",
  "message": "string - Descripción detallada del error",
  "timestamp": "ISO8601 datetime - Momento del error",
  "path": "string - Endpoint que generó el error"
}
```

### Ejemplos de Respuestas de Error

#### Error 401: API Key Inválida

```json
{
  "error": "Invalid or missing API key"
}
```

#### Error 400: Parámetros Inválidos

```json
{
  "error": "Bad Request",
  "message": "Invalid date format. Expected YYYY-MM-DD, got '2026/01/01'",
  "timestamp": "2026-01-02T14:40:00",
  "path": "/api/v1/sessions/published"
}
```

---

## Ejemplos de Integración

### Python (requests)

```python
import requests
from datetime import datetime, timedelta

API_BASE_URL = "https://odoo.benglish.com/api/v1"
API_KEY = "vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

# Obtener sesiones del próximo mes
start_date = datetime.now().strftime("%Y-%m-%d")
end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

params = {
    "start_date": start_date,
    "end_date": end_date,
    "campus_id": 1,
    "format": "json"
}

response = requests.get(
    f"{API_BASE_URL}/sessions/published",
    headers=headers,
    params=params
)

if response.status_code == 200:
    data = response.json()
    print(f"Total sesiones: {data['count']}")
    for session in data['sessions']:
        print(f"- {session['name']} el {session['schedule']['start_datetime']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

### JavaScript (fetch)

```javascript
const API_BASE_URL = "https://odoo.benglish.com/api/v1";
const API_KEY = "vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL";

async function getPublishedSessions(campusId, startDate, endDate) {
  const params = new URLSearchParams({
    campus_id: campusId,
    start_date: startDate,
    end_date: endDate,
    format: "json",
  });

  try {
    const response = await fetch(
      `${API_BASE_URL}/sessions/published?${params}`,
      {
        headers: {
          Authorization: `Bearer ${API_KEY}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    const data = await response.json();
    console.log(`Total sesiones: ${data.count}`);
    return data.sessions;
  } catch (error) {
    console.error("Error fetching sessions:", error);
    return [];
  }
}

// Uso
getPublishedSessions(1, "2026-01-01", "2026-01-31").then((sessions) => {
  sessions.forEach((session) => {
    console.log(`${session.name} - ${session.schedule.start_datetime}`);
  });
});
```

### cURL

```bash
#!/bin/bash

API_BASE_URL="https://odoo.benglish.com/api/v1"
API_KEY="vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL"

# Obtener sesiones en JSON
curl -X GET "${API_BASE_URL}/sessions/published?start_date=2026-01-01&end_date=2026-01-31&campus_id=1&format=json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Accept: application/json"

# Descargar sesiones en CSV
curl -X GET "${API_BASE_URL}/sessions/published?format=csv" \
  -H "Authorization: Bearer ${API_KEY}" \
  -o sessions_export.csv

# Obtener estadísticas
curl -X GET "${API_BASE_URL}/sessions/stats?campus_id=1" \
  -H "Authorization: Bearer ${API_KEY}"
```

---

## Mejores Prácticas

### 1. Seguridad

- ✅ **USAR HTTPS** en producción (nunca HTTP)
- ✅ Almacenar API key en variables de entorno, no en código
- ✅ Rotar API keys periódicamente (cada 90 días)
- ✅ Usar Bearer Token en headers (no en query params cuando sea posible)
- ✅ Implementar logging de accesos para auditoría

### 2. Rendimiento

- ✅ Cachear respuestas cuando sea apropiado (TTL: 5-15 minutos)
- ✅ Usar filtros de fecha para limitar resultados
- ✅ Preferir formato JSON para procesamiento, CSV para reportes
- ✅ Implementar paginación en futuras versiones (limit/offset)

### 3. Manejo de Errores

- ✅ Validar códigos de respuesta HTTP antes de procesar
- ✅ Implementar reintentos con backoff exponencial para errores 5xx
- ✅ Registrar errores para debugging
- ✅ No reintentar errores 4xx (son permanentes)

### 4. Monitoreo

- ✅ Monitorear tiempos de respuesta (SLA: < 2 segundos)
- ✅ Alertas para tasas de error > 5%
- ✅ Rastrear uso de API por endpoint
- ✅ Monitorear uso cercano a rate limits

---

## Changelog de API

### v1.0.0 (2026-01-02)

- ✅ Endpoint inicial: `GET /api/v1/sessions/published`
- ✅ Endpoint de estadísticas: `GET /api/v1/sessions/stats`
- ✅ Soporte para autenticación con API key
- ✅ Formatos de respuesta: JSON y CSV
- ✅ Filtros por campus, asignatura y rango de fechas

### Próximas versiones (Roadmap)

- [ ] Paginación en endpoints de listado (limit/offset)
- [ ] Webhooks para notificaciones push de cambios
- [ ] Endpoint para crear/actualizar sesiones (POST/PUT)
- [ ] Endpoint para cancelar sesiones (DELETE)
- [ ] Filtros adicionales (por docente, modalidad, tipo)
- [ ] Versionado de API (v2)
- [ ] GraphQL como alternativa a REST
- [ ] Rate limiting con Redis
- [ ] OAuth 2.0 para autenticación avanzada

---

## Soporte y Contacto

**Equipo Técnico:** Ailumex Development Team  
**Email:** dev@ailumex.com  
**Documentación:** https://docs.benglish.com/api  
**Repositorio:** Ailumex--Be (GitHub)

**SLA de Soporte:**

- Respuesta inicial: 24 horas
- Resolución de bugs críticos: 48 horas
- Mejoras y features: Según sprint planning

---

**Última actualización:** 2026-01-02  
**Versión del documento:** 1.0.0  
**Autor:** Sistema Benglish Academy API
