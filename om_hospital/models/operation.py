from odoo import api, fields, models, _


class HospitalOperation(models.Model):
    _name = 'hospital.operation'
    _description = 'Hospital Operation'
    _log_access = False

    doctor_id = fields.Many2one('res.users', string='Doctor')
    name = fields.Char(String='Operation Name')
    reference_record = fields.Reference([('hospital.patient','Patient'),('hospital.appointment','Appointment')],string="Record")

    @api.model
    def name_create(self,name):
        return self.create({'operation_name': name}).name_get()[0]