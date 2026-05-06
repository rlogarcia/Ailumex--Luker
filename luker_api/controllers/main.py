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
