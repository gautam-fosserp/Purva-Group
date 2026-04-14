import frappe
from frappe.utils import flt
from frappe import _
from frappe.utils.user import get_users_with_role
from frappe.utils import get_formatted_email

from erpnext.selling.doctype.customer.customer import (
    get_customer_outstanding,
    get_credit_limit,
)


def check_credit_limit(customer, company, ignore_outstanding_sales_order=False, extra_amount=0):
    
    parent_company = frappe.db.get_value("Company", company, "parent_company")
    group_company = parent_company or company
    customer_group = frappe.db.get_value("Customer", customer, "customer_group")
    customers = frappe.get_all(
        "Customer",
        filters={"customer_group": customer_group},
        pluck="name"
    )

    credit_limit = get_credit_limit(customer, group_company)

    if not credit_limit:
        return

    if parent_company:
        companies = frappe.get_all(
            "Company",
            filters={"parent_company": group_company},
            pluck="name"
        )
        companies.append(group_company)
    else:
        companies = [company]

    customer_outstanding = 0

    for cust in customers:
        for comp in companies:
            customer_outstanding += flt(
                get_customer_outstanding(
                    cust,
                    comp,
                    ignore_outstanding_sales_order
                )
            )

    # Add current transaction value
    if extra_amount > 0:
        customer_outstanding += flt(extra_amount)

    if credit_limit > 0 and flt(customer_outstanding) > credit_limit:

        message = _("Credit limit has been crossed for Customer Group {0} ({1}/{2})").format(
            customer_group, customer_outstanding, credit_limit
        )

        message += "<br><br>"

        message += _(
            "Please contact your Accounts Team to extend the credit limit for Customer Group {0}."
        ).format(customer_group)

        frappe.throw(
            message,
            title=_("Credit Limit Crossed")
        )
        