import base64

import fitz
import frappe


@frappe.whitelist()
def get_pdf_pages_as_images(file_url: str) -> list:
	if not file_url:
		return []

	try:
		file_doc = frappe.get_doc("File", {"file_url": file_url})
		file_path = file_doc.get_full_path()

		images = []
		pdf = fitz.open(file_path)

		for page_num in range(len(pdf)):
			page = pdf[page_num]
			mat = fitz.Matrix(2.0, 2.0)
			pix = page.get_pixmap(matrix=mat)
			img_data = pix.tobytes("png")
			b64 = base64.b64encode(img_data).decode("utf-8")
			images.append("data:image/png;base64," + b64)

		pdf.close()
		return images

	except Exception as e:
		frappe.log_error(str(e), "PDF to Image Error")
		return []
