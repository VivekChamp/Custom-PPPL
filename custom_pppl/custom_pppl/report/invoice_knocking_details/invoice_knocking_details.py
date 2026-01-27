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

   
    sql_where = ""
    if sql_conditions:
        sql_where = " AND " + " AND ".join(sql_conditions)

    payment_entry_sql = f"""
        SELECT 
            'Payment Entry' AS payment_document,
            pe.name AS id,
            pe.docstatus,
            pe.payment_type,
            pe.posting_date AS payment_date,
            pe.mode_of_payment,
            pe.party_type,
            pe.party,
            pe.paid_amount,
            pe.paid_from_account_currency AS account_currency,
            
            per.reference_doctype AS reference_type,
            per.reference_name AS sales_invoice,
            
            si.posting_date AS invoice_date,
            si.due_date AS invoice_due_date,
            
            per.outstanding_amount AS outstanding,
            per.allocated_amount AS allocated,
            
            CASE 
                WHEN IFNULL(per.outstanding_amount,0) <= 0 THEN 0
                WHEN IFNULL(per.outstanding_amount,0) <= IFNULL(per.allocated_amount,0) THEN 0
                ELSE IFNULL(per.outstanding_amount,0) - IFNULL(per.allocated_amount,0)
            END AS balance,
            
            pe.owner,
            
            ABS(DATEDIFF(pe.posting_date, IFNULL(si.posting_date, pe.posting_date))) AS age_in_days

        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per
            ON per.parent = pe.name
        LEFT JOIN `tabSales Invoice` si
            ON si.name = per.reference_name
        WHERE 
            pe.docstatus = 1
            AND per.reference_doctype = 'Sales Invoice'
            {sql_where};
    """

    journal_entry_sql = f"""
        SELECT 
            'Journal Entry' AS payment_document,
            je.name AS id,
            je.docstatus,
            je.voucher_type AS payment_type,
            je.posting_date AS payment_date,
            je.mode_of_payment,
            'Customer' AS party_type,
            jea.party,
            jea.debit_in_account_currency AS paid_amount,
            jea.account_currency,
            
            jea.reference_type,
            jea.reference_name AS sales_invoice,
            
            si.posting_date AS invoice_date,
            si.due_date AS invoice_due_date,
            
            si.outstanding_amount AS outstanding,
            jea.debit_in_account_currency AS allocated,
            
            CASE 
                WHEN IFNULL(si.outstanding_amount,0) <= 0 THEN 0
                WHEN IFNULL(si.outstanding_amount,0) <= IFNULL(jea.debit_in_account_currency,0) THEN 0
                ELSE IFNULL(si.outstanding_amount,0) - IFNULL(jea.debit_in_account_currency,0)
            END AS balance,
            
            je.owner,
            
            ABS(DATEDIFF(je.posting_date, IFNULL(si.posting_date, je.posting_date))) AS age_in_days

        FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` jea
            ON jea.parent = je.name
        LEFT JOIN `tabSales Invoice` si
            ON si.name = jea.reference_name
        WHERE 
            je.docstatus = 1
            AND jea.reference_type = 'Sales Invoice'
            {sql_where};
    """

    pe_data = frappe.db.sql(payment_entry_sql, sql_values, as_dict=True)
    je_data = frappe.db.sql(journal_entry_sql, sql_values, as_dict=True)

    data = pe_data + je_data
    return data

def get_columns():
    columns = [
        {
			"fieldname": "payment_document",
			"label": _("Payment Document Type"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "id",
			"label": _("ID"),
			"fieldtype": "Dynamic Link",
			"options": "payment_document",
			"width": 160,
		},
        {
            "fieldname": "docstatus", 
            "label": "Doc Status", 
            "fieldtype": "Int", 
            "width": 90
        },

        {
            "fieldname": "payment_type", 
            "label": "Payment Type - Receive & JV's", 
            "fieldtype": "Data", 
            "width": 160
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
            "fieldname": "reference_type", 
            "label": "Reference Type", 
            "fieldtype": "Data", 
            "width": 150
        },
        {
            "fieldname": "sales_invoice", 
            "label": "Sales Invoice", 
            "fieldtype": "Link", 
            "options": "Sales Invoice", 
            "width": 150
        },
        {
            "fieldname": "invoice_date", 
            "label": "Invoice Date", 
            "fieldtype": "Date", 
            "width": 120
        },
        {
            "fieldname": "invoice_due_date", 
            "label": "Invoice Due Date", 
            "fieldtype": "Date", 
            "width": 140
        },
        {
            "fieldname": "outstanding", 
            "label": "Outstanding", 
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
    ]
    return columns
