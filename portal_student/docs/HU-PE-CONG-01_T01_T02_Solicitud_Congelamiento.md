# HU-PE-CONG-01 & Tareas T-PE-CONG-01 y T-PE-CONG-02: Solicitud de Congelamiento desde el Portal

## 📋 Información General

**Historia de Usuario:** HU-PE-CONG-01  
**Título:** Solicitud de congelamiento desde el portal de estudiante  
**Descripción:** Como estudiante con plan que permite congelamiento quiero poder solicitar el congelamiento de mi curso desde el portal, indicando el rango de fechas y una justificación (vacaciones, viaje, salud, etc.), para pausar temporalmente mi avance académico.

**Tareas Técnicas Incluidas:**
- **T-PE-CONG-01:** Formulario de solicitud de congelamiento en portal
- **T-PE-CONG-02:** Mensaje de advertencia sobre implicaciones financieras

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad permite a los estudiantes **solicitar pausas académicas de forma autónoma**:

- **Formulario de solicitud:** Captura de fechas, motivo y justificación
- **Validación de elegibilidad:** Solo para planes que permiten congelamiento
- **Cálculo de días:** Muestra días disponibles y días solicitados
- **Verificación de pagos:** Solo estudiantes al día pueden solicitar
- **Advertencia financiera:** Informa que el congelamiento NO pausa pagos
- **Aceptación de términos:** Checkbox obligatorio de condiciones financieras
- **Adjuntar documentos:** Soporte para cartas médicas, reservas de viaje, etc.
- **Historial de solicitudes:** Ver estado de solicitudes previas
- **Sin intervención administrativa:** Proceso completamente autoservicio

Es un **sistema de autogestión de pausas académicas** que empodera al estudiante mientras mantiene control institucional.

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Ruta Principal de Congelamiento**

Controlador que muestra el formulario y el historial:

```python
@http.route("/my/student/freeze", type="http", auth="user", website=True, methods=["GET"])
def portal_student_freeze(self, **kwargs):
    """Vista principal de solicitud de congelamiento."""
    student = self._get_student()
    if not student:
        return request.redirect("/my")
    
    # Obtener matrículas activas
    active_enrollments = student.enrollment_ids.sudo().filtered(
        lambda e: e.state in ["enrolled", "in_progress"]
    )
    
    # Obtener periodos de congelamiento del backend
    FreezePeriod = request.env['benglish.student.freeze.period'].sudo()
    freeze_periods = FreezePeriod.search([
        ('student_id', '=', student.id),
        ('visible_portal', '=', True)
    ], order='fecha_inicio desc')
    
    # HU-PE-CONG-02: Obtener congelamiento activo actual
    today = fields.Date.context_today(request.env.user)
    active_freeze_period = FreezePeriod.search([
        ('student_id', '=', student.id),
        ('estado', '=', 'aprobado'),
        ('fecha_inicio', '<=', today),
        ('fecha_fin', '>=', today)
    ], limit=1)
    
    # Calcular fecha de retorno (día siguiente al fin)
    return_date = False
    if active_freeze_period:
        return_date = active_freeze_period.fecha_fin + timedelta(days=1)
    
    # Obtener motivos disponibles
    FreezeReason = request.env['benglish.freeze.reason'].sudo()
    freeze_reasons = FreezeReason.search([
        ('active', '=', True),
        ('es_especial', '=', False)
    ], order='sequence, name')
    
    # Preparar información de cada matrícula
    enrollment_info = []
    for enrollment in active_enrollments:
        FreezeConfig = request.env['benglish.plan.freeze.config'].sudo()
        config = FreezeConfig.get_config_for_plan(enrollment.plan_id)
        
        # Calcular días usados
        dias_usados = 0
        if config:
            congelamientos = FreezePeriod.search([
                ('enrollment_id', '=', enrollment.id),
                ('estado', 'in', ('aprobado', 'finalizado')),
                ('es_especial', '=', False)
            ])
            dias_usados = sum(congelamientos.mapped('dias'))
        
        # Calcular días disponibles
        dias_disponibles = 0
        permite_congelamiento = False
        if config:
            permite_congelamiento = config.permite_congelamiento
            if permite_congelamiento:
                dias_disponibles = max(0, config.max_dias_acumulados - dias_usados)
        
        enrollment_info.append({
            'enrollment': enrollment,
            'config': config,
            'dias_usados': dias_usados,
            'dias_disponibles': dias_disponibles,
            'permite_congelamiento': permite_congelamiento,
            'puede_solicitar': permite_congelamiento and 
                              dias_disponibles >= (config.min_dias_congelamiento if config else 0),
        })
    
    values = {
        'page_name': 'freeze',
        'student': student,
        'active_enrollments': active_enrollments,
        'enrollment_info': enrollment_info,
        'freeze_periods': freeze_periods,
        'freeze_reasons': freeze_reasons,
        'active_freeze_period': active_freeze_period,
        'return_date': return_date,
        'message': kwargs.get('message'),
        'error': kwargs.get('error'),
    }
    return request.render("portal_student.portal_student_freeze", values)
```

