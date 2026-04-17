import frappe
from frappe.utils import flt


def execute():
	"""
	Fix basic_amount and amount for finished items in Repack stock entries where
	set_basic_rate_manually=1 caused ERPNext to skip basic_amount calculation,
	leaving it as 0 despite a valid basic_rate.

	Affected entries: 27-RPE-AAB-00006, 27-RPE-AAB-00097
	Stock Ledger Entries are already correct — only display fields need fixing.
	"""
	affected_rows = [
		# (parent, row_name, transfer_qty, basic_rate)
		("27-RPE-AAB-00006", "0ep91h362p", 2250, 53.08),
		("27-RPE-AAB-00097", "3l3bkjjvq6", 1849, 59.43),
	]

	for parent, row_name, transfer_qty, basic_rate in affected_rows:
		basic_amount = flt(transfer_qty * basic_rate, 2)

		frappe.db.set_value(
			"Stock Entry Detail",
			row_name,
			{"basic_amount": basic_amount, "amount": basic_amount},
			update_modified=False,
		)

		# Recalculate header totals from all item rows
		rows = frappe.db.sql(
			"""
			SELECT t_warehouse, s_warehouse, amount
			FROM `tabStock Entry Detail`
			WHERE parent = %s
			""",
			parent,
			as_dict=True,
		)

		total_incoming = sum(flt(r.amount) for r in rows if r.t_warehouse)
		total_outgoing = sum(flt(r.amount) for r in rows if r.s_warehouse)

		frappe.db.set_value(
			"Stock Entry",
			parent,
			{
				"total_incoming_value": total_incoming,
				"total_outgoing_value": total_outgoing,
				"value_difference": total_incoming - total_outgoing,
			},
			update_modified=False,
		)

		frappe.logger().info(
			f"Fixed {parent}: row {row_name} basic_amount={basic_amount}, "
			f"total_incoming={total_incoming}, value_difference={total_incoming - total_outgoing}"
		)
