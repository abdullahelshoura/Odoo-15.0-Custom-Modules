
from odoo import models, fields, api


class CancelJournalWizard(models.TransientModel):
    _name = 'cancel.journal.wizard'
    _description = 'Journal Cancellation'

    move_id = fields.Many2one('account.move', string="Journal", required=True)

    # def action_cancel(self):

    def action_cancel(self):
        for rec in self:
            rec.move_id.unlink()
        return {
                'type': 'ir.actions.client',
                'tag': 'reload',
        }