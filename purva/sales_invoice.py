import frappe


@frappe.whitelist()
def fetch_actual_qty(warehouse: str, item_code: str = None, batch_no: str = None, serial_and_batch_bundle: str = None) -> float:
	"""Return available qty for a batch/bundle scoped to the given warehouse only."""
	total = 0.0

	if batch_no and item_code:
		total = _get_batch_qty_in_warehouse(item_code, warehouse, batch_no)
	elif serial_and_batch_bundle:
		bundle_batches = frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": serial_and_batch_bundle},
			fields=["batch_no", "item_code"],
		)
		for b in bundle_batches:
			if not b.batch_no:
				continue
			ic = b.item_code or item_code
			if ic:
				total += _get_batch_qty_in_warehouse(ic, warehouse, b.batch_no)

	return total


def _get_batch_qty_in_warehouse(item_code: str, warehouse: str, batch_no: str) -> float:
	"""Return actual available qty for a batch in a specific warehouse via SLE."""
	result = frappe.db.sql(
		"""
		SELECT SUM(actual_qty)
		FROM `tabStock Ledger Entry`
		WHERE item_code = %s
		  AND warehouse = %s
		  AND batch_no = %s
		  AND is_cancelled = 0
		""",
		(item_code, warehouse, batch_no),
	)
	return result[0][0] or 0


@frappe.whitelist()
def create_inventory_adjustment(invoice_name: str) -> dict:
	source = frappe.get_doc("Sales Invoice", invoice_name)

	items = []

	for row in source.items:

		if not frappe.db.get_value("Item", row.item_code, "is_stock_item"):
			continue

		batch_qty = 0

		if row.use_serial_batch_fields:
			if row.batch_no:
				batch_qty = _get_batch_qty_in_warehouse(row.item_code, row.warehouse, row.batch_no)
		else:
			if row.serial_and_batch_bundle:
				bundle_batches = frappe.get_all(
					"Serial and Batch Entry",
					filters={"parent": row.serial_and_batch_bundle},
					fields=["batch_no"],
				)
				for batch in bundle_batches:
					if not batch.batch_no:
						continue
					batch_qty += _get_batch_qty_in_warehouse(row.item_code, row.warehouse, batch.batch_no)

		invoice_qty = row.qty or 0
		shortage = invoice_qty - batch_qty

		if shortage <= 0:
			continue

		items.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"description": row.description,
				"qty": shortage,
				"uom": row.uom,
				"warehouse": row.warehouse,
				"batch_no": row.batch_no,
				"serial_and_batch_bundle": row.serial_and_batch_bundle,
				"custom_batch_make": row.custom_batch_make,
			}
		)

	return {
		"company": source.company,
		"cost_center": source.cost_center,
		"items": items,
	}
