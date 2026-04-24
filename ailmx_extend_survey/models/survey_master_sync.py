# -*- coding: utf-8 -*-

# =========================================================
# PUENTE ENTRE survey.user_input Y luker_master
# =========================================================
#
# Este archivo NO reemplaza nada del flujo actual.
# Solo agrega:
# 1. Un vínculo con el participante maestro de luker_master
# 2. Un vínculo con la sesión maestra (luker.application.result)
# 3. Un helper para crear/sincronizar esa sesión maestra
#
# Objetivo de esta fase:
# - No romper ailmx_extend_survey
# - No eliminar modelos viejos
# - Hacer que luker_master empiece a ser la fuente operativa
#
# =========================================================

from odoo import models, fields, api


class SurveyMasterSync(models.Model):
    _inherit = 'survey.user_input'

    # =========================================================
    # CAMPOS PUENTE HACIA luker_master
    # =========================================================

    luker_participant_id = fields.Many2one(
        comodel_name='luker.participant',
        string='Participante maestro',
        ondelete='set null',
        index=True,
        help='Participante maestro en luker_master asociado a esta aplicación.'
    )

    luker_application_result_id = fields.Many2one(
        comodel_name='luker.application.result',
        string='Sesión maestra',
        ondelete='set null',
        index=True,
        help='Sesión/aplicación operativa maestra asociada a esta respuesta de encuesta.'
    )

    # =========================================================
    # MÉTODO 1: BUSCAR PARTICIPANTE MAESTRO DESDE partner_id
    # =========================================================
    #
    # Regla recomendada en esta fase:
    # usar partner_id de survey.user_input como puente
    # hacia luker.participant.
    #
    # Esto tiene sentido porque:
    # - luker.participant ya está vinculado 1:1 con res.partner
    # - survey.user_input ya maneja partner_id en tu flujo actual
    #
    # =========================================================
    def _get_luker_participant_from_partner(self):
        """
        Busca el participante maestro de luker_master usando partner_id.

        Retorna:
        - un registro de luker.participant si existe
        - False si no se encuentra
        """
        self.ensure_one()

        if not self.partner_id:
            return False

        participant = self.env['luker.participant'].search([
            ('partner_id', '=', self.partner_id.id)
        ], limit=1)

        return participant or False

    # =========================================================
    # MÉTODO 2: ARMAR SNAPSHOT DE CONTEXTO ACTUAL
    # =========================================================
    #
    # luker.application.result ya está pensado para congelar
    # el contexto al momento de la sesión:
    # - institución
    # - sede
    # - grado/grupo
    # - jornada
    #
    # Aquí lo construimos desde el participante maestro.
    # =========================================================
    def _build_luker_context_snapshot_vals(self, luker_participant):
        """
        Construye un diccionario con los valores snapshot
        del contexto actual del participante maestro.

        Parámetros:
        - luker_participant: registro de luker.participant

        Retorna:
        - dict con campos snapshot listos para escribir
          en luker.application.result
        """
        self.ensure_one()

        vals = {
            'snapshot_institucion': False,
            'snapshot_sede': False,
            'snapshot_grado_grupo': False,
            'snapshot_jornada': False,
        }

        if not luker_participant:
            return vals

        # -----------------------------------------------------
        # Buscar asignación actual del participante
        # -----------------------------------------------------
        current_assignment = self.env['luker.participant.assignment'].search([
            ('participante_id', '=', luker_participant.id),
            ('vigencia_hasta', '=', False),
        ], order='vigencia_desde desc, id desc', limit=1)

        if not current_assignment:
            return vals

        # -----------------------------------------------------
        # Snapshot de institución
        # -----------------------------------------------------
        if current_assignment.institucion_id:
            vals['snapshot_institucion'] = current_assignment.institucion_id.nom_unidad

        # -----------------------------------------------------
        # Snapshot de sede
        # -----------------------------------------------------
        if current_assignment.sede_id:
            vals['snapshot_sede'] = current_assignment.sede_id.nom_sede

        # -----------------------------------------------------
        # Snapshot de unidad / grado / grupo
        # -----------------------------------------------------
        if current_assignment.unidad_id:
            unit = current_assignment.unidad_id

            unit_parts = []

            if unit.nom_grado:
                unit_parts.append(str(unit.nom_grado))

            if unit.nom_grupo:
                unit_parts.append(str(unit.nom_grupo))

            vals['snapshot_grado_grupo'] = ' - '.join(unit_parts) if unit_parts else unit.display_name

            if unit.jornada:
                # Convertimos el valor técnico a etiqueta visible
                jornada_label = dict(unit._fields['jornada'].selection).get(unit.jornada)
                vals['snapshot_jornada'] = jornada_label or unit.jornada

        return vals

    # =========================================================
    # MÉTODO 3: PREPARAR VALORES DE LA SESIÓN MAESTRA
    # =========================================================
    #
    # Este método construye los valores base para crear o
    # actualizar luker.application.result.
    # =========================================================
    def _prepare_luker_application_result_vals(self, luker_participant):
        """
        Prepara los valores base para crear o actualizar
        luker.application.result desde survey.user_input.

        Parámetros:
        - luker_participant: registro de luker.participant

        Retorna:
        - dict con valores para create/write
        """
        self.ensure_one()

        snapshot_vals = self._build_luker_context_snapshot_vals(luker_participant)

        vals = {
            # -------------------------------------------------
            # Enlace principal de sesión maestra
            # -------------------------------------------------
            'participante_id': luker_participant.id,
            'survey_input_id': self.id,

            # -------------------------------------------------
            # Snapshot del participante
            # En esta fase lo dejamos simple y legible.
            # Más adelante podríamos guardar JSON real.
            # -------------------------------------------------
            'snapshot_perfil_participante': (
                f'Participante: {luker_participant.nom_completo or ""}\n'
                f'Código: {luker_participant.cod_participante or ""}\n'
                f'Tipo: {luker_participant.tipo_participante_id.display_name or ""}\n'
                f'Contacto: {luker_participant.partner_id.display_name or ""}'
            ),

            # -------------------------------------------------
            # Datos del instrumento
            # -------------------------------------------------
            'cod_instrumento': (
                getattr(self.survey_id, 'Cod_Instrument', False) or
                self.survey_id.title or
                False
            ),
            'version_instrumento': False,

            # -------------------------------------------------
            # Tiempos
            # -------------------------------------------------
            'fecha_hora_inicio_dispositivo': self.create_date or fields.Datetime.now(),
            'fecha_hora_recepcion_servidor': fields.Datetime.now(),

            # -------------------------------------------------
            # Estado base
            # -------------------------------------------------
            'estado_sesion': 'sincronizada',

            # -------------------------------------------------
            # Snapshot de contexto
            # -------------------------------------------------
            **snapshot_vals,
        }

        # -----------------------------------------------------
        # Si el survey.user_input tiene scoring_percentage
        # aprovechamos ese dato para el resultado maestro.
        # -----------------------------------------------------
        if hasattr(self, 'scoring_percentage'):
            vals['puntaje_normalizado'] = self.scoring_percentage or 0.0

        return vals

    # =========================================================
    # MÉTODO 4: ASEGURAR VÍNCULO CON EL PARTICIPANTE MAESTRO
    # =========================================================
    def action_sync_luker_participant(self):
        """
        Busca el participante maestro desde partner_id
        y lo guarda en luker_participant_id.

        Este método no crea participantes nuevos.
        Solo enlaza si ya existe el participante maestro.
        """
        for record in self:
            luker_participant = record._get_luker_participant_from_partner()

            if luker_participant:
                record.luker_participant_id = luker_participant.id
            else:
                record.luker_participant_id = False

        return True

    # =========================================================
    # MÉTODO 5: CREAR O ACTUALIZAR LA SESIÓN MAESTRA
    # =========================================================
    #
    # Este es el método principal que usaremos más adelante
    # desde el flujo de guardado custom.
    #
    # Regla:
    # - si no hay participante maestro, no creamos sesión
    # - si ya existe sesión maestra, la actualizamos
    # - si no existe, la creamos
    # =========================================================
    def action_sync_luker_application_result(self):
        """
        Crea o actualiza la sesión maestra de luker_master
        asociada a este survey.user_input.
        """
        LukerApplicationResult = self.env['luker.application.result']

        for record in self:
            # -------------------------------------------------
            # Paso 1: asegurar participante maestro
            # -------------------------------------------------
            luker_participant = record._get_luker_participant_from_partner()

            if not luker_participant:
                # En esta fase no creamos el participante;
                # solo enlazamos si ya existe.
                record.luker_participant_id = False
                record.luker_application_result_id = False
                continue

            record.luker_participant_id = luker_participant.id

            # -------------------------------------------------
            # Paso 2: preparar valores de sesión maestra
            # -------------------------------------------------
            vals = record._prepare_luker_application_result_vals(luker_participant)

            # -------------------------------------------------
            # Paso 3: buscar una sesión maestra existente
            # -------------------------------------------------
            existing_result = LukerApplicationResult.search([
                ('survey_input_id', '=', record.id)
            ], limit=1)

            # -------------------------------------------------
            # Paso 4: actualizar o crear
            # -------------------------------------------------
            if existing_result:
                existing_result.write(vals)
                record.luker_application_result_id = existing_result.id
            else:
                new_result = LukerApplicationResult.create(vals)
                record.luker_application_result_id = new_result.id

        return True

    # =========================================================
    # MÉTODO 6: MÉTODO GENERAL DE SINCRONIZACIÓN
    # =========================================================
    def action_sync_luker_master_bridge(self):
        """
        Método general para sincronizar:
        1. participante maestro
        2. sesión maestra operativa
        """
        for record in self:
            record.action_sync_luker_participant()
            record.action_sync_luker_application_result()

        return True