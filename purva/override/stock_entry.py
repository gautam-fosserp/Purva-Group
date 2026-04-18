from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.utils import get_incoming_rate
from frappe.utils import flt


class CustomStockEntry(StockEntry):
    """Use custom rate logic only for the Material Transfer stock entry type."""

    def is_material_transfer_type(self):
        return self.stock_entry_type == "Material Transfer"

    def set_rate_for_outgoing_items(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
        """Use custom_updated_rate only for outgoing items in Material Transfer."""
        outgoing_items_cost = 0.0
        for d in self.get("items"):
            if d.s_warehouse:
                if self.is_material_transfer_type() and d.get("custom_updated_rate"):
                    d.basic_rate = d.custom_updated_rate
                elif reset_outgoing_rate:
                    args = self.get_args_for_incoming_rate(d)
                    rate = get_incoming_rate(args, raise_error_if_no_rate)
                    if rate >= 0:
                        d.basic_rate = rate

                d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))
                if not d.t_warehouse:
                    outgoing_items_cost += flt(d.basic_amount)

        return outgoing_items_cost

    def set_basic_rate(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
        """Ensure basic_amount is always calculated for incoming items even when
        set_basic_rate_manually is checked. ERPNext skips the entire loop body
        (including basic_amount) when set_basic_rate_manually=True, leaving
        basic_amount=0 on finished/incoming items in Repack entries."""
        super().set_basic_rate(reset_outgoing_rate, raise_error_if_no_rate)

        for d in self.get("items"):
            if d.set_basic_rate_manually and not d.s_warehouse:
                d.basic_amount = flt(flt(d.transfer_qty) * flt(d.basic_rate), d.precision("basic_amount"))

