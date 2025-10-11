# Copyright (c) 2025, vivekchamp84@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from frappe.utils import get_first_day, get_last_day, add_months, add_years, getdate, add_days
from frappe.utils import getdate
from frappe.utils.data import get_last_day
from erpnext.accounts.utils import get_fiscal_year
import datetime


def execute(filters=None):
	filters = filters or {}
	today = getdate(frappe.utils.today())
	period = filters.get("period")

	# Get current fiscal year based on today
	fy_info = get_fiscal_year(today)
	fy_start = getdate(fy_info[1])
	fy_end = getdate(fy_info[2])

	from_date, to_date = None, None

	if period == "Monthly":
		from_date = get_first_day(today)
		to_date = get_last_day(today)

	elif period == "Quarterly":
		quarter_start_month = ((today.month - 1) // 3) * 3 + 1
		from_date = getdate(f"{today.year}-{quarter_start_month:02d}-01")
		to_date = get_last_day(add_months(from_date, 2))

	elif period == "Half Yearly":
		fy_half_1_start = fy_start
		fy_half_1_end = add_months(fy_start, 6)  # 6 months after FY start
		fy_half_1_end = add_days(fy_half_1_end, -1)  # end of first half
		fy_half_2_start = fy_half_1_end + datetime.timedelta(days=1)
		fy_half_2_end = fy_end

		if fy_half_1_start <= today <= fy_half_1_end:
			from_date = fy_half_1_start
			to_date = fy_half_1_end
		else:
			from_date = fy_half_2_start
			to_date = fy_half_2_end

	elif period == "Yearly":
		from_date = fy_start
		to_date = fy_end

	else:
		from_date = getdate(filters.get("from_date")) if filters.get("from_date") else fy_start
		to_date = getdate(filters.get("to_date")) if filters.get("to_date") else fy_end

	from_date = getdate(from_date)
	to_date = getdate(to_date)

	if from_date < fy_start:
		from_date = fy_start
	if to_date > fy_end:
		to_date = fy_end

	prev_from_date = add_years(from_date, -1)
	prev_to_date = add_years(to_date, -1)


	def get_child_groups(parent_name):
		parent = frappe.db.get_value("Item Group", parent_name, ["lft", "rgt"], as_dict=True)
		if not parent:
			return [parent_name]
		
		groups = frappe.get_all(
			"Item Group",
			filters={"lft": (">=", parent.lft), "rgt": ("<=", parent.rgt)},
			pluck="name"
		)
		
		if parent_name not in groups:
			groups.append(parent_name)
		
		return groups

	def get_sales(from_dt, to_dt, item_group=None, uom=None, customer_group=None, without_tax=False):
		amount_field = "sii.rate * sii.qty" if without_tax else "sii.base_net_amount"

		conditions = []
		params = []

		if item_group:
			placeholders = ", ".join(["%s"] * len(item_group))
			conditions.append(f"sii.item_group IN ({placeholders})")
			params.extend(item_group)

		if uom:
			conditions.append("sii.uom = %s")
			params.append(uom)

		if customer_group:
			conditions.append("c.customer_group = %s")
			params.append(customer_group)

		if from_dt and to_dt:
			conditions.append("si.posting_date BETWEEN %s AND %s")
			params.extend([from_dt, to_dt])

		cond_sql = ""
		if conditions:
			cond_sql = "AND " + " AND ".join(conditions)

		query = f"""
			SELECT IFNULL(SUM(
				CASE 
					WHEN si.is_return = 0 THEN {amount_field}
					WHEN si.is_return = 1 THEN -1 * ABS({amount_field})
				END
			), 0)
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
			INNER JOIN `tabCustomer` c ON c.name = si.customer
			WHERE si.docstatus = 1
			{cond_sql}
		"""
		return frappe.db.sql(query, tuple(params))[0][0] or 0

	def get_qty(item_group=None, uom=None, customer_group=None, from_dt=None, to_dt=None):
		conditions = []
		params = []

		if item_group:
			placeholders = ", ".join(["%s"] * len(item_group))
			conditions.append(f"sii.item_group IN ({placeholders})")
			params.extend(item_group)

		if uom:
			conditions.append("sii.uom = %s")
			params.append(uom)

		if customer_group:
			conditions.append("c.customer_group = %s")
			params.append(customer_group)

		if from_dt and to_dt:
			conditions.append("si.posting_date BETWEEN %s AND %s")
			params.extend([from_dt, to_dt])

		cond_sql = ""
		if conditions:
			cond_sql = "AND " + " AND ".join(conditions)

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
			WHERE si.docstatus = 1
			{cond_sql}
		"""
		return frappe.db.sql(query, tuple(params))[0][0] or 0

	def get_net_sales_total(from_dt, to_dt):
		sales = frappe.db.sql("""
			SELECT IFNULL(SUM(base_net_total), 0)
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND is_return = 0 AND posting_date BETWEEN %s AND %s
		""", (from_dt, to_dt))[0][0] or 0

		returns = frappe.db.sql("""
			SELECT IFNULL(SUM(ABS(base_net_total)), 0)
			FROM `tabSales Invoice`
			WHERE docstatus = 1 AND is_return = 1 AND posting_date BETWEEN %s AND %s
		""", (from_dt, to_dt))[0][0] or 0

		return sales - returns

	net_sales = get_net_sales_total(from_date, to_date)
	prev_net_sales = get_net_sales_total(prev_from_date, prev_to_date)

	item_cards = [
		{"label": "Tyre (Nos)", "group": "TYRE", "uom": "Nos", "type": "qty"},
		{"label": "Tipper (Nos)", "group": "TIPPER", "uom": "Nos", "type": "qty"},
		{"label": "Non Tipper (Nos)", "group": "Non TIPPER", "uom": "Nos", "type": "qty"},
		{"label": "Tyre (Kg)", "group": "TYRE", "uom": "Kg", "type": "qty"},
		{"label": "Pumps (Nos)", "group": "PUMPS", "uom": "Nos", "type": "qty"},
		{"label": "Sales VCL (Litre)", "group": ["VCL"], "uom": "Litre", "customer_group": None, "type": "sales"},
		{"label": "BKT - Dealer - SAS", "group": None, "uom": None, "customer_group": "BKT - Dealer - SAS", "type": "sales"},
		{"label": "BKT - Customer", "group": None, "uom": None, "customer_group": "BKT - Customer", "type": "sales"},
		{"label": "BKT - Distributor", "group": None, "uom": None, "customer_group": "BKT - Distributor", "type": "sales"},
		{"label": "Tyre Qty BKT - Dealer - SAS (Nos)", "group": ["TYRE"], "uom": "Nos", "customer_group": "BKT - Dealer - SAS", "type": "qty"},
		{"label": "Tyre Qty BKT - Customer (Nos)", "group": ["TYRE"], "uom": "Nos", "customer_group": "BKT - Customer", "type": "qty"},
		{"label": "Tyre Qty BKT - Distributor (Nos)", "group": ["TYRE"], "uom": "Nos", "customer_group": "BKT - Distributor", "type": "qty"},
	]

	card_values = []
	for card in item_cards:
		if isinstance(card.get("group"), list):
			groups = get_child_groups(card["group"][0]) if card.get("group") else None
		elif isinstance(card.get("group"), str):
			groups = get_child_groups(card["group"]) if card.get("group") else None
		else:
			groups = None

		if card["type"] == "sales":
			current_val = get_sales(from_date, to_date, groups, card.get("uom"), card.get("customer_group"))
			prev_val = get_sales(prev_from_date, prev_to_date, groups, card.get("uom"), card.get("customer_group"))
		else:
			current_val = get_qty(groups, card.get("uom"), card.get("customer_group"), from_date, to_date)
			prev_val = get_qty(groups, card.get("uom"), card.get("customer_group"), prev_from_date, prev_to_date)

		card_values.append({
			"label": card["label"],
			"current": current_val,
			"previous": prev_val
		})

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

	message_cards.append(f"""
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
	""")

	message_cards.append("<div style='display:flex;gap:20px;flex-wrap:wrap;'>")
	for card in card_values:
		message_cards.append(f"""
			<div style='{card_style}'>
				<h4 style='margin:0;font-size:14px;'>{card['label']} CY</h4>
				<h2 style='margin:5px 0 0 0;color:#28a745;font-size:24px;'>{frappe.format_value(card['current'], {"fieldtype": "Float"})}</h2>
				<h4 style='margin:10px 0 0 0;font-size:14px;'>{card['label']} LY</h4>
				<h2 style='margin:5px 0 0 0;color:#6c757d;font-size:24px;'>{frappe.format_value(card['previous'], {"fieldtype": "Float"})}</h2>
			</div>
		""")
	message_cards.append("</div>")

	message = "".join(message_cards)
	return [], [], message, None