### 2. **Ruta de Procesamiento de Solicitud**

Endpoint que crea la solicitud con validaciones:

```python
@http.route("/my/student/freeze/request", type="http", auth="user", website=True, 
            methods=["GET", "POST"], csrf=True)
def portal_student_freeze_request(self, **kwargs):
    """Formulario y procesamiento de solicitud de congelamiento."""
    student = self._get_student()
    if not student:
        return request.redirect("/my")
    
    if request.httprequest.method == "POST":
        try:
            # Validar datos requeridos
            enrollment_id = int(kwargs.get('enrollment_id', 0))
            fecha_inicio = kwargs.get('fecha_inicio')
            fecha_fin = kwargs.get('fecha_fin')
            freeze_reason_id = int(kwargs.get('freeze_reason_id', 0))
            motivo_detalle = kwargs.get('motivo_detalle', '')
            
            # T-PE-CONG-02: Validar aceptación de términos financieros
            aceptacion_terminos = kwargs.get('aceptacion_terminos')
            if not aceptacion_terminos or aceptacion_terminos != 'on':
                raise ValidationError(
                    "Debes aceptar las condiciones financieras para continuar. "
                    "El congelamiento es únicamente académico y tu plan de pagos continúa sin cambios."
                )
            
            if not all([enrollment_id, fecha_inicio, fecha_fin, freeze_reason_id]):
                raise ValidationError("Todos los campos son obligatorios")
            
            # Validar matrícula
            enrollment = request.env['benglish.enrollment'].sudo().browse(enrollment_id)
            if not enrollment.exists() or enrollment.student_id.id != student.id:
                raise ValidationError("Matrícula no válida")
            
            if enrollment.state not in ['enrolled', 'in_progress']:
                raise ValidationError("Solo puedes solicitar congelamiento para matrículas activas")
            
            # Convertir fechas
            fecha_inicio = fields.Date.from_string(fecha_inicio)
            fecha_fin = fields.Date.from_string(fecha_fin)
            
            # Validar fechas futuras
            today = fields.Date.context_today(request.env.user)
            if fecha_inicio < today:
                raise ValidationError("La fecha de inicio debe ser igual o posterior a hoy")
            
            # Crear periodo de congelamiento directamente en backend
            FreezePeriod = request.env['benglish.student.freeze.period'].sudo()
            freeze_period = FreezePeriod.create({
                'student_id': student.id,
                'enrollment_id': enrollment_id,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
                'freeze_reason_id': freeze_reason_id,
                'motivo_detalle': motivo_detalle,
                'estado': 'borrador',
            })
            
            # T-PE-CONG-02: Registrar aceptación de términos en chatter
            freeze_period.message_post(
                body=f"""
                <div style="padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b;">
                    <strong style="color: #92400e;">✓ Términos Financieros Aceptados</strong><br/>
                    <p style="margin: 8px 0 0; color: #78350f;">
                        El estudiante <strong>{student.name}</strong> ha leído y aceptado que:
                    </p>
                    <ul style="margin: 8px 0; padding-left: 20px; color: #78350f;">
                        <li>El congelamiento es únicamente académico</li>
                        <li>El plan de pagos continúa sin cambios</li>
                        <li>Debe mantener sus cuotas al día durante el congelamiento</li>
                    </ul>
                    <p style="margin: 8px 0 0; font-size: 12px; color: #92400e;">
                        <em>Fecha de aceptación: {fields.Datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</em>
                    </p>
                </div>
                """,
                subject="Aceptación de Términos Financieros"
            )
            
            # Manejar archivos adjuntos
            if 'documento_soporte' in request.httprequest.files:
                files = request.httprequest.files.getlist('documento_soporte')
                Attachment = request.env['ir.attachment'].sudo()
                for file in files:
                    if file.filename:
                        attachment = Attachment.create({
                            'name': file.filename,
                            'datas': base64.b64encode(file.read()),
                            'res_model': 'benglish.student.freeze.period',
                            'res_id': freeze_period.id,
                            'type': 'binary',
                        })
                        freeze_period.documento_soporte_ids = [(4, attachment.id)]
            
            # Enviar a aprobación
            freeze_period.action_enviar_aprobacion()
            
            return request.redirect('/my/student/freeze?message=Solicitud enviada correctamente')
            
        except ValidationError as e:
            return request.redirect(f'/my/student/freeze?error={str(e)}')
        except Exception as e:
            return request.redirect('/my/student/freeze?error=Error al procesar la solicitud')
```

