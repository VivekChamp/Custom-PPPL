// Copyright (c) 2025, vivekchamp84@gmail.com and contributors
// For license information, please see license.txt

frappe.query_reports["Sales Dashboard"] = {
    "filters": [
        {
            fieldname: "period",
            label: __("Period"),
            fieldtype: "Select",
            options: [
                "Monthly",
                "Quarterly",
                "Half Yearly",
                "Yearly",
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
        },
        {
            fieldname: "branch",
            label: __("Branch"),
            fieldtype: "MultiSelectList",
            hidden:1,
            get_data: function(txt) { return frappe.db.get_link_options("Branch", txt); }
        },
        {
            fieldname: "warehouse",
            label: __("Warehouse"),
            fieldtype: "MultiSelectList",
            hidden:1,
            get_data: function(txt) { return frappe.db.get_link_options("Warehouse", txt); }
        },
        {
            fieldname: "brand",
            label: __("Brand"),
            fieldtype: "MultiSelectList",
            hidden:1,
            get_data: function(txt) { return frappe.db.get_link_options("Brand", txt); }
        },
        {
            fieldname: "customer_group",
            label: __("Customer Group"),
            fieldtype: "MultiSelectList",
            hidden:1,
            get_data: function(txt) { return frappe.db.get_link_options("Customer Group", txt); }
        },
        {
            fieldname: "item_group",
            label: __("Item Group"),
            hidden:1,
            fieldtype: "MultiSelectList",
            get_data: function(txt) { return frappe.db.get_link_options("Item Group", txt); }
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "MultiSelectList",
            hidden:1,
            get_data: function(txt) { return frappe.db.get_link_options("Customer", txt); }
        },
        {
            fieldname: "sales_person",
            label: __("Sales Person"),
            fieldtype: "MultiSelectList",
            hidden:1,
            get_data: function(txt) { return frappe.db.get_link_options("Sales Person", txt); }
        }
    ],

};

