# api.py
import frappe
from frappe import _
from frappe.utils import flt, nowdate, now_datetime

# Shared config (overridden in tests or via hooks/config later)
monitored_warehouses = []


def on_sle_update(doc, method):
    """Event hook: called after each Stock Ledger Entry is created/updated."""
    if doc.docstatus == 1 and not doc.is_cancelled:
        frappe.enqueue(
            "low_stock_alerts.api.check_and_alert_low_stock",
            item_code=doc.item_code,
            warehouse=doc.warehouse,
            queue="short",
        )


def get_monitored_warehouses_for_leaf(leaf_warehouse):
    import low_stock_alerts.api as api

    monitored = api.monitored_warehouses or []
    if not monitored:
        return [leaf_warehouse]

    result = []
    leaf = frappe.db.get_value("Warehouse", leaf_warehouse, ["lft", "rgt"], as_dict=True)
    if not leaf:
        return [leaf_warehouse]

    for wh in monitored:
        is_group = frappe.db.get_value("Warehouse", wh, "is_group")
        if is_group:
            parent = frappe.db.get_value("Warehouse", wh, ["lft", "rgt"], as_dict=True)
            if parent and parent.lft <= leaf.lft and parent.rgt >= leaf.rgt:
                result.append(wh)
        elif leaf_warehouse == wh:
            result.append(wh)

    return result if result else [leaf_warehouse]


def _get_reorder_for_leaf(item_code, leaf_warehouse):
    return frappe.db.get_value(
        "Item Reorder",
        {"parent": item_code, "warehouse": leaf_warehouse},
        ["warehouse_reorder_level", "warehouse_reorder_qty"],
        as_dict=True,
    )


def check_and_alert_low_stock(item_code, warehouse):
    monitored = get_monitored_warehouses_for_leaf(warehouse)
    if not monitored:
        return

    # 🔥 IMPORTANT FIX: Reorder rules exist on LEAF warehouses, not group warehouses
    reorder = _get_reorder_for_leaf(item_code, warehouse)
    if not reorder or not reorder.warehouse_reorder_level:
        return

    projected_qty = flt(
        frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "projected_qty") or 0
    )

    if projected_qty > reorder.warehouse_reorder_level:
        return

    throttle_key = f"low_stock_alert:{item_code}:{warehouse}"
    if frappe.cache().get_value(throttle_key):
        return

    frappe.cache().set_value(throttle_key, now_datetime(), expires_in_sec=3600)

    item_payload = {
        "item_code": item_code,
        "item_name": frappe.db.get_value("Item", item_code, "item_name"),
        "description": frappe.db.get_value("Item", item_code, "description"),
        "warehouse": warehouse,
        "projected_qty": projected_qty,
        "reorder_level": reorder.warehouse_reorder_level,
        "reorder_qty": reorder.warehouse_reorder_qty,
    }

    # Send to each monitored parent/group or leaf
    for monitored_name in monitored:
        recipient = frappe.db.get_value("Warehouse", monitored_name, "email_id")
        if recipient:
            send_low_stock_email([item_payload], recipient, monitored_name)


def send_low_stock_email(items, recipient, warehouse_or_group):
    template = """
    <h2>Low Stock Alert - {{ warehouse }}</h2>
    <p>The following items are at or below reorder level under {{ warehouse }}:</p>
    <table border="1" cellpadding="5" cellspacing="0">
        <tr>
            <th>Item Code</th>
            <th>Item Name</th>
            <th>Leaf Warehouse</th>
            <th>Projected Qty</th>
            <th>Reorder Level</th>
        </tr>
        {% for item in items %}
        <tr>
            <td>{{ item.item_code }}</td>
            <td>{{ item.item_name }}</td>
            <td>{{ item.warehouse }}</td>
            <td>{{ item.projected_qty }}</td>
            <td>{{ item.reorder_level }}</td>
        </tr>
        {% endfor %}
    </table>
    """

    message = frappe.render_template(template, {"items": items, "warehouse": warehouse_or_group})
    print("SENDING EMAIL TO:", recipient)
    frappe.sendmail(
        recipients=recipient,
        subject=_("Low Stock Alert"),
        message=message,
        reference_doctype="User",
    )
    print("email sent", recipient)


def run_low_stock_alerts_fallback(debug=None):
    """Hourly fallback: scan all enabled leaf warehouses and send alerts."""
    warehouses = frappe.get_all(
        "Warehouse", fields=["name", "email_id"], filters={"disabled": 0, "is_group": 0}
    )
    print("warehouses:", warehouses) 
    if not warehouses:
        return

    placeholders = ", ".join(["%s"] * len(warehouses))
    reorder_data = frappe.db.sql(
        f"""
        SELECT
            ir.parent as item_code,
            i.item_name,
            i.description,
            ir.warehouse,
            ir.warehouse_reorder_level,
            ir.warehouse_reorder_qty
        FROM `tabItem Reorder` ir
        INNER JOIN `tabItem` i ON i.name = ir.parent
        WHERE
            i.disabled = 0
            AND i.is_stock_item = 1
            AND (i.end_of_life IS NULL OR i.end_of_life > %s OR i.end_of_life = '0000-00-00')
            AND ir.warehouse IN ({placeholders})
        """,
        (nowdate(), *[w.name for w in warehouses]),
        as_dict=True,
    )

    low_stock_by_warehouse = {}
    for d in reorder_data:
        projected_qty = flt(
            frappe.db.get_value("Bin", {"item_code": d.item_code, "warehouse": d.warehouse}, "projected_qty") or 0
        )
        if d.warehouse_reorder_level and projected_qty <= d.warehouse_reorder_level:
            low_stock_by_warehouse.setdefault(d.warehouse, []).append({
                "item_code": d.item_code,
                "item_name": d.item_name,
                "description": d.description,
                "warehouse": d.warehouse,
                "projected_qty": projected_qty,
                "reorder_level": d.warehouse_reorder_level,
                "reorder_qty": d.warehouse_reorder_qty,
            })

    print("low_stock_by_warehouse:", low_stock_by_warehouse) 
    for wh in warehouses:
        items = low_stock_by_warehouse.get(wh.name)
        print(f"Warehouse {wh.name}: email_id={wh.email_id}, items={items}") 
        if items and wh.email_id:
            send_low_stock_email(items, wh.email_id, wh.name)
