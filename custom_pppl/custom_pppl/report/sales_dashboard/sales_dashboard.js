// Copyright (c) 2025, vivekchamp84@gmail.com and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Dashboard"] = {
    "filters": [
        {
            fieldname: "period",
            label: __("Period"),
            fieldtype: "Select",
            options: [
                "Current Month",
                "Current Quarter",
                "Current Half-Year",
                "Current Year",
                "Date Range"
            ],
            default: "Yearly",
            reqd: 1,
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        }
    ],

};

