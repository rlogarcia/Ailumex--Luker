# -*- coding: utf-8 -*-
# Luker API — Controladores HTTP para PWA offline-first
# Base URL: /luker/api/v1/
import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _json_ok(data, status=200):
    return Response(
        json.dumps({'status': 'ok', 'data': data}, ensure_ascii=False, default=str),
        status=status,
        mimetype='application/json',
        headers=_cors_headers(),
    )


def _json_error(msg, status=400, code=None):
    return Response(
        json.dumps({'status': 'error', 'message': msg, 'code': code}, ensure_ascii=False),
        status=status,
        mimetype='application/json',
        headers=_cors_headers(),
    )


def _cors_headers():
    return {
        'Access-Control-Allow-Origin':  '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age':       '86400',
    }


def _get_token_record():
    """Extrae y valida el token del header Authorization: Bearer <token>."""
    auth = request.httprequest.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token_str = auth[7:].strip()
    return request.env['luker.api.token'].sudo().validar_token(token_str)


def _require_auth():
    """Retorna (token_rec, None) si OK, o (None, respuesta_error) si falla."""
    rec = _get_token_record()
    if not rec:
        return None, _json_error('Token inválido o expirado.', 401, 'AUTH_REQUIRED')
    return rec, None


# ── Serializadores ────────────────────────────────────────────────────────────

def _serializar_participante(p):
    return {
        'id':               p.id,
        'cod_participante': p.cod_participante,
        'nom_completo':     p.nom_completo,
        'uuid_local':       p.uuid_local,
        'email':            p.email or '',
        'telefono':         p.telefono or '',
        'tipo':             p.tipo_participante_id.nom_tipo_participante if p.tipo_participante_id else '',
        'estado':           p.estado,
        'institucion':      p.institucion_actual_id.nom_unidad if p.institucion_actual_id else '',
    }


def _serializar_pregunta(q):
    """
    Serializa una pregunta con TODOS los campos extendidos de ailmx_extend_survey.
    La PWA usa esto para renderizar cada tipo de pregunta en offline.
    """
    base = {
        'id':        q.id,
        'titulo':    q.title or '',
        'descripcion': q.description or '',
        'tipo_nativo': q.question_type,          # Tipo Odoo base
        'secuencia': q.sequence,
        'es_pagina':  q.is_page,

        # ── Campos extendidos (ailmx_extend_survey) ──────────────────────
        'tipo_custom':     q.id_question_type.cod_question_type if q.id_question_type else None,
        'nombre_tipo':     q.id_question_type.nam_question_type if q.id_question_type else None,
        'requerida':       q.flg_required,
        'config_json':     q.des_config_json or {},

        # Tiempo límite
        'flg_time_limit':      q.flg_time_limit,
        'valor_limite_tiempo': q.valor_limite_tiempo,
        'unidad_limite_tiempo': q.unidad_limite_tiempo,

        # Adjuntos de imagen en la pregunta
        'flg_allow_image_attachment': q.flg_allow_image_attachment,

        # Grabación de voz
        'flg_auto_voice_record': q.flg_auto_voice_record,
        'modo_grabacion_voz':    q.modo_grabacion_voz,

        # Condiciones de fin (lógica de salto)
        'condiciones_fin_json':    q.condiciones_fin_json or {},
        'condiciones_fin_opciones': q.condiciones_fin_opciones or {},
        'condiciones_fin_texto':   q.condiciones_fin_texto or '',

        # Secciones
        'indice_seccion':     q.indice_seccion,
        'total_secciones':    q.total_secciones,
        'mostrar_info_seccion': q.mostrar_info_seccion,

        # Opciones de respuesta (simple_choice / multiple_choice)
        'opciones': [
            {
                'id':      opt.id,
                'valor':   opt.value or '',
                'correcta': opt.flg_is_correct if hasattr(opt, 'flg_is_correct') else False,
            }
            for opt in q.suggested_answer_ids
        ],
    }

    # ── Grillas de lectura ───────────────────────────────────────────────────
    if q.question_type == 'reading_grid' and hasattr(q, 'reading_grid_ids'):
        base['grilla_lectura'] = [
            {
                'id':        cell.id,
                'contenido': cell.content or '',
                'fila':      cell.row_index if hasattr(cell, 'row_index') else 0,
                'columna':   cell.col_index if hasattr(cell, 'col_index') else 0,
            }
            for cell in q.reading_grid_ids
        ]

    # ── Grillas matemáticas ──────────────────────────────────────────────────
    if q.question_type == 'math_grid' and hasattr(q, 'math_grid_ids'):
        base['grilla_matematica'] = [
            {
                'id':        cell.id,
                'contenido': cell.content or '',
                'fila':      cell.row_index if hasattr(cell, 'row_index') else 0,
                'columna':   cell.col_index if hasattr(cell, 'col_index') else 0,
                'tipo_celda': cell.cell_type if hasattr(cell, 'cell_type') else 'text',
            }
            for cell in q.math_grid_ids
        ]

    return base


