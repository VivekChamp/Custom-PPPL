# Copyright (c) 2026, vivekchamp84@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_data(filters):
    filters = filters or {}

    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.get("company")
    branch = filters.get("branch")

    sql_conditions = []
    sql_values = {}

    if from_date:
        sql_conditions.append("si.posting_date >= %(from_date)s")
        sql_values["from_date"] = from_date

    if to_date:
        sql_conditions.append("si.posting_date <= %(to_date)s")
        sql_values["to_date"] = to_date

    if company:
        sql_conditions.append("si.company = %(company)s")
        sql_values["company"] = company

    if branch:
        sql_conditions.append("si.branch = %(branch)s")
        sql_values["branch"] = branch

    sql_where = ""
    if sql_conditions:
        sql_where = " AND " + " AND ".join(sql_conditions)

    sql = f"""

    SELECT
        t.sales_invoice,
        t.selling_price_list,
        t.docstatus,
        t.customer_group,
        t.party,
        t.invoice_date,
        t.total,
        t.net_total,
        t.rounded_total,
        t.invoice_due_date,
        t.additional_discount_percentage,
        t.discount_amount,
        t.additional_discount_account,
        t.account_currency,
        t.outstanding_amount,

        t.doctype,
        t.payment_id,
        t.journal_id,
        t.payment_date,
        t.party_type,
        t.mode_of_payment,
        t.paid_amount,
        t.allocated,
        t.reference_no,
        t.reference_date,
        t.owner,
        t.age_in_days,
       
        @running_paid := IF(@prev_invoice = t.sales_invoice,
                            @running_paid + IFNULL(t.allocated,0),
                            IFNULL(t.allocated,0)
                        ) AS cumulative_paid,

        @balance := t.rounded_total - @running_paid AS balance,

        @prev_invoice := t.sales_invoice

    FROM
    (
        -- PAYMENT ENTRY --
        SELECT
            si.name AS sales_invoice,
            si.selling_price_list,
            si.docstatus,
            si.customer_group,
            si.customer AS party,
            si.posting_date AS invoice_date,
            si.total,
            si.net_total,
            si.rounded_total,
            si.due_date AS invoice_due_date,
            si.additional_discount_percentage,
            si.discount_amount,
            si.additional_discount_account,
            si.currency AS account_currency,
            si.outstanding_amount,

            'Payment Entry' AS doctype,
            pe.name AS payment_id,
            NULL AS journal_id,
            pe.posting_date AS payment_date,
            pe.party_type,
            pe.mode_of_payment,
            per.allocated_amount AS paid_amount,
            per.allocated_amount AS allocated,
            pe.reference_no,
            pe.reference_date,
            pe.owner,

            DATEDIFF(pe.posting_date, si.posting_date ) AS age_in_days


        FROM `tabSales Invoice` si
        INNER JOIN `tabPayment Entry Reference` per
            ON per.reference_name = si.name
            AND per.reference_doctype = 'Sales Invoice'
        INNER JOIN `tabPayment Entry` pe
            ON pe.name = per.parent
            AND pe.docstatus = 1

        WHERE si.docstatus = 1
        {sql_where}

        UNION ALL

        -- JOURNAL ENTRY --
        SELECT
            si.name AS sales_invoice,
            si.selling_price_list,
            si.docstatus,
            si.customer_group,
            si.customer AS party,
            si.posting_date AS invoice_date,
            si.total,
            si.net_total,
            si.rounded_total,
            si.due_date AS invoice_due_date,
            si.additional_discount_percentage,
            si.discount_amount,
            si.additional_discount_account,
            si.currency AS account_currency,
            si.outstanding_amount,

            'Journal Entry' AS doctype,
            NULL AS payment_id,
            je.name AS journal_id,
            je.posting_date AS payment_date,
            jea.party_type,
            NULL AS mode_of_payment,
            IFNULL(jea.credit_in_account_currency, jea.credit) AS paid_amount,
            IFNULL(jea.credit_in_account_currency, jea.credit) AS allocated,
            je.cheque_no AS reference_no,
            je.cheque_date AS reference_date,
            je.owner,
            DATEDIFF(je.posting_date, si.posting_date ) AS age_in_days

        FROM `tabSales Invoice` si
        INNER JOIN `tabJournal Entry Account` jea
            ON jea.reference_name = si.name
            AND jea.reference_type = 'Sales Invoice'
        INNER JOIN `tabJournal Entry` je
            ON je.name = jea.parent
            AND je.docstatus = 1

        WHERE si.docstatus = 1
        {sql_where}

    ) t,

    (SELECT @running_paid := 0, @prev_invoice := '') vars

    ORDER BY t.sales_invoice, t.payment_date
    """

    return frappe.db.sql(sql, sql_values, as_dict=True)


