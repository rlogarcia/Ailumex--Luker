# Configuración de Entorno Odoo para Webhooks

## Versión de Odoo

- **Versión instalada**: Odoo 18.0.20251128
- **Módulo compatible**: benglish_academy v18.0.1.4.0

## Configuración Requerida

### 1. Base URL

Configurar el parámetro del sistema para la URL base del servidor:

```
Menú: Configuración > Técnico > Parámetros > Parámetros del Sistema
```

| Clave          | Valor                                              | Descripción                |
| -------------- | -------------------------------------------------- | -------------------------- |
| `web.base.url` | `https://tu-dominio.com` o `http://localhost:8069` | URL base del servidor Odoo |

### 2. Configuración de Correo Saliente (SMTP)

```
Menú: Configuración > Técnico > Correo electrónico > Servidores de correo saliente
```

**Parámetros recomendados:**

| Campo                    | Valor                          |
| ------------------------ | ------------------------------ |
| Nombre                   | Servidor SMTP Principal        |
| Servidor SMTP            | smtp.gmail.com (o tu servidor) |
| Puerto                   | 587 (TLS) o 465 (SSL)          |
| Seguridad de la conexión | TLS (STARTTLS)                 |
| Usuario                  | tu-email@dominio.com           |
| Contraseña               | contraseña-app o contraseña    |

**Probar envío:**

1. Ir a Configuración > Técnico > Correo electrónico > Servidores de correo saliente
2. Seleccionar el servidor configurado
3. Clic en "Probar conexión"

### 3. Grupos y Usuarios para API

#### Grupos existentes en benglish_academy:

- `group_academic_manager` - Gestor académico (acceso completo)
- `group_academic_coordinator` - Coordinador académico
- `group_academic_assistant` - Asistente académico
- `group_academic_teacher` - Docente
- `group_academic_user` - Usuario académico (solo lectura)

#### Usuario API recomendado:

Crear un usuario técnico dedicado para consumo de API:

```
Menú: Configuración > Usuarios > Crear
```

| Campo          | Valor                             |
| -------------- | --------------------------------- |
| Nombre         | API User - Portal Sync            |
| Login          | api.portal@benglish.com           |
| Grupos         | Technical Settings, Academic User |
| Tipo de acceso | Portal o Usuario interno          |

### 4. Configuración de API Key

Configurar parámetros del sistema para seguridad de API:

```
Menú: Configuración > Técnico > Parámetros > Parámetros del Sistema
```

| Clave                       | Valor                       | Descripción                     |
| --------------------------- | --------------------------- | ------------------------------- |
| `benglish.api.allow_no_key` | `False`                     | En producción: requerir API key |
| `benglish.api.key`          | `tu_clave_secreta_generada` | API key para autenticación      |

**Generar API key segura:**

```python
import secrets
api_key = secrets.token_urlsafe(32)
# Ejemplo: 'vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL'
```

### 5. Endpoints de Webhooks Disponibles

#### GET /api/v1/sessions/published

Obtiene sesiones académicas publicadas.

**Headers:**

```
Authorization: Bearer tu_api_key_aqui
```

**Query Parameters:**

- `campus_id` (int, opcional): Filtrar por sede
- `start_date` (YYYY-MM-DD, opcional): Fecha inicio
- `end_date` (YYYY-MM-DD, opcional): Fecha fin
- `subject_id` (int, opcional): Filtrar por asignatura
- `format` (json|csv, opcional): Formato de respuesta (default: json)
- `api_key` (string, opcional): API key alternativa por query param

**Ejemplo de request:**

```bash
curl -X GET "https://tu-dominio.com/api/v1/sessions/published?start_date=2026-01-01&end_date=2026-01-31&format=json" \
  -H "Authorization: Bearer tu_api_key_aqui"
```

### 6. Rate Limits (Propuesto)

| Endpoint                       | Límite        | Ventana  |
| ------------------------------ | ------------- | -------- |
| GET /api/v1/sessions/published | 100 requests  | por hora |
| Todos los endpoints            | 1000 requests | por día  |

**Implementación futura:** Usar módulo `web_rate_limit` o middleware personalizado.

### 7. Estados de Sesiones

Estados válidos para sesiones publicadas (`benglish.academic.session`):

| Estado     | Valor         | Descripción                        |
| ---------- | ------------- | ---------------------------------- |
| Borrador   | `draft`       | Sesión no confirmada               |
| Confirmada | `confirmed`   | Sesión confirmada                  |
| En curso   | `in_progress` | Clase en desarrollo                |
| Completada | `done`        | Clase finalizada                   |
| Cancelada  | `cancelled`   | Sesión cancelada (excluida de API) |

**Filtro de publicación:**

- `is_published = True`
- `state != 'cancelled'`

### 8. Checklist de Configuración

- [ ] Verificar versión Odoo 18.0
- [ ] Configurar `web.base.url`
- [ ] Configurar servidor SMTP
- [ ] Probar envío de correo
- [ ] Crear usuario API
- [ ] Configurar API key en parámetros del sistema
- [ ] Deshabilitar `benglish.api.allow_no_key` en producción
- [ ] Probar endpoint `/api/v1/sessions/published`
- [ ] Configurar CORS si aplica
- [ ] Documentar API key para equipo de desarrollo frontend

### 9. Seguridad Adicional

#### CORS (si aplicable)

Para permitir requests desde dominios externos:

```python
# En odoo.conf o configuración del servidor web (nginx/apache)
# Agregar headers CORS apropiados
```

#### HTTPS Obligatorio

En producción, forzar HTTPS:

- Configurar certificado SSL/TLS
- Redirigir HTTP → HTTPS
- Usar `web.base.url` con https://

#### Logs y Auditoría

- Registrar accesos a API en logs de Odoo
- Monitorear requests sospechosos
- Implementar alertas para intentos de autenticación fallidos

---

**Fecha de configuración:** 2026-01-02  
**Responsable técnico:** Equipo Ailumex  
**Última actualización:** 2026-01-02