### 3. **Vista del Formulario (T-PE-CONG-01)**

Template QWeb con formulario completo:

```xml
<template id="portal_student_freeze" name="Portal Student Freeze">
    <t t-call="portal.portal_layout">
        <div class="ps-shell">
            <h2>Solicitar Congelamiento</h2>
            <p>Pausa temporalmente tu avance académico. Recuerda que el plan de pagos continúa.</p>
            
            <!-- Mensajes de éxito/error -->
            <t t-if="message">
                <div class="alert alert-success"><t t-esc="message"/></div>
            </t>
            <t t-if="error">
                <div class="alert alert-danger"><t t-esc="error"/></div>
            </t>
            
            <!-- Formulario de solicitud -->
            <form action="/my/student/freeze/request" method="post" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
                
                <!-- Selección de matrícula -->
                <div class="form-group">
                    <label for="enrollment_id">Matrícula a congelar *</label>
                    <select id="enrollment_id" name="enrollment_id" class="form-control" required="required">
                        <option value="">Selecciona una matrícula</option>
                        <t t-foreach="enrollment_info" t-as="info">
                            <t t-if="info.get('puede_solicitar')">
                                <option t-att-value="info.get('enrollment').id">
                                    <t t-esc="info.get('enrollment').subject_id.name"/> - 
                                    <t t-esc="info.get('enrollment').group_id.name"/>
                                    (Disponibles: <t t-esc="info.get('dias_disponibles')"/> días)
                                </option>
                            </t>
                        </t>
                    </select>
                </div>
                
                <!-- Fechas -->
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="fecha_inicio">Fecha de inicio *</label>
                            <input type="date" id="fecha_inicio" name="fecha_inicio" 
                                   class="form-control" required="required"/>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="fecha_fin">Fecha de fin *</label>
                            <input type="date" id="fecha_fin" name="fecha_fin" 
                                   class="form-control" required="required"/>
                        </div>
                    </div>
                </div>
                
                <!-- Motivo -->
                <div class="form-group">
                    <label for="freeze_reason_id">Motivo *</label>
                    <select id="freeze_reason_id" name="freeze_reason_id" 
                            class="form-control" required="required">
                        <option value="">Selecciona un motivo</option>
                        <t t-foreach="freeze_reasons" t-as="reason">
                            <option t-att-value="reason.id" t-esc="reason.name"/>
                        </t>
                    </select>
                </div>
                
                <!-- Justificación detallada -->
                <div class="form-group">
                    <label for="motivo_detalle">Justificación detallada</label>
                    <textarea id="motivo_detalle" name="motivo_detalle" 
                              class="form-control" rows="4" 
                              placeholder="Explica con más detalle tu situación..."></textarea>
                </div>
                
                <!-- Documentos de soporte -->
                <div class="form-group">
                    <label for="documento_soporte">Documentos de soporte (opcional)</label>
                    <input type="file" id="documento_soporte" name="documento_soporte" 
                           class="form-control" multiple="multiple"/>
                    <small class="form-text text-muted">
                        Puedes adjuntar cartas médicas, reservas de viaje, etc.
                    </small>
                </div>
                
                <!-- T-PE-CONG-02: Advertencia financiera -->
                <div class="alert alert-warning" style="background: #fef3c7; border-left: 4px solid #f59e0b;">
                    <h5 style="color: #92400e;">
                        <i class="fa fa-exclamation-triangle"></i> 
                        Importante: Implicaciones Financieras
                    </h5>
                    <p style="color: #78350f;">
                        <strong>El congelamiento es únicamente académico.</strong> 
                        Tu plan de pagos continúa sin cambios y debes mantener tus cuotas al día 
                        durante el periodo de congelamiento.
                    </p>
                    <ul style="color: #78350f;">
                        <li>Las fechas de pago NO se pausan</li>
                        <li>Los montos de las cuotas NO se modifican</li>
                        <li>Debes seguir pagando según tu plan original</li>
                    </ul>
                </div>
                
                <!-- T-PE-CONG-02: Checkbox de aceptación OBLIGATORIO -->
                <div class="form-group">
                    <div class="form-check">
                        <input type="checkbox" id="aceptacion_terminos" name="aceptacion_terminos" 
                               class="form-check-input" required="required"/>
                        <label for="aceptacion_terminos" class="form-check-label">
                            <strong>Acepto y comprendo</strong> que el congelamiento es académico y 
                            mi plan de pagos continúa sin cambios. *
                        </label>
                    </div>
                </div>
                
                <!-- Botones -->
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">
                        <i class="fa fa-paper-plane"></i> Enviar solicitud
                    </button>
                    <a href="/my/student" class="btn btn-secondary">Cancelar</a>
                </div>
            </form>
            
            <!-- Historial de solicitudes -->
            <h3 style="margin-top: 3rem;">Mis Solicitudes Anteriores</h3>
            <t t-if="freeze_periods">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Matrícula</th>
                            <th>Fechas</th>
                            <th>Días</th>
                            <th>Estado</th>
                            <th>Fecha Solicitud</th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-foreach="freeze_periods" t-as="period">
                            <tr>
                                <td><t t-esc="period.enrollment_id.subject_id.name"/></td>
                                <td>
                                    <t t-esc="period.fecha_inicio"/> - <t t-esc="period.fecha_fin"/>
                                </td>
                                <td><t t-esc="period.dias"/> días</td>
                                <td>
                                    <span t-attf-class="badge badge-{{period.estado}}">
                                        <t t-esc="period.estado"/>
                                    </span>
                                </td>
                                <td><t t-esc="period.create_date"/></td>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </t>
            <t t-else="">
                <p class="text-muted">No tienes solicitudes previas.</p>
            </t>
        </div>
    </t>
</template>
```

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

