import io
from odoo import http
from odoo.http import request

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

import csv

class ImportLeadsTemplateController(http.Controller):
    @http.route('/crm/import_leads/template', type='http', auth='user')
    def download_template(self, **kwargs):
        # Verificar permisos: sólo usuarios con el grupo de Leads o usuarios
        # normales pueden descargar la plantilla. Si no tienen permisos,
        # devolver 404 (comportamiento original de `request.not_found()`).
        if not (
            request.env.user.has_group('crm.group_use_lead')
            or request.env.user.has_group('base.group_user')
        ):
            return request.not_found()

        wizard_model = request.env['import.leads.wizard']
        headers = getattr(wizard_model, '_required_headers', [])

        # Si la librería xlsxwriter está disponible, generamos un archivo
        # XLSX con un encabezado formateado y una fila de ejemplo.
        if xlsxwriter:
            output = io.BytesIO()
            # Crear libro de trabajo en memoria
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Plantilla Leads')

            # Formato para la fila de encabezados (negrita y fondo azul)
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4F81BD',
                'font_color': '#FFFFFF',
            })

            # Escribir encabezados en la primera fila
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Valores de ejemplo para mostrar cómo rellenar la plantilla
            sample_values = [
                'Juan Pérez',
                'demo@example.com',
                '+523331112233',
                '+523331112244',
                'Empresa Demo',
                'Mexico',
                'Guadalajara',
                'Facebook Ads',
                'Marca Demo',
                'Campaña Verano 2026',
                'MBA Ejecutivo',
                'Perfil Ejecutivo',
                'Interesado en horario vespertino',
                '50000',
            ]
            for col, value in enumerate(sample_values):
                worksheet.write(1, col, value)

            # Ajustar ancho de columnas si hay encabezados
            if headers:
                worksheet.set_column(0, len(headers) - 1, 22)
            workbook.close()

            # Preparar la respuesta HTTP con el contenido del XLSX
            output.seek(0)
            data = output.read()

            filename = 'plantilla_importacion_leads.xlsx'
            return request.make_response(
                data,
                [
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Length', len(data)),
                    ('Content-Disposition', 'attachment; filename="%s"' % filename),
                ],
            )

        # Fallback a CSV si xlsxwriter no está disponible. Se usa BOM UTF-8
        # para asegurar compatibilidad con Excel en Windows.
        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(headers)
        sample_values = [
            'Juan Pérez',
            'demo@example.com',
            '+523331112233',
            '+523331112244',
            'Empresa Demo',
            'Mexico',
            'Guadalajara',
            'Facebook Ads',
            'Marca Demo',
            'Campaña Verano 2026',
            'MBA Ejecutivo',
            'Perfil Ejecutivo',
            'Interesado en horario vespertino',
            '50000',
        ]
        writer.writerow(sample_values)
        # Codificar con BOM para que Excel detecte correctamente UTF-8
        data = csv_output.getvalue().encode('utf-8-sig')
        filename = 'plantilla_importacion_leads.csv'
        return request.make_response(
            data,
            [
                ('Content-Type', 'text/csv; charset=utf-8'),
                ('Content-Length', len(data)),
                ('Content-Disposition', 'attachment; filename="%s"' % filename),
            ],
        )
