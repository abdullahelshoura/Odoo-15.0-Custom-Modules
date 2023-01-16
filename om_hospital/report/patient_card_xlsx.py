from odoo import models
class PatientCardXlsx(models.AbstractModel):
    _name = 'report.om_hospital.report_patient_card_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    def generate_xlsx_report(self, workbook, data, patients):
        sheet = workbook.add_worksheet("Patient ID Card's")
        bold = workbook.add_format({'bold': True,'align':'center'})
        bg_format = workbook.add_format({'bold': True,'align':'center','bg_color':'yellow'})
        format1 = workbook.add_format({'align': 'center'})
        sheet.set_column('C:D', 15)
        row = 3
        col = 3
        for obj in patients:
            import base64
            import io

            sheet.merge_range(row, col - 1, row, col, 'ID Card', bg_format)
            row += 1
            if obj.image:
                sheet.merge_range(row, col - 1, row, col, 'ID Card', bg_format)
                patient_image = io.BytesIO(base64.b64decode(obj.image))
                sheet.insert_image(row,col,"image.png",{'image_data': patient_image, 'x_scale': 0.5, 'y_scale': 0.5})
                row+=7

            sheet.write(row, col - 1, "ID Card", bold)
            sheet.write(row, col-1, "Name", bold)
            sheet.write(row, col, obj.name, format1)

            row+=1

            sheet.write(row, col - 1, "Age", bold)
            sheet.write(row, col, obj.age,format1)

            row+=1

            sheet.write(row, col - 1, "Reference", bold)
            sheet.write(row, col, obj.ref, format1)

            row+=2