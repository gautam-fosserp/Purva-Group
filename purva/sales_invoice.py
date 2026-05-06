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
	"""Return actual available qty for a batch in a specific warehouse via SLE.

	ERPNext stores batch_no directly on the SLE only when use_serial_batch_fields=1.
	When a Serial and Batch Bundle is used, the SLE has batch_no=NULL and links via
	serial_and_batch_bundle. We cover both cases with a UNION.
	"""
	result = frappe.db.sql(
		"""
		SELECT SUM(actual_qty) FROM (

			-- direct batch_no on SLE (use_serial_batch_fields = 1)
			SELECT actual_qty
			FROM `tabStock Ledger Entry`
			WHERE item_code = %s
			  AND warehouse = %s
			  AND batch_no = %s
			  AND is_cancelled = 0

			UNION ALL

			-- bundle-based: use sbe.qty (per-batch qty) not sle.actual_qty (total for all batches)
			SELECT sbe.qty AS actual_qty
			FROM `tabStock Ledger Entry` sle
			JOIN `tabSerial and Batch Entry` sbe ON sbe.parent = sle.serial_and_batch_bundle
			WHERE sle.item_code = %s
			  AND sle.warehouse = %s
			  AND sle.is_cancelled = 0
			  AND sbe.batch_no = %s
			  AND (sbe.item_code = %s OR sbe.item_code IS NULL OR sbe.item_code = '')

		) combined
		""",
		(item_code, warehouse, batch_no, item_code, warehouse, batch_no, item_code),
	)
	return result[0][0] or 0


@frappe.whitelist()
def create_inventory_adjustment(invoice_name: str) -> dict:
	source = frappe.get_doc("Sales Invoice", invoice_name)

	items = []

	for row in source.items:

		if not frappe.db.get_value("Item", row.item_code, "is_stock_item"):
			continue

		if row.use_serial_batch_fields:
			if not row.batch_no:
				continue
			batch_qty = _get_batch_qty_in_warehouse(row.item_code, row.warehouse, row.batch_no)
			shortage = (row.qty or 0) - batch_qty
			if shortage <= 0:
				continue
			items.append({
				"item_code": row.item_code,
				"item_name": row.item_name,
				"description": row.description,
				"qty": shortage,
				"uom": row.uom,
				"warehouse": row.warehouse,
				"batch_no": row.batch_no,
				"custom_batch_make": row.custom_batch_make,
			})
		else:
			if not row.serial_and_batch_bundle:
				continue
			bundle_batches = frappe.get_all(
				"Serial and Batch Entry",
				filters={"parent": row.serial_and_batch_bundle},
				fields=["batch_no", "qty", "item_code"],
			)
			for batch in bundle_batches:
				if not batch.batch_no:
					continue
				ic = batch.item_code or row.item_code
				available_qty = _get_batch_qty_in_warehouse(ic, row.warehouse, batch.batch_no)
				# outward bundle entries store qty as negative; abs() gives the invoiced qty
				batch_invoice_qty = abs(batch.qty or 0)
				shortage = batch_invoice_qty - available_qty
				if shortage <= 0:
					continue
				items.append({
					"item_code": ic,
					"item_name": row.item_name,
					"description": row.description,
					"qty": shortage,
					"uom": row.uom,
					"warehouse": row.warehouse,
					"batch_no": batch.batch_no,
					"custom_batch_make": row.custom_batch_make,
				})

	return {
		"company": source.company,
		"cost_center": source.cost_center,
		"items": items,
	}