def _serializar_encuesta(survey):
    """
    Serializa la encuesta completa para descarga offline.
    Incluye páginas, preguntas y toda la configuración extendida.
    """
    elementos = []
    for item in survey.question_and_page_ids:
        if item.is_page:
            elementos.append({
                'id':      item.id,
                'es_pagina': True,
                'titulo':  item.title or '',
                'secuencia': item.sequence,
            })
        else:
            elementos.append(_serializar_pregunta(item))

    preguntas = [e for e in elementos if not e.get('es_pagina')]

    return {
        'id':              survey.id,
        'titulo':          survey.title,
        'estado':          survey.state,
        'descripcion':     survey.description or '',
        'elementos':       elementos,        # Páginas + preguntas en orden
        'preguntas':       preguntas,        # Solo preguntas (para indexar en offline)
        'total_preguntas': len(preguntas),
    }


# ── Controlador principal ─────────────────────────────────────────────────────

class LukerApiController(http.Controller):

    # ── Bootstrap PWA ─────────────────────────────────────────────────────────

    @http.route('/luker/api/v1/bootstrap',
                auth='none', methods=['POST'], csrf=False, type='http')
    def bootstrap(self, **kwargs):
        """
        Descarga todo lo que la PWA necesita en UN solo llamado:
        - Perfil del participante/ejecutor
        - Tareas del día asignadas
        - Instrumentos completos de las tareas
        - Catálogos (tipos de pregunta, tipos de incidente)
        Diseñado para conexión lenta — payload mínimo.
        """
        token_rec, err = _require_auth()
        if err:
            return err

        executor = request.env['luker.operation.executor'].sudo().search([
            ('user_id', '=', token_rec.participante_id.user_id.id
                            if token_rec.participante_id else 0)
        ], limit=1)

        # Tareas activas del ejecutor
        tareas = []
        if executor:
            tasks = request.env['luker.operation.task'].sudo().search([
                ('executor_id', '=', executor.id),
                ('estado', 'in', ('pendiente', 'programado', 'en_progreso', 'reprogramado')),
            ])
            for t in tasks:
                tarea_data = {
                    'id':              t.id,
                    'cod_tarea':       t.cod_tarea,
                    'uuid_local':      t.uuid_local,
                    'estado':          t.estado,
                    'estado_sync':     t.estado_sync,
                    'fecha_programada': str(t.fecha_programada) if t.fecha_programada else None,
                    'campana': {
                        'id':     t.campana_id.id,
                        'nombre': t.campana_id.nom_campana,
                        'codigo': t.campana_id.cod_campana,
                    } if t.campana_id else None,
                    'participante': _serializar_participante(t.participante_id)
                                    if t.participante_id else None,
                    'instrumento_id': t.survey_id.id if t.survey_id else None,
                }
                tareas.append(tarea_data)

        # Instrumentos únicos de las tareas
        survey_ids = list(set(
            t['instrumento_id'] for t in tareas if t.get('instrumento_id')
        ))
        instrumentos = {}
        for sid in survey_ids:
            survey = request.env['survey.survey'].sudo().browse(sid)
            if survey.exists():
                instrumentos[sid] = _serializar_encuesta(survey)

        # Catálogos
        tipos_incidente = [
            {'id': t.id, 'cod': t.cod_tipo, 'nombre': t.nom_tipo,
             'impacto': t.impacto, 'requiere_reprogramacion': t.requiere_reprogramacion}
            for t in request.env['luker.operation.incident.type'].sudo().search(
                [('activo', '=', True)]
            )
        ]

        return _json_ok({
            'ejecutor': {
                'id':       executor.id if executor else None,
                'nombre':   executor.nom_ejecutor if executor else None,
                'cod':      executor.cod_ejecutor if executor else None,
                'rol':      executor.rol_id.nom_rol if executor and executor.rol_id else None,
            },
            'participante': _serializar_participante(token_rec.participante_id)
                            if token_rec.participante_id else None,
            'tareas':       tareas,
            'instrumentos': instrumentos,
            'catalogos': {
                'tipos_incidente': tipos_incidente,
            },
            'total_tareas': len(tareas),
        })

    # ── Tareas del ejecutor ───────────────────────────────────────────────────

    @http.route('/luker/api/v1/tasks',
                auth='none', methods=['GET'], csrf=False, type='http')
    def tasks(self, **kwargs):
        """Lista de tareas asignadas al ejecutor autenticado."""
        token_rec, err = _require_auth()
        if err:
            return err

        executor = request.env['luker.operation.executor'].sudo().search([
            ('user_id', '=', token_rec.participante_id.user_id.id
                            if token_rec.participante_id else 0)
        ], limit=1)

        if not executor:
            return _json_ok({'tareas': [], 'total': 0})

        tasks = request.env['luker.operation.task'].sudo().search([
            ('executor_id', '=', executor.id),
        ], order='fecha_programada asc')

        tareas = [{
            'id':              t.id,
            'cod_tarea':       t.cod_tarea,
            'uuid_local':      t.uuid_local,
            'estado':          t.estado,
            'estado_sync':     t.estado_sync,
            'fecha_programada': str(t.fecha_programada) if t.fecha_programada else None,
            'campana_id':      t.campana_id.id if t.campana_id else None,
            'survey_id':       t.survey_id.id if t.survey_id else None,
            'participante':    _serializar_participante(t.participante_id)
                               if t.participante_id else None,
        } for t in tasks]

        return _json_ok({'tareas': tareas, 'total': len(tareas)})

    # ── Actualizar estado de tarea ────────────────────────────────────────────

    @http.route('/luker/api/v1/tasks/<int:task_id>/status',
                auth='none', methods=['POST'], csrf=False, type='http')
    def task_update_status(self, task_id, **kwargs):
        """Actualiza el estado de una tarea desde la PWA."""
        token_rec, err = _require_auth()
        if err:
            return err

        try:
            body = __import__('json').loads(
                request.httprequest.data or b'{}'
            )
        except Exception:
            return _json_error('Body JSON inválido.', 400)

        nuevo_estado = body.get('estado')
        estados_validos = ('pendiente','programado','en_progreso',
                          'completado','fallido','reprogramado','cancelado')
        if nuevo_estado not in estados_validos:
            return _json_error(
                f'Estado inválido. Válidos: {estados_validos}', 400
            )

        task = request.env['luker.operation.task'].sudo().browse(task_id)
        if not task.exists():
            return _json_error('Tarea no encontrada.', 404)

        task.write({'estado': nuevo_estado, 'estado_sync': 'synced'})
        return _json_ok({'id': task_id, 'estado': nuevo_estado})

    # ── Registrar incidente ───────────────────────────────────────────────────

    @http.route('/luker/api/v1/incidents',
                auth='none', methods=['POST'], csrf=False, type='http')
    def create_incident(self, **kwargs):
        """
        Registra un incidente de campo capturado offline.
        Body: {uuid_local, tipo_cod, descripcion, task_id, timestamp}
        """
        token_rec, err = _require_auth()
        if err:
            return err

        try:
            body = __import__('json').loads(
                request.httprequest.data or b'{}'
            )
        except Exception:
            return _json_error('Body JSON inválido.', 400)

        uuid_op = body.get('uuid_local')
        if not uuid_op:
            return _json_error('uuid_local requerido.', 400)

        # Idempotencia
        existente = request.env['luker.operation.incident'].sudo().search([
            ('uuid_local', '=', uuid_op)
        ], limit=1)
        if existente:
            return _json_ok({'id': existente.id, 'estado': existente.estado,
                             'duplicado': True})

        tipo = request.env['luker.operation.incident.type'].sudo().search([
            ('cod_tipo', '=', body.get('tipo_cod'))
        ], limit=1)
        if not tipo:
            return _json_error('Tipo de incidente no encontrado.', 404)

        task = None
        if body.get('task_id'):
            task = request.env['luker.operation.task'].sudo().browse(
                body['task_id']
            )

        executor = request.env['luker.operation.executor'].sudo().search([
            ('user_id', '=', token_rec.participante_id.user_id.id
                            if token_rec.participante_id else 0)
        ], limit=1)

        incident = request.env['luker.operation.incident'].sudo().create({
            'uuid_local':       uuid_op,
            'tipo_id':          tipo.id,
            'descripcion':      body.get('descripcion', ''),
            'task_id':          task.id if task and task.exists() else False,
            'campana_id':       task.campana_id.id if task and task.exists() else False,
            'executor_id':      executor.id if executor else False,
            'enviado_offline':  True,
            'fecha_incidente':  body.get('timestamp') or __import__('odoo').fields.Datetime.now(),
        })

        return _json_ok({
            'id':     incident.id,
            'estado': incident.estado,
            'codigo': incident.cod_incidente,
        })

    # ── CORS preflight ────────────────────────────────────────────────────────

    @http.route('/luker/api/v1/<path:subpath>',
                auth='none', methods=['OPTIONS'], csrf=False, cors='*')
    def options_handler(self, subpath, **kwargs):
        return Response('', status=204, headers=_cors_headers())

    # ── Ping / health check ───────────────────────────────────────────────────

    @http.route('/luker/api/v1/ping',
                auth='none', methods=['GET'], csrf=False, type='http')
    def ping(self, **kwargs):
        """Verifica que el API está en línea."""
        return _json_ok({'mensaje': 'Luker API activa', 'version': '1.0'})

    # ── Autenticación ─────────────────────────────────────────────────────────

    @http.route('/luker/api/v1/auth/login',
                auth='none', methods=['POST'], csrf=False, type='http')
    def login(self, **kwargs):
        """
        Autentica un dispositivo por número de documento del participante.
        Body JSON: { "num_documento": "...", "dispositivo_id": "..." }
        Retorna: { "token": "...", "participante": {...} }
        """
        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json_error('Body JSON inválido.', 400, 'INVALID_JSON')

        num_doc       = (body.get('num_documento') or '').strip()
        dispositivo   = (body.get('dispositivo_id') or '').strip()

        if not num_doc or not dispositivo:
            return _json_error('num_documento y dispositivo_id son requeridos.', 400, 'MISSING_FIELDS')

        # Buscar participante por identidad principal
        identidad = request.env['luker.participant.identity'].sudo().search([
            ('num_identidad', '=', num_doc),
            ('estado', '=', 'activa'),
        ], limit=1)

        if not identidad:
            return _json_error('Participante no encontrado.', 404, 'NOT_FOUND')

        participante = identidad.participante_id
        if participante.estado != 'activo':
            return _json_error('Participante inactivo.', 403, 'INACTIVE')

        ip = request.httprequest.remote_addr
        token_str = request.env['luker.api.token'].sudo().generar_token(
            participante.id, dispositivo, ip
        )

        return _json_ok({
            'token':        token_str,
            'participante': _serializar_participante(participante),
            'expira_dias':  30,
        })

    # ── Participante ──────────────────────────────────────────────────────────

    @http.route('/luker/api/v1/participant/me',
                auth='none', methods=['GET'], csrf=False, type='http')
    def participant_me(self, **kwargs):
        """Retorna el perfil del participante autenticado."""
        token_rec, err = _require_auth()
        if err:
            return err

        p = token_rec.participante_id.sudo()
        if not p:
            return _json_error('Token sin participante vinculado.', 404, 'NO_PARTICIPANT')

        return _json_ok(_serializar_participante(p))

    # ── Encuestas ─────────────────────────────────────────────────────────────

    @http.route('/luker/api/v1/surveys',
                auth='none', methods=['GET'], csrf=False, type='http')
    def surveys_list(self, **kwargs):
        """
        Lista encuestas publicadas disponibles para aplicar offline.
        """
        token_rec, err = _require_auth()
        if err:
            return err

        surveys = request.env['survey.survey'].sudo().search([
            ('state', '=', 'open'),
        ])

        data = [{
            'id':     s.id,
            'titulo': s.title,
            'estado': s.state,
            'total_preguntas': s.question_count,
        } for s in surveys]

        return _json_ok({'encuestas': data, 'total': len(data)})

    @http.route('/luker/api/v1/surveys/<int:survey_id>',
                auth='none', methods=['GET'], csrf=False, type='http')
    def survey_detail(self, survey_id, **kwargs):
        """
        Descarga la estructura completa de una encuesta para uso offline.
        Incluye todas las preguntas, opciones y configuración extendida.
        """
        token_rec, err = _require_auth()
        if err:
            return err

        survey = request.env['survey.survey'].sudo().browse(survey_id)
        if not survey.exists():
            return _json_error(f'Encuesta {survey_id} no encontrada.', 404, 'NOT_FOUND')

        return _json_ok(_serializar_encuesta(survey))

    # ── Sincronización ────────────────────────────────────────────────────────

    @http.route('/luker/api/v1/sync',
                auth='none', methods=['POST'], csrf=False, type='http')
    def sync(self, **kwargs):
        """
        Recibe y procesa un lote de sesiones capturadas offline.
        Body JSON:
        {
          "sesiones": [
            {
              "uuid_local": "...",
              "survey_id": 123,
              "fecha_inicio": "2026-05-02T10:00:00",
              "fecha_fin":    "2026-05-02T10:30:00",
              "responses": [{"question_id": 1, "value": "texto"}, ...]
            }
          ]
        }
        """
        token_rec, err = _require_auth()
        if err:
            return err

        try:
            body = json.loads(request.httprequest.data or '{}')
        except json.JSONDecodeError:
            return _json_error('Body JSON inválido.', 400, 'INVALID_JSON')

        sesiones  = body.get('sesiones', [])
        resultados = []

        SyncQ = request.env['luker.sync.queue'].sudo()

        for sesion in sesiones:
            uuid_op = sesion.get('uuid_local')
            if not uuid_op:
                resultados.append({'error': 'uuid_local requerido', 'sesion': sesion})
                continue

            try:
                rec = SyncQ.encolar(
                    uuid_op      = uuid_op,
                    tipo         = 'sync_sesion',
                    payload_dict = {
                        **sesion,
                        'participante_id': token_rec.participante_id.id,
                    },
                    token_rec    = token_rec,
                    dispositivo_id = token_rec.dispositivo_id,
                )
                resultados.append({
                    'uuid_local': uuid_op,
                    'estado':     rec.estado_cola,
                    'resultado_id': rec.resultado_id.id if rec.resultado_id else None,
                })
            except Exception as exc:
                _logger.error('Error encolando sesión %s: %s', uuid_op, exc)
                resultados.append({
                    'uuid_local': uuid_op,
                    'estado':     'error',
                    'mensaje':    str(exc)[:200],
                })

        ok     = sum(1 for r in resultados if r.get('estado') == 'completado')
        errores = sum(1 for r in resultados if r.get('estado') == 'error')

        return _json_ok({
            'total':    len(sesiones),
            'exitosas': ok,
            'errores':  errores,
            'detalle':  resultados,
        })

    # ── Estado de sync ────────────────────────────────────────────────────────

    @http.route('/luker/api/v1/sync/status/<string:uuid_local>',
                auth='none', methods=['GET'], csrf=False, type='http')
    def sync_status(self, uuid_local, **kwargs):
        """Consulta el estado de procesamiento de una sesión por su uuid_local."""
        token_rec, err = _require_auth()
        if err:
            return err

        rec = request.env['luker.sync.queue'].sudo().search([
            ('uuid_operacion', '=', uuid_local),
        ], limit=1)

        if not rec:
            return _json_error('Operación no encontrada.', 404, 'NOT_FOUND')

        return _json_ok({
            'uuid_local':   uuid_local,
            'estado':       rec.estado_cola,
            'intentos':     rec.intentos,
            'ultimo_error': rec.ultimo_error or '',
            'resultado_id': rec.resultado_id.id if rec.resultado_id else None,
        })