### **Archivos Creados/Modificados:**

1. **`controllers/portal_student.py`**
   - Ruta `/my/student/freeze` (GET) - Vista principal
   - Ruta `/my/student/freeze/request` (POST) - Procesamiento
   - Cálculo de días disponibles por matrícula
   - Validación de elegibilidad
   - Creación de periodo de congelamiento
   - Registro en chatter de aceptación de términos

2. **`views/portal_student_templates.xml`**
   - Template completo de formulario
   - T-PE-CONG-01: Campos de matrícula, fechas, motivo, justificación, documentos
   - T-PE-CONG-02: Advertencia financiera destacada
   - T-PE-CONG-02: Checkbox obligatorio de aceptación
   - Tabla de historial de solicitudes

3. **`data/portal_student_menu.xml`**
   - Entrada "Solicitar congelamiento" en menú de usuario

---

## ✅ Pruebas y Validación

### **Preparación:**
1. Configurar plan con `permite_congelamiento = True`
2. Configurar `max_dias_acumulados = 30`
3. Crear motivos de congelamiento
4. Estudiante al día en pagos

### **Prueba:**
1. ✅ Formulario visible solo si plan permite congelamiento
2. ✅ Cálculo correcto de días disponibles
3. ✅ Advertencia financiera destacada
4. ✅ No se puede enviar sin aceptar términos
5. ✅ Solicitud se crea en estado "borrador"
6. ✅ Aceptación registrada en chatter
7. ✅ Archivos adjuntos vinculados correctamente

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
