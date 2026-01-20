# -*- coding: utf-8 -*-
"""
Periodos de Congelamiento de Estudiantes
========================================

Este modelo implementa:
- Registro de periodos de congelamiento y cálculo de días
- Ajuste automático de fecha fin de enrollment
- Validación de estado de cartera (al_dia_en_pagos)
- HU-GA-CONG-02: Congelamientos especiales (es_especial=True)

Flujo de estados:
- borrador: Solicitud creada, pendiente de revisión
- pendiente: Enviada para aprobación
- aprobado: Congelamiento activo, fechas ajustadas
- rechazado: Solicitud denegada con motivo
- cancelado: Solicitud cancelada por el estudiante o admin
- finalizado: Periodo de congelamiento completado
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
import logging

_logger = logging.getLogger(__name__)


class StudentFreezePeriod(models.Model):
    _name = "benglish.student.freeze.period"
    _description = "Periodo de Congelamiento de Estudiante"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "fecha_inicio desc, id desc"
    _rec_name = "display_name"

    # CONSTANTES

    SELECTION_ESTADO = [
        ("borrador", "Borrador"),
        ("pendiente", "Pendiente de Aprobación"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
        ("cancelado", "Cancelado"),
        ("finalizado", "Finalizado"),
    ]

    # CAMPOS RELACIONALES

    student_id = fields.Many2one(
        "benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
        help="Estudiante que solicita el congelamiento",
    )

    enrollment_id = fields.Many2one(
        "benglish.enrollment",
        string="Matrícula",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        domain="[('student_id', '=', student_id)]",
        help="Matrícula afectada por el congelamiento",
    )

    plan_id = fields.Many2one(
        related="enrollment_id.plan_id",
        string="Plan",
        store=True,
        help="Plan de la matrícula (para validaciones de política)",
    )

    freeze_config_id = fields.Many2one(
        "benglish.plan.freeze.config",
        string="Configuración de Congelamiento",
        compute="_compute_freeze_config",
        store=True,
        help="Configuración de política aplicable según el plan",
    )

    aprobado_por_id = fields.Many2one(
        "res.users",
        string="Aprobado Por",
        readonly=True,
        tracking=True,
        help="Usuario que aprobó el congelamiento",
    )

    rechazado_por_id = fields.Many2one(
        "res.users",
        string="Rechazado Por",
        readonly=True,
        help="Usuario que rechazó la solicitud",
    )

    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company
    )

    # CAMPOS DE FECHAS

    fecha_solicitud = fields.Date(
        string="Fecha de Solicitud",
        default=fields.Date.context_today,
        required=True,
        readonly=True,
        help="Fecha en que se creó la solicitud",
    )

    fecha_inicio = fields.Date(
        string="Fecha de Inicio",
        required=True,
        tracking=True,
        help="Fecha de inicio del periodo de congelamiento",
    )

    fecha_fin = fields.Date(
        string="Fecha de Fin",
        required=True,
        tracking=True,
        help="Fecha de finalización del periodo de congelamiento",
    )

    fecha_aprobacion = fields.Datetime(
        string="Fecha de Aprobación",
        readonly=True,
        help="Fecha y hora de aprobación del congelamiento",
    )

    # CAMPOS DE DÍAS

    dias = fields.Integer(
        string="Días Solicitados",
        compute="_compute_dias",
        store=True,
        help="Número de días del periodo de congelamiento",
    )

    dias_restantes = fields.Integer(
        string="Días Restantes",
        compute="_compute_dias_restantes",
        help="Días que faltan para finalizar el congelamiento (si está activo)",
    )

    # CAMPOS DE ESTADO Y FLUJO

    estado = fields.Selection(
        SELECTION_ESTADO,
        string="Estado",
        default="borrador",
        required=True,
        tracking=True,
        help="Estado actual de la solicitud de congelamiento",
    )

    active = fields.Boolean(string="Activo", default=True)

    # CAMPOS DE CONGELAMIENTO ESPECIAL

    es_especial = fields.Boolean(
        string="Congelamiento Especial",
        default=False,
        tracking=True,
        help="Congelamiento especial que excede los parámetros del plan. "
        "Solo puede ser creado por Coordinación o Cartera. "
        "No visible para el estudiante en el portal.",
    )

    # Mejora 3: Tipos de congelamiento especial
    tipo_especial = fields.Selection(
        [
            ("medico", "Médico"),
            ("viaje", "Viaje"),
            ("laboral", "Laboral/Trabajo"),
            ("familiar", "Situación Familiar"),
            ("economico", "Dificultad Económica"),
            ("academico", "Razones Académicas"),
            ("otro", "Otro"),
        ],
        string="Tipo de Especial",
        tracking=True,
        help="Categoría del congelamiento especial. Requerido para especiales.",
    )

    motivo_especial = fields.Text(
        string="Justificación Especial",
        tracking=True,
        help="Motivo de la excepción para congelamientos especiales. "
        "Requerido cuando es_especial=True",
    )

    # Mejora 3: Documentos de soporte
    documento_soporte_ids = fields.Many2many(
        "ir.attachment",
        "benglish_freeze_attachment_rel",
        "freeze_id",
        "attachment_id",
        string="Documentos de Soporte",
        help="Archivos adjuntos que respaldan la solicitud (certificados médicos, etc.)",
    )

    documentos_pendientes = fields.Boolean(
        string="Documentos Pendientes",
        default=False,
        tracking=True,
        help="Indica si faltan documentos por entregar",
    )

    fecha_limite_documentos = fields.Date(
        string="Fecha Límite Documentos",
        help="Fecha límite para entregar documentación pendiente",
    )

    visible_portal = fields.Boolean(
        string="Visible en Portal",
        compute="_compute_visible_portal",
        store=True,
        help="Indica si el congelamiento es visible para el estudiante en su portal",
    )

    documentacion_completa = fields.Boolean(
        string="Documentación Completa",
        compute="_compute_documentacion_completa",
        help="Indica si se han adjuntado todos los documentos requeridos",
    )

    mensaje_validacion = fields.Html(
        string="Estado de Validación",
        compute="_compute_mensaje_validacion",
        help="Muestra el estado actual de la solicitud y qué falta por completar",
    )

    # CAMPOS DE MOTIVO Y DOCUMENTACIÓN

    freeze_reason_id = fields.Many2one(
        "benglish.freeze.reason",
        string="Motivo de Congelamiento",
        required=True,
        tracking=True,
        domain="[('active', '=', True), '|', ('es_especial', '=', False), ('es_especial', '=', es_especial)]",
        help="Seleccione el motivo principal de su solicitud",
    )

    motivo_detalle = fields.Text(
        string="Descripción Detallada",
        tracking=True,
        help="Explique con más detalle su situación (opcional pero recomendado)",
    )

    # Campo legacy para compatibilidad
    motivo = fields.Text(
        string="Motivo Completo",
        compute="_compute_motivo",
        store=True,
        help="Combinación del motivo seleccionado y los detalles adicionales",
    )

    requiere_documentacion = fields.Boolean(
        string="Requiere Documentación",
        related="freeze_reason_id.requiere_documentacion",
        help="Indica si este motivo requiere documentos de soporte",
    )

    tipos_documentos_requeridos = fields.Text(
        string="Documentos Requeridos",
        related="freeze_reason_id.tipos_documentos",
        help="Tipos de documentos que debe adjuntar",
    )

    motivo_rechazo = fields.Text(
        string="Motivo de Rechazo",
        readonly=True,
        tracking=True,
        help="Explicación del rechazo de la solicitud",
    )

    notas_internas = fields.Text(
        string="Notas Internas",
        tracking=True,
        help="Notas administrativas (no visibles para el estudiante)",
    )

    # CAMPOS DE VALIDACIÓN DE CARTERA

    estudiante_al_dia = fields.Boolean(
        string="Estudiante al Día",
        compute="_compute_estudiante_al_dia",
        help="Indica si el estudiante está al día en sus pagos",
    )

    excepcion_cartera = fields.Boolean(
        string="Excepción de Cartera",
        default=False,
        tracking=True,
        help="Permite aprobar aunque el estudiante no esté al día en pagos",
    )

    motivo_excepcion_cartera = fields.Text(
        string="Motivo Excepción Cartera",
        tracking=True,
        help="Justificación para aprobar sin estar al día en pagos",
    )

    # CAMPOS DE AUDITORÍA

    fecha_fin_original_enrollment = fields.Date(
        string="Fecha Fin Original",
        readonly=True,
        help="Fecha de fin original de la matrícula antes del ajuste",
    )

    fecha_fin_nueva_enrollment = fields.Date(
        string="Fecha Fin Ajustada",
        readonly=True,
        help="Nueva fecha de fin de la matrícula después del ajuste",
    )

    ajuste_aplicado = fields.Boolean(
        string="Ajuste de Fecha Aplicado",
        default=False,
        readonly=True,
        help="Indica si ya se aplicó el ajuste de fecha a la matrícula",
    )

    # CAMPOS COMPUTADOS DE VISUALIZACIÓN

    display_name = fields.Char(compute="_compute_display_name", store=True)

    color = fields.Integer(
        string="Color", compute="_compute_color", help="Color basado en el estado"
    )

    puede_aprobar = fields.Boolean(
        string="Puede Aprobar",
        compute="_compute_puede_aprobar",
        help="Indica si la solicitud cumple requisitos para aprobación",
    )

    # RESTRICCIONES SQL

    _sql_constraints = [
        (
            "fecha_fin_mayor_inicio",
            "CHECK(fecha_fin >= fecha_inicio)",
            "La fecha de fin debe ser posterior o igual a la fecha de inicio.",
        ),
        (
            "dias_positivos",
            "CHECK(dias > 0 OR dias IS NULL)",
            "El número de días debe ser mayor a cero.",
        ),
    ]

    # MÉTODOS COMPUTADOS

    @api.depends("enrollment_id.plan_id")
    def _compute_freeze_config(self):
        """Obtiene la configuración de congelamiento según el plan."""
        FreezeConfig = self.env["benglish.plan.freeze.config"]
        for record in self:
            if record.enrollment_id and record.enrollment_id.plan_id:
                record.freeze_config_id = FreezeConfig.get_config_for_plan(
                    record.enrollment_id.plan_id
                )
            else:
                record.freeze_config_id = False

    @api.depends("fecha_inicio", "fecha_fin")
    def _compute_dias(self):
        """Calcula el número de días del periodo."""
        for record in self:
            if record.fecha_inicio and record.fecha_fin:
                delta = record.fecha_fin - record.fecha_inicio
                record.dias = delta.days + 1  # Incluir ambos días
            else:
                record.dias = 0

    @api.depends("fecha_fin", "estado")
    def _compute_dias_restantes(self):
        """Calcula los días restantes si el congelamiento está activo."""
        today = fields.Date.context_today(self)
        for record in self:
            if record.estado == "aprobado" and record.fecha_fin:
                delta = record.fecha_fin - today
                record.dias_restantes = max(0, delta.days + 1)
            else:
                record.dias_restantes = 0

    @api.depends("es_especial")
    def _compute_visible_portal(self):
        """Los congelamientos especiales no son visibles en el portal."""
        for record in self:
            record.visible_portal = not record.es_especial

    @api.depends("student_id.name", "fecha_inicio", "estado")
    def _compute_display_name(self):
        """Genera el nombre para mostrar."""
        for record in self:
            if record.student_id and record.fecha_inicio:
                estado_display = dict(self.SELECTION_ESTADO).get(record.estado, "")
                record.display_name = (
                    f"{record.student_id.name} - "
                    f"{record.fecha_inicio.strftime('%d/%m/%Y')} "
                    f"({estado_display})"
                )
            else:
                record.display_name = "Nuevo Congelamiento"

    @api.depends("estado")
    def _compute_color(self):
        """Asigna color según el estado."""
        color_map = {
            "borrador": 0,  # Gris
            "pendiente": 3,  # Amarillo
            "aprobado": 10,  # Verde
            "rechazado": 1,  # Rojo
            "cancelado": 2,  # Naranja
            "finalizado": 4,  # Azul claro
        }
        for record in self:
            record.color = color_map.get(record.estado, 0)

    @api.depends("student_id")
    def _compute_estudiante_al_dia(self):
        """Verifica si el estudiante está al día en pagos."""
        for record in self:
            # Obtener el campo al_dia_en_pagos del estudiante
            if record.student_id and hasattr(record.student_id, "al_dia_en_pagos"):
                record.estudiante_al_dia = record.student_id.al_dia_en_pagos
            else:
                # Si no existe el campo, asumir que sí está al día
                record.estudiante_al_dia = True

    @api.depends(
        "estado",
        "estudiante_al_dia",
        "excepcion_cartera",
        "freeze_config_id",
        "dias",
        "es_especial",
    )
    def _compute_puede_aprobar(self):
        """Verifica si la solicitud puede ser aprobada."""
        for record in self:
            if record.estado != "pendiente":
                record.puede_aprobar = False
                continue

            # Congelamientos especiales siempre pueden aprobarse
            if record.es_especial:
                record.puede_aprobar = True
                continue

            # Verificar cartera
            config = record.freeze_config_id
            if config and config.requiere_pago_al_dia:
                if not record.estudiante_al_dia and not record.excepcion_cartera:
                    record.puede_aprobar = False
                    continue

            # Verificar política del plan
            if config and config.permite_congelamiento:
                dias_usados = record._get_dias_usados_estudiante()
                puede, _ = config.can_request_freeze(record.dias, dias_usados)
                record.puede_aprobar = puede
            else:
                record.puede_aprobar = False

    @api.depends("freeze_reason_id", "motivo_detalle")
    def _compute_motivo(self):
        """Combina el motivo seleccionado con los detalles adicionales."""
        for record in self:
            if record.freeze_reason_id:
                motivo_completo = f"[{record.freeze_reason_id.name}]"
                if record.motivo_detalle:
                    motivo_completo += f"\n\n{record.motivo_detalle}"
                record.motivo = motivo_completo
            else:
                record.motivo = record.motivo_detalle or ""

    @api.depends("requiere_documentacion", "documento_soporte_ids")
    def _compute_documentacion_completa(self):
        """Verifica si se han adjuntado los documentos requeridos."""
        for record in self:
            if record.requiere_documentacion:
                record.documentacion_completa = len(record.documento_soporte_ids) > 0
            else:
                record.documentacion_completa = True

    @api.depends(
        "estado",
        "puede_aprobar",
        "estudiante_al_dia",
        "documentacion_completa",
        "freeze_config_id",
        "dias",
        "requiere_documentacion",
    )
    def _compute_mensaje_validacion(self):
        """Genera un mensaje HTML con el estado de validación de la solicitud."""
        for record in self:
            if not record.id:
                record.mensaje_validacion = ""
                continue

            mensajes = []

            # Estado general
            if record.estado == "borrador":
                mensajes.append(
                    '<p><i class="fa fa-info-circle text-info"></i> '
                    "<strong>Estado:</strong> Esta solicitud está en borrador. "
                    "Complete todos los campos y envíela a aprobación.</p>"
                )
            elif record.estado == "pendiente":
                if record.puede_aprobar:
                    mensajes.append(
                        '<p><i class="fa fa-check-circle text-success"></i> '
                        "<strong>Validación exitosa:</strong> Esta solicitud cumple "
                        "todos los requisitos y puede ser aprobada.</p>"
                    )
                else:
                    mensajes.append(
                        '<p><i class="fa fa-exclamation-triangle text-warning"></i> '
                        "<strong>Atención:</strong> Esta solicitud tiene pendientes.</p>"
                    )
            elif record.estado == "aprobado":
                mensajes.append(
                    '<p><i class="fa fa-check-circle text-success"></i> '
                    f"<strong>Aprobado:</strong> Congelamiento activo por {record.dias} días.</p>"
                )
            elif record.estado == "rechazado":
                mensajes.append(
                    '<p><i class="fa fa-times-circle text-danger"></i> '
                    "<strong>Rechazado:</strong> Esta solicitud fue rechazada.</p>"
                )

            # Validación de documentación
            if record.requiere_documentacion:
                if record.documentacion_completa:
                    mensajes.append(
                        '<p><i class="fa fa-check text-success"></i> '
                        "Documentación adjunta correctamente.</p>"
                    )
                else:
                    mensajes.append(
                        '<p><i class="fa fa-exclamation-triangle text-danger"></i> '
                        f'<strong>Falta documentación:</strong> {record.tipos_documentos_requeridos or "Adjunte los documentos requeridos"}</p>'
                    )

            # Validación de cartera
            config = record.freeze_config_id
            if (
                config
                and config.requiere_pago_al_dia
                and record.estado in ("borrador", "pendiente")
            ):
                if record.estudiante_al_dia:
                    mensajes.append(
                        '<p><i class="fa fa-check text-success"></i> '
                        "El estudiante está al día en sus pagos.</p>"
                    )
                else:
                    if record.excepcion_cartera:
                        mensajes.append(
                            '<p><i class="fa fa-info-circle text-info"></i> '
                            "Se aprobó excepción de cartera para este congelamiento.</p>"
                        )
                    else:
                        mensajes.append(
                            '<p><i class="fa fa-exclamation-triangle text-danger"></i> '
                            "<strong>Atención:</strong> El estudiante tiene pagos pendientes. "
                            "Se requiere excepción de cartera para aprobar.</p>"
                        )

            # Información de días
            if record.dias > 0 and config:
                dias_usados = record._get_dias_usados_estudiante()
                dias_disponibles = max(0, config.max_dias_acumulados - dias_usados)
                mensajes.append(
                    f'<p><i class="fa fa-calendar text-info"></i> '
                    f"<strong>Días de congelamiento:</strong> {record.dias} días solicitados. "
                    f"Disponibles: {dias_disponibles} días.</p>"
                )

            record.mensaje_validacion = (
                "".join(mensajes)
                if mensajes
                else '<p class="text-muted">Sin validaciones pendientes</p>'
            )

    # MÉTODOS ONCHANGE

    @api.onchange("student_id")
    def _onchange_student_id(self):
        """Filtra matrículas activas del estudiante seleccionado."""
        if self.student_id:
            # Limpiar matrícula si el estudiante cambió
            if self.enrollment_id and self.enrollment_id.student_id != self.student_id:
                self.enrollment_id = False

            # Devolver dominio para filtrar matrículas
            return {
                "domain": {
                    "enrollment_id": [
                        ("student_id", "=", self.student_id.id),
                        ("state", "in", ["active", "enrolled"]),
                    ]
                }
            }

    @api.onchange("fecha_inicio", "dias")
    def _onchange_calcular_fecha_fin(self):
        """Auto-calcula fecha_fin si se indica fecha_inicio y días."""
        if self.fecha_inicio and self.dias and self.dias > 0:
            self.fecha_fin = self.fecha_inicio + timedelta(days=self.dias - 1)

    @api.onchange("es_especial")
    def _onchange_es_especial(self):
        """Advertencia al marcar como especial."""
        if self.es_especial:
            return {
                "warning": {
                    "title": "Congelamiento Especial",
                    "message": (
                        "Un congelamiento especial no será visible para el estudiante "
                        "en su portal y puede exceder los límites del plan.\n\n"
                        "Por favor documente el motivo de la excepción."
                    ),
                }
            }

    # VALIDACIONES

    @api.constrains("fecha_inicio", "fecha_fin")
    def _check_fechas(self):
        """Valida coherencia de fechas."""
        for record in self:
            if record.fecha_inicio and record.fecha_fin:
                if record.fecha_fin < record.fecha_inicio:
                    raise ValidationError(
                        "La fecha de fin debe ser posterior o igual a la fecha de inicio."
                    )
                # Verificar que no exceda 365 días (límite de seguridad)
                if (record.fecha_fin - record.fecha_inicio).days > 365:
                    raise ValidationError(
                        "El periodo de congelamiento no puede exceder 365 días."
                    )

    @api.constrains("estado", "es_especial", "motivo_especial", "tipo_especial")
    def _check_motivo_especial(self):
        """Valida que congelamientos especiales tengan justificación y tipo."""
        for record in self:
            if record.es_especial:
                if record.estado in ("pendiente", "aprobado"):
                    if not record.motivo_especial:
                        raise ValidationError(
                            "Los congelamientos especiales requieren una justificación."
                        )
                    if not record.tipo_especial:
                        raise ValidationError(
                            "Los congelamientos especiales requieren indicar el tipo."
                        )

    @api.constrains("excepcion_cartera", "motivo_excepcion_cartera")
    def _check_excepcion_cartera(self):
        """Valida que excepciones de cartera tengan motivo."""
        for record in self:
            if record.excepcion_cartera and not record.motivo_excepcion_cartera:
                raise ValidationError(
                    "Debe indicar el motivo de la excepción de cartera."
                )

    @api.constrains("enrollment_id", "fecha_inicio", "fecha_fin", "estado")
    def _check_overlap(self):
        """Valida que no haya solapamiento con otros congelamientos."""
        for record in self:
            if record.estado in ("aprobado", "pendiente"):
                overlapping = self.search(
                    [
                        ("id", "!=", record.id),
                        ("enrollment_id", "=", record.enrollment_id.id),
                        ("estado", "in", ("aprobado", "pendiente")),
                        ("fecha_inicio", "<=", record.fecha_fin),
                        ("fecha_fin", ">=", record.fecha_inicio),
                    ]
                )
                if overlapping:
                    raise ValidationError(
                        f"Existe un solapamiento con otro congelamiento "
                        f"({overlapping[0].display_name}). "
                        "Los periodos de congelamiento no pueden superponerse."
                    )

    # MÉTODOS AUXILIARES

    def _get_dias_usados_estudiante(self):
        """
        Calcula el total de días de congelamiento ya usados por el estudiante
        en la matrícula actual.

        Returns:
            int: Total de días usados
        """
        self.ensure_one()

        congelamientos_previos = self.search(
            [
                ("id", "!=", self.id),
                ("enrollment_id", "=", self.enrollment_id.id),
                ("estado", "in", ("aprobado", "finalizado")),
                ("es_especial", "=", False),  # No contar especiales
            ]
        )

        return sum(congelamientos_previos.mapped("dias"))

    def _get_saldo_disponible(self):
        """
        Obtiene el saldo de días disponibles para congelamiento.

        Returns:
            dict: Información de disponibilidad
        """
        self.ensure_one()

        if not self.freeze_config_id:
            return {
                "disponibles": 0,
                "mensaje": "No hay configuración de congelamiento para este plan",
            }

        dias_usados = self._get_dias_usados_estudiante()
        return self.freeze_config_id.get_available_days(dias_usados)

    # ACCIONES DE FLUJO DE TRABAJO

    def action_enviar_aprobacion(self):
        """Envía la solicitud para aprobación."""
        for record in self:
            if record.estado != "borrador":
                raise UserError("Solo se pueden enviar solicitudes en estado borrador.")

            # Validar política del plan (si no es especial)
            if not record.es_especial and record.freeze_config_id:
                dias_usados = record._get_dias_usados_estudiante()
                puede, mensaje = record.freeze_config_id.can_request_freeze(
                    record.dias, dias_usados
                )
                if not puede:
                    raise ValidationError(mensaje)

            record.estado = "pendiente"
            record.message_post(
                body=f"Solicitud enviada para aprobación. Días solicitados: {record.dias}"
            )

    def action_abrir_preview_aprobacion(self):
        """
        Abre el wizard de preview antes de aprobar.
        Mejora 2: Preview de ajuste de fechas antes de aprobar.
        """
        self.ensure_one()

        if self.estado != "pendiente":
            raise UserError("Solo se pueden aprobar solicitudes pendientes.")

        return {
            "name": "Preview de Aprobación",
            "type": "ir.actions.act_window",
            "res_model": "benglish.freeze.approval.preview.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_freeze_period_id": self.id,
            },
        }

    def action_aprobar(self):
        """
        Aprueba el congelamiento y ajusta la fecha de fin de la matrícula.
        Implementa T-GA-CONG-03 y T-GA-CONG-04.
        """
        for record in self:
            if record.estado != "pendiente":
                raise UserError("Solo se pueden aprobar solicitudes pendientes.")

            # Validar cartera (T-GA-CONG-04)
            if record.freeze_config_id and record.freeze_config_id.requiere_pago_al_dia:
                if not record.estudiante_al_dia and not record.excepcion_cartera:
                    raise ValidationError(
                        "El estudiante no está al día en sus pagos. "
                        "Marque 'Excepción de Cartera' e indique el motivo "
                        "si desea aprobar de todas formas."
                    )

            # Validar política del plan (si no es especial)
            if not record.es_especial and record.freeze_config_id:
                dias_usados = record._get_dias_usados_estudiante()
                puede, mensaje = record.freeze_config_id.can_request_freeze(
                    record.dias, dias_usados
                )
                if not puede:
                    raise ValidationError(
                        f"No se puede aprobar: {mensaje}\n\n"
                        "Si necesita aprobar esta solicitud, márquela como "
                        "'Congelamiento Especial' y justifique la excepción."
                    )

            # Guardar fecha original de enrollment (T-GA-CONG-03)
            enrollment = record.enrollment_id
            fecha_fin_original = enrollment.end_date

            # Calcular nueva fecha de fin
            if fecha_fin_original:
                fecha_fin_nueva = fecha_fin_original + timedelta(days=record.dias)

                # Registrar auditoría
                record.fecha_fin_original_enrollment = fecha_fin_original
                record.fecha_fin_nueva_enrollment = fecha_fin_nueva

                # Aplicar ajuste a la matrícula
                enrollment.sudo().write({"end_date": fecha_fin_nueva})
                record.ajuste_aplicado = True

                _logger.info(
                    f"Congelamiento {record.id}: Ajustada fecha_fin de enrollment {enrollment.id} "
                    f"de {fecha_fin_original} a {fecha_fin_nueva} (+{record.dias} días)"
                )

            # Actualizar estado
            record.write(
                {
                    "estado": "aprobado",
                    "aprobado_por_id": self.env.user.id,
                    "fecha_aprobacion": fields.Datetime.now(),
                }
            )

            # INTEGRACIÓN CON ESTADOS DE MATRÍCULA:
            # Suspender matrículas activas del estudiante
            active_enrollments = self.env["benglish.enrollment"].search(
                [
                    ("student_id", "=", record.student_id.id),
                    (
                        "state",
                        "in",
                        ["active", "enrolled", "in_progress"],
                    ),  # Mapeo legacy
                ]
            )

            if active_enrollments:
                active_enrollments.action_suspend()
                _logger.info(
                    f"Congelamiento {record.id}: Suspendidas {len(active_enrollments)} "
                    f"matrícula(s) activa(s) del estudiante {record.student_id.name}"
                )

            # Registrar mensaje
            record.message_post(
                body=f"""
                <strong>Congelamiento Aprobado</strong><br/>
                <ul>
                    <li>Aprobado por: {self.env.user.name}</li>
                    <li>Días de congelamiento: {record.dias}</li>
                    <li>Periodo: {record.fecha_inicio} - {record.fecha_fin}</li>
                    {f'<li>Fecha fin original: {fecha_fin_original}</li>' if fecha_fin_original else ''}
                    {f'<li>Nueva fecha fin: {fecha_fin_nueva}</li>' if fecha_fin_original else ''}
                    {f'<li>Excepción de cartera: {record.motivo_excepcion_cartera}</li>' if record.excepcion_cartera else ''}
                    {'<li><strong>CONGELAMIENTO ESPECIAL</strong></li>' if record.es_especial else ''}
                    <li><strong>Matrículas suspendidas: {len(active_enrollments)}</strong></li>
                </ul>
                """
            )

    def action_rechazar(self):
        """Abre wizard para indicar motivo de rechazo."""
        self.ensure_one()

        if self.estado != "pendiente":
            raise UserError("Solo se pueden rechazar solicitudes pendientes.")

        return {
            "name": "Rechazar Congelamiento",
            "type": "ir.actions.act_window",
            "res_model": "benglish.freeze.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_freeze_period_id": self.id,
            },
        }

    def action_confirmar_rechazo(self, motivo):
        """Confirma el rechazo con el motivo indicado."""
        self.ensure_one()

        self.write(
            {
                "estado": "rechazado",
                "motivo_rechazo": motivo,
                "rechazado_por_id": self.env.user.id,
            }
        )

        self.message_post(
            body=f"""
            <strong>Solicitud Rechazada</strong><br/>
            <ul>
                <li>Rechazado por: {self.env.user.name}</li>
                <li>Motivo: {motivo}</li>
            </ul>
            """
        )

    def action_cancelar(self):
        """Cancela la solicitud de congelamiento."""
        for record in self:
            if record.estado in ("aprobado", "finalizado"):
                raise UserError(
                    "No se puede cancelar un congelamiento aprobado o finalizado."
                )

            record.estado = "cancelado"
            record.message_post(body="Solicitud cancelada.")

    def action_finalizar(self):
        """
        Marca el congelamiento como finalizado.

        INTEGRACIÓN CON ESTADOS DE MATRÍCULA:
        - Reactiva automáticamente las matrículas suspendidas
        - Valida estado financiero antes de reactivar
        """
        for record in self:
            if record.estado != "aprobado":
                raise UserError("Solo se pueden finalizar congelamientos aprobados.")

            # Buscar matrículas suspendidas del estudiante
            suspended_enrollments = self.env["benglish.enrollment"].search(
                [("student_id", "=", record.student_id.id), ("state", "=", "suspended")]
            )

            # Intentar reactivar cada matrícula
            reactivated = 0
            failed = []

            for enrollment in suspended_enrollments:
                try:
                    enrollment.action_reactivate()
                    reactivated += 1
                except ValidationError as e:
                    # Capturar errores de validación financiera
                    failed.append((enrollment.code, str(e)))
                    _logger.warning(
                        f"No se pudo reactivar enrollment {enrollment.id}: {e}"
                    )

            # Actualizar estado del congelamiento
            record.estado = "finalizado"

            # Mensaje de resultado
            message_body = f"""
            <strong>Periodo de congelamiento finalizado</strong><br/>
            <ul>
                <li>Matrículas reactivadas: {reactivated}</li>
            """

            if failed:
                message_body += "<li><strong style='color: orange;'>Matrículas NO reactivadas por mora:</strong><ul>"
                for code, error in failed:
                    message_body += (
                        f"<li>{code}: Requiere regularización financiera</li>"
                    )
                message_body += "</ul></li>"

            message_body += "</ul>"

            record.message_post(body=message_body)

            _logger.info(
                f"Congelamiento {record.id} finalizado. "
                f"Reactivadas: {reactivated}/{len(suspended_enrollments)}"
            )

    def action_revertir_ajuste(self):
        """
        Revierte el ajuste de fecha de la matrícula.
        Solo para uso administrativo en casos excepcionales.
        """
        self.ensure_one()

        if not self.ajuste_aplicado:
            raise UserError("No hay ajuste de fecha para revertir.")

        if self.estado not in ("aprobado", "cancelado"):
            raise UserError("Solo se puede revertir en estado aprobado o cancelado.")

        if self.fecha_fin_original_enrollment:
            self.enrollment_id.sudo().write(
                {"end_date": self.fecha_fin_original_enrollment}
            )

            self.write(
                {
                    "ajuste_aplicado": False,
                    "fecha_fin_nueva_enrollment": False,
                }
            )

            self.message_post(
                body=f"Ajuste de fecha revertido. Fecha fin restaurada a: "
                f"{self.fecha_fin_original_enrollment}"
            )

    # CRON JOB

    @api.model
    def _cron_finalizar_congelamientos_vencidos(self):
        """
        Job programado para finalizar congelamientos vencidos.
        Ejecutar diariamente.
        """
        today = fields.Date.context_today(self)

        congelamientos_vencidos = self.search(
            [
                ("estado", "=", "aprobado"),
                ("fecha_fin", "<", today),
            ]
        )

        for congelamiento in congelamientos_vencidos:
            congelamiento.action_finalizar()
            _logger.info(
                f"Congelamiento {congelamiento.id} finalizado automáticamente "
                f"(venció el {congelamiento.fecha_fin})"
            )

        return True

    # MÉTODOS DE MODELO

    @api.model_create_multi
    def create(self, vals_list):
        """Crea nuevos registros validando permisos para especiales."""
        for vals in vals_list:
            # Solo coordinación puede crear congelamientos especiales
            if vals.get("es_especial"):
                # TODO: Verificar permisos del usuario
                pass

        return super().create(vals_list)

    def write(self, vals):
        """Actualiza registros con validaciones adicionales."""
        # Evitar modificación de congelamientos finalizados
        if any(rec.estado == "finalizado" for rec in self):
            allowed_fields = {"notas_internas", "active"}
            if not set(vals.keys()).issubset(allowed_fields):
                raise UserError("No se puede modificar un congelamiento finalizado.")

        return super().write(vals)
