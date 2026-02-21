# Copyright (c) 2025, vivekchamp84@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from frappe.utils import (
    getdate,
    get_first_day,
    get_last_day,
    add_months,
    add_years,
    today,
)
from frappe.utils import getdate
from frappe.utils.data import get_last_day


def execute(filters=None):
    filters = filters or {}

    today_date = getdate(today())
    period = filters.get("period")

    year_start = getdate(f"{today_date.year}-01-01")
    year_end = getdate(f"{today_date.year}-12-31")

    if period == "Current Month":
        from_date = get_first_day(today_date)
        to_date = get_last_day(today_date)

    elif period == "Current Quarter":
        quarter_start_month = ((today_date.month - 1) // 3) * 3 + 1
        from_date = getdate(f"{today_date.year}-{quarter_start_month:02d}-01")
        to_date = get_last_day(add_months(from_date, 2))

    elif period == "Current Half-Year":
        if today_date.month <= 6:
            from_date = year_start
            to_date = getdate(f"{today_date.year}-06-30")
        else:
            from_date = getdate(f"{today_date.year}-07-01")
            to_date = year_end

    elif period == "Current Year":
        from_date = year_start
        to_date = year_end

    else:
        from_date = (
            getdate(filters.get("from_date"))
            if filters.get("from_date")
            else year_start
        )
        to_date = (
            getdate(filters.get("to_date")) if filters.get("to_date") else year_end
        )

    prev_from_date = add_years(from_date, -1)
    prev_to_date = add_years(to_date, -1)

    # Child Item Groups
    def get_child_groups(parent_name):
        parent = frappe.db.get_value(
            "Item Group", parent_name, ["lft", "rgt"], as_dict=True
        )
        if not parent:
            return [parent_name]

        groups = frappe.get_all(
            "Item Group",
            filters={"lft": (">=", parent.lft), "rgt": ("<=", parent.rgt)},
            pluck="name",
        )
        return groups

    # Base Filters Builder
    def build_conditions(
        from_dt, to_dt, item_group=None, uom=None, card_customer_group=None
    ):
        conditions = [
            "si.docstatus = 1",
            "si.is_return = 0",
            "c.customer_name NOT LIKE %s",
            "si.posting_date BETWEEN %s AND %s",
        ]
        params = ["%Parikh Power Private Limited%", from_dt, to_dt]

        # Report Filters
        if filters.get("branch"):
            conditions.append("si.branch = %s")
            params.append(filters["branch"])

        if filters.get("warehouse"):
            conditions.append("sii.warehouse = %s")
            params.append(filters["warehouse"])

        if filters.get("brand"):
            conditions.append("sii.brand = %s")
            params.append(filters["brand"])

        if filters.get("customer"):
            conditions.append("si.customer = %s")
            params.append(filters["customer"])

        if filters.get("sales_person"):
            conditions.append("st.sales_person = %s")
            params.append(filters["sales_person"])

        # Customer Group (Card-level priority)
        if card_customer_group:
            conditions.append("c.customer_group = %s")
            params.append(card_customer_group)
        elif filters.get("customer_group"):
            conditions.append("c.customer_group = %s")
            params.append(filters["customer_group"])

        
        if item_group:
            placeholders = ", ".join(["%s"] * len(item_group))
            conditions.append(f"sii.item_group IN ({placeholders})")
            params.extend(item_group)

        elif filters.get("item_group"):
            report_groups = get_child_groups(filters["item_group"])
            placeholders = ", ".join(["%s"] * len(report_groups))
            conditions.append(f"sii.item_group IN ({placeholders})")
            params.extend(report_groups)

        if uom:
            conditions.append("sii.uom = %s")
            params.append(uom)

        return conditions, params

    # Sales Amount
    def get_sales(from_dt, to_dt, item_group=None, uom=None, card_customer_group=None):
        conditions, params = build_conditions(
            from_dt, to_dt, item_group, uom, card_customer_group
        )

        query = f"""
			SELECT IFNULL(SUM(
				CASE 
					WHEN si.is_return = 0 THEN sii.base_net_amount
					WHEN si.is_return = 1 THEN -1 * ABS(sii.base_net_amount)
				END
			), 0)
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
			INNER JOIN `tabCustomer` c ON c.name = si.customer
			LEFT JOIN `tabSales Team` st ON st.parent = si.name
			WHERE {" AND ".join(conditions)}
		"""

        return frappe.db.sql(query, tuple(params))[0][0] or 0

    # Quantity
    def get_qty(from_dt, to_dt, item_group=None, uom=None, card_customer_group=None):
        conditions, params = build_conditions(
            from_dt, to_dt, item_group, uom, card_customer_group
        )

        query = f"""
			SELECT IFNULL(SUM(
				CASE 
					WHEN si.is_return = 0 THEN sii.qty
					WHEN si.is_return = 1 THEN -1 * ABS(sii.qty)
				END
			), 0)
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
			INNER JOIN `tabCustomer` c ON c.name = si.customer
			LEFT JOIN `tabSales Team` st ON st.parent = si.name
			WHERE {" AND ".join(conditions)}
		"""

        return frappe.db.sql(query, tuple(params))[0][0] or 0

    # Net Sales (Invoice level)
    def get_net_sales_total(from_dt, to_dt):

        conditions = [
            "si.docstatus = 1",
            "si.is_return = 0",
            "si.posting_date BETWEEN %s AND %s",
            "c.customer_name NOT LIKE %s",
        ]

        params = [from_dt, to_dt, "%Parikh Power Private Limited%"]

        # Report Filters

        if filters.get("branch"):
            conditions.append("si.branch = %s")
            params.append(filters["branch"])

        if filters.get("customer"):
            conditions.append("si.customer = %s")
            params.append(filters["customer"])

        if filters.get("customer_group"):
            conditions.append("c.customer_group = %s")
            params.append(filters["customer_group"])

        if filters.get("warehouse"):
            conditions.append("sii.warehouse = %s")
            params.append(filters["warehouse"])

        if filters.get("brand"):
            conditions.append("sii.brand = %s")
            params.append(filters["brand"])

        if filters.get("sales_person"):
            conditions.append("st.sales_person = %s")
            params.append(filters["sales_person"])

        # Item Group (with children)
        if filters.get("item_group"):
            groups = get_child_groups(filters["item_group"])
            placeholders = ", ".join(["%s"] * len(groups))
            conditions.append(f"sii.item_group IN ({placeholders})")
            params.extend(groups)

        query = f"""
			SELECT IFNULL(SUM(
				CASE 
					WHEN si.is_return = 0 THEN sii.base_net_amount
					WHEN si.is_return = 1 THEN -1 * ABS(sii.base_net_amount)
				END
			), 0)
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
			INNER JOIN `tabCustomer` c ON c.name = si.customer
			LEFT JOIN `tabSales Team` st ON st.parent = si.name
			WHERE {" AND ".join(conditions)}
		"""

        return frappe.db.sql(query, tuple(params))[0][0] or 0

    net_sales = get_net_sales_total(from_date, to_date)
    prev_net_sales = get_net_sales_total(prev_from_date, prev_to_date)

    # Item Cards
    item_cards = [
        {"label": "Tyre (Nos)", "group": "TYRE", "uom": "Nos", "type": "qty"},
        {"label": "Tipper (Nos)", "group": "TIPPER", "uom": "Nos", "type": "qty"},
        {
            "label": "Non Tipper (Nos)",
            "group": "Non TIPPER",
            "uom": "Nos",
            "type": "qty",
        },
        {"label": "Tyre (Kg)", "group": "TYRE", "uom": "Kg", "type": "qty"},
        {"label": "Pumps (Nos)", "group": "PUMPS", "uom": "Nos", "type": "qty"},
        {
            "label": "Sales VCL (Litre)",
            "group": ["VCL"],
            "uom": "Litre",
            "type": "sales",
        },
        {
            "label": "BKT - Dealer - SAS",
            "customer_group": "BKT - Dealer - SAS",
            "type": "sales",
        },
        {
            "label": "BKT - Customer",
            "customer_group": "BKT - Customer",
            "type": "sales",
        },
        {
            "label": "BKT - Distributor",
            "customer_group": "BKT - Distributor",
            "type": "sales",
        },
    ]

    card_values = []

    for card in item_cards:

        # HIDE CUSTOMER GROUP CARDS
        if filters.get("customer_group"):
            # If this card is customer-group based → hide it
            if card.get("customer_group"):
                continue

        # HIDE ITEM GROUP CARDS
        if filters.get("item_group"):
            # If this card is item-group based → hide it
            if card.get("group"):
                continue

        # Resolve Child Groups
        if isinstance(card.get("group"), list):
            groups = get_child_groups(card["group"][0])
        elif isinstance(card.get("group"), str):
            groups = get_child_groups(card["group"])
        else:
            groups = None

        # Fetch Values
        if card["type"] == "sales":
            current = get_sales(
                from_date, to_date, groups, card.get("uom"), card.get("customer_group")
            )
            previous = get_sales(
                prev_from_date,
                prev_to_date,
                groups,
                card.get("uom"),
                card.get("customer_group"),
            )
        else:
            current = get_qty(
                from_date, to_date, groups, card.get("uom"), card.get("customer_group")
            )
            previous = get_qty(
                prev_from_date,
                prev_to_date,
                groups,
                card.get("uom"),
                card.get("customer_group"),
            )

        card_values.append(
            {"label": card["label"], "current": current, "previous": previous}
        )
    card_style = """
		width: 280px;
		height: 160px;
		padding: 20px 25px;
		background: #f8f9fa;
		border-radius: 10px;
		box-shadow: 0 2px 5px rgba(0,0,0,0.15);
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		text-align: center;
	"""

    message_cards = []

    message_cards.append(
        f"""
		<div style='display:flex;gap:20px;flex-wrap:wrap;margin-bottom:20px;'>
			<div style='{card_style}'>
				<h4 style='margin:0;font-size:14px;'>Sales CY (₹)</h4>
				<h2 style='margin:5px 0 0 0;color:#007bff;font-size:24px;'>{frappe.format_value(net_sales, {"fieldtype": "Currency"})}</h2>
			</div>
			<div style='{card_style}'>
				<h4 style='margin:0;font-size:14px;'>Sales LY (₹)</h4>
				<h2 style='margin:5px 0 0 0;color:#6c757d;font-size:24px;'>{frappe.format_value(prev_net_sales, {"fieldtype": "Currency"})}</h2>
			</div>
		</div>
	"""
    )

    message_cards.append("<div style='display:flex;gap:20px;flex-wrap:wrap;'>")
    for card in card_values:
        message_cards.append(
            f"""
			<div style='{card_style}'>
				<h4 style='margin:0;font-size:14px;'>{card['label']} CY</h4>
				<h2 style='margin:5px 0 0 0;color:#28a745;font-size:24px;'>{frappe.format_value(card['current'], {"fieldtype": "Float"})}</h2>
				<h4 style='margin:10px 0 0 0;font-size:14px;'>{card['label']} LY</h4>
				<h2 style='margin:5px 0 0 0;color:#6c757d;font-size:24px;'>{frappe.format_value(card['previous'], {"fieldtype": "Float"})}</h2>
			</div>
		"""
        )
    message_cards.append("</div>")

    message = "".join(message_cards)

    return [], [], message, None