def get_columns():
    columns = [
        {
			"fieldname": "sales_invoice",
			"label": "Sales Invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 160,
		},
        {
            "fieldname": "docstatus", 
            "label": "Doc Status", 
            "fieldtype": "Int", 
            "width": 90
        },
        {
			"fieldname": "doctype",
			"label": "Doctype",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "payment_id",
			"label": "Payment Entry",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 160,
		},
		{
			"fieldname": "journal_id",
			"label": "Journal Entry",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 160,
		},
        {
            "fieldname": "payment_date", 
            "label": "Payment Date", 
            "fieldtype": "Date", 
            "width": 120
        },
        {
            "fieldname": "mode_of_payment", 
            "label": "Mode of Payment", 
            "fieldtype": "Link", 
            "options": "Mode of Payment", 
            "width": 140
        },
        {
            "fieldname": "reference_no", 
            "label": "Cheque/Reference No", 
            "fieldtype": "Data", 
            "width": 140
        },
        {
            "fieldname": "reference_date", 
            "label": "Cheque/Reference Date", 
            "fieldtype": "Date", 
            "width": 140
        },
        {
            "fieldname": "party_type", 
            "label": "Party Type", 
            "fieldtype": "Data", 
            "width": 110
        },
        {
            "fieldname": "party", 
            "label": "Party", 
            "fieldtype": "Link", 
            "options": "Customer", 
            "width": 180
        },
        {
            "fieldname": "customer_group", 
            "label": "Customer Group", 
            "fieldtype": "Link", 
            "options": "Customer Group", 
            "width": 140
        },
        {
            "fieldname": "paid_amount", 
            "label": "Paid Amount", 
            "fieldtype": "Currency", 
            "width": 130
        },
        {
            "fieldname": "account_currency", 
            "label": "Account Currency (From)", 
            "fieldtype": "Data", 
            "width": 120
        },
        {
            "fieldname": "invoice_due_date", 
            "label": "Invoice Due Date", 
            "fieldtype": "Date", 
            "width": 140
        },
        {
            "fieldname": "invoice_date", 
            "label": "Invoice Date", 
            "fieldtype": "Date", 
            "width": 120
        },
        {
            "fieldname": "total", 
            "label": "Total", 
            "fieldtype": "Currency", 
            "width": 120
        },
        {
            "fieldname": "net_total", 
            "label": "Net Total", 
            "fieldtype": "Currency", 
            "width": 120
        },
        {
            "fieldname": "outstanding_amount", 
            "label": "Total Outstanding", 
            "fieldtype": "Currency", 
            "width": 120
        },
        {
            "fieldname": "rounded_total", 
            "label": "Round Total", 
            "fieldtype": "Currency", 
            "width": 120
        },
        {
            "fieldname": "allocated", 
            "label": "Allocated", 
            "fieldtype": "Currency", 
            "width": 120
        },
        {
            "fieldname": "balance", 
            "label": "Bal", 
            "fieldtype": "Currency", ""
            "width": 100
        },
        {
            "fieldname": "owner", 
            "label": "Owner", 
            "fieldtype": "Data", 
            "width": 180
        },
        {
            "fieldname": "age_in_days", 
            "label": "Age in Days", 
            "fieldtype": "Int", 
            "width": 110
        },
        {
            "fieldname": "additional_discount_account", 
            "label": "Discount Account", 
            "fieldtype": "Link", 
            "options": "Account",
            "width": 180
        },
        {
            "fieldname": "additional_discount_percentage", 
            "label": "Additional Discount Percentage", 
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "discount_amount", 
            "label": "Additional Discount Amount", 
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "fieldname": "selling_price_list", 
            "label": "Price List", 
            "fieldtype": "Link", 
            "options": "Price List",
            "width": 180
        },
        
    ]
    return columns

