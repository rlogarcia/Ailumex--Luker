# -*- coding: utf-8 -*-
"""
Controlador para descarga de Bitácora Académica
"""

from odoo import http
from odoo.http import request, content_disposition
import io
from datetime import datetime

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class BitacoraController(http.Controller):
    """Controlador para manejar la descarga de registros de bitácora académica."""

    @http.route("/benglish/bitacora/download", type="http", auth="user")
    def download_bitacora(self, ids=None, **kwargs):
        """
        Descarga los registros de bitácora en formato Excel.

        Args:
            ids: IDs de los registros a descargar (separados por coma)

        Returns:
            Archivo Excel con los datos de la bitácora
        """
        if not ids:
            return request.not_found()

        if not xlsxwriter:
            return request.make_response(
                "La librería xlsxwriter no está instalada. Por favor, instálela usando: pip install xlsxwriter",
                headers=[("Content-Type", "text/plain")],
            )

        # Convertir IDs de string a lista de enteros
        record_ids = [int(id_str) for id_str in ids.split(",")]

        # Obtener registros
        history_records = (
            request.env["benglish.academic.history"].sudo().browse(record_ids)
        )

        if not history_records:
            return request.not_found()

        # Crear archivo Excel en memoria
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Bitácora Académica")

        # Formatos
        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#4472C4",
                "font_color": "white",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )

        cell_format = workbook.add_format({"border": 1, "valign": "vcenter"})

        date_format = workbook.add_format(
            {"border": 1, "num_format": "dd/mm/yyyy", "valign": "vcenter"}
        )

        # Encabezados
        headers = [
            "Fecha",
            "Clase",
            "Docente",
            "Novedad",
            "Código del Curso",
            "Observación",
            "Estudiante",
            "Asistencia",
            "Calificación",
        ]

        # Anchos de columna
        column_widths = [12, 25, 25, 20, 18, 40, 25, 15, 12]

        # Escribir encabezados
        for col, (header, width) in enumerate(zip(headers, column_widths)):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, width)

        # Escribir datos
        row = 1
        for record in history_records:
            worksheet.write_datetime(
                row,
                0,
                (
                    datetime.strptime(str(record.session_date), "%Y-%m-%d")
                    if record.session_date
                    else None
                ),
                date_format,
            )
            worksheet.write(row, 1, record.subject_id.name or "", cell_format)
            worksheet.write(row, 2, record.teacher_id.name or "", cell_format)

            # Traducir novedad
            novedad_dict = dict(record._fields["novedad"].selection)
            novedad_text = novedad_dict.get(record.novedad, record.novedad or "")
            worksheet.write(row, 3, novedad_text, cell_format)

            worksheet.write(row, 4, record.session_code or "", cell_format)
            worksheet.write(row, 5, record.notes or "", cell_format)
            worksheet.write(row, 6, record.student_id.name or "", cell_format)

            # Traducir estado de asistencia
            attendance_dict = dict(record._fields["attendance_status"].selection)
            attendance_text = attendance_dict.get(
                record.attendance_status, record.attendance_status or ""
            )
            worksheet.write(row, 7, attendance_text, cell_format)

            worksheet.write(row, 8, record.grade or "", cell_format)

            row += 1

        # Cerrar el workbook
        workbook.close()

        # Preparar respuesta
        output.seek(0)
        filename = f'bitacora_academica_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return request.make_response(
            output.getvalue(),
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )
