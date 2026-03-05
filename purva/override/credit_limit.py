import frappe
from frappe.utils import flt


def get_company_group(company):

    company_doc = frappe.get_doc("Company", company)

    if company_doc.is_group:
        return company

    parent = company_doc.parent_company

    while parent:
        parent_doc = frappe.get_doc("Company", parent)

        if parent_doc.is_group:
            return parent

        parent = parent_doc.parent_company

    return company


def get_child_companies(company_group):

    group_doc = frappe.get_doc("Company", company_group)

    companies = frappe.get_all(
        "Company",
        filters={
            "lft": [">", group_doc.lft],
            "rgt": ["<", group_doc.rgt],
            "is_group": 0
        },
        pluck="name"
    )

    return companies


def get_credit_limit_from_customer_group(customer_group, company_group):

    return frappe.db.get_value(
        "Customer Credit Limit",
        {
            "parent": customer_group,
            "company": company_group
        },
        "credit_limit"
    )


def get_sales_invoice_outstanding(customer, companies):

    if not companies:
        return 0

    outstanding = frappe.db.sql(
        """
        SELECT SUM(outstanding_amount)
        FROM `tabSales Invoice`
        WHERE customer = %(customer)s
        AND company IN %(companies)s
        AND docstatus = 1
        """,
        {
            "customer": customer,
            "companies": tuple(companies)
        }
    )[0][0]

    return flt(outstanding)


def get_unbilled_sales_orders(customer, companies):

    if not companies:
        return 0

    orders = frappe.db.sql(
        """
        SELECT grand_total, per_billed
        FROM `tabSales Order`
        WHERE customer = %(customer)s
        AND company IN %(companies)s
        AND docstatus = 1
        AND per_billed < 100
        """,
        {
            "customer": customer,
            "companies": tuple(companies)
        },
        as_dict=True
    )

    total_unbilled = 0

    for d in orders:
        unbilled = flt(d.grand_total) * (100 - flt(d.per_billed)) / 100
        total_unbilled += unbilled

    return total_unbilled


def validate_group_credit_limit(doc, method):

    if not doc.customer or not doc.company:
        return

    customer = doc.customer
    company = doc.company

    company_group = get_company_group(company)

    customer_group = frappe.db.get_value(
        "Customer", customer, "customer_group"
    )

    credit_limit = get_credit_limit_from_customer_group(
        customer_group, company_group
    )

    if not credit_limit:
        return

    companies = get_child_companies(company_group)

    if not companies:
        companies = [company_group]

    invoice_outstanding = get_sales_invoice_outstanding(customer, companies)

    sales_order_outstanding = get_unbilled_sales_orders(customer, companies)

    total_outstanding = invoice_outstanding + sales_order_outstanding

    if doc.doctype in ["Sales Order", "Sales Invoice"]:
        total_outstanding += flt(doc.grand_total)

    if total_outstanding > flt(credit_limit):

        frappe.throw(
            f"""
<h3>Credit Limit Exceeded</h3>

Customer: <b>{customer}</b><br><br>

Invoice Outstanding: <b>{invoice_outstanding}</b><br>
Unbilled Sales Orders: <b>{sales_order_outstanding}</b><br>

Total Exposure: <b>{total_outstanding}</b><br>
Credit Limit (Group Company): <b>{credit_limit}</b>
"""
        )