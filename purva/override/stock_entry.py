import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.utils import get_incoming_rate
from frappe.utils import flt

class CustomStockEntry(StockEntry):
    """
    Customised Stock Entry to use custom_updated_rate for Material Transfer.
    """

    def set_rate_for_outgoing_items(self, reset_outgoing_rate=True, raise_error_if_no_rate=True):
        """
        Override the method that sets basic_rate for items with a source warehouse.
        If the purpose is 'Material Transfer' and the item has custom_updated_rate,
        use that value instead of fetching the incoming rate.
        """
        outgoing_items_cost = 0.0
        for d in self.get("items"):
            if d.s_warehouse:
                # Use custom rate for Material Transfer if present
                if self.purpose == "Material Transfer" and d.get("custom_updated_rate"):
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

    def update_valuation_rate(self):
        """
        Override to ensure that for Material Transfer items with custom_updated_rate,
        additional costs are ignored and amount/valuation_rate reflect the custom rate.
        """
        # First run the original logic (which may set additional_cost)
        super().update_valuation_rate()

        if self.purpose == "Material Transfer":
            for d in self.get("items"):
                if d.get("custom_updated_rate"):
                    # Remove any distributed additional costs and recompute
                    d.additional_cost = 0.0
                    d.amount = flt(d.basic_amount, d.precision("amount"))
                    d.valuation_rate = d.basic_rate