from odoo import api, fields, models, _
import datetime
from odoo.exceptions import ValidationError
from datetime import date
from dateutil import relativedelta


class CancelAppointmentWizard(models.TransientModel):
    _name = 'cancel.appointment.wizard'
    _description = 'Cancel Appointment Wizard'

    @api.model
    def default_get(self, fields):
        res = super(CancelAppointmentWizard, self).default_get(fields)
        res['date_cancel'] = datetime.date.today()
        if self.env.context.get('active_id'):
            res['appointment_id'] = self.env.context.get('active_id')

        return res

    # domain=['|',('state', '=', 'draft'), ('priority', 'in', (0, 1))]
    appointment_id = fields.Many2one('hospital.appointment', string="Appointment")
    reason = fields.Text(string="Reason")
    date_cancel = fields.Date(string="Cancellation Date")

    def action_cancel(self):
        for rec in self:
            cancel_day = rec.env['ir.config_parameter'].get_param('om_hospital.cancel_days')
            allowed_date = rec.appointment_id.booking_date + relativedelta.relativedelta(days=int(cancel_day))
            print(allowed_date , cancel_day ,date.today())
            if date.today() > allowed_date:
                raise ValidationError(_("Sorry, Cancellation availability is expired !"))
            else:
                rec.appointment_id.state = 'cancel'
            # if self.appointment_id.booking_date == fields.Date.today():
            #     raise ValidationError(_("Sorry, Cancellation is not allowed on the same day of booking !"))
            # else:
            #     rec.appointment_id.state = 'cancel'
