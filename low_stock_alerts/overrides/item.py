import frappe  
  
def validate_warehouse_for_reorder(doc, method):  
    """Override to allow 0 reorder qty with file logging"""  
    # Write to temp file to verify execution  
    with open("/tmp/override_execution.log", "a") as f:  
        f.write(f"Override called for Item: {doc.name} at {frappe.utils.now()}\n")  
      
    warehouse_material_request_type = []  
    _warehouse_before_save = frappe._dict()  
      
    if not doc.is_new() and doc._doc_before_save:  
        _warehouse_before_save = {  
            d.name: d.warehouse for d in doc._doc_before_save.get("reorder_levels") or []  
        }  
  
    for d in doc.get("reorder_levels"):  
        if not d.warehouse_group:  
            d.warehouse_group = d.warehouse  
              
        # Check for duplicate warehouse entries  
        if (d.get("warehouse"), d.get("material_request_type")) not in warehouse_material_request_type:  
            warehouse_material_request_type += [(d.get("warehouse"), d.get("material_request_type"))]  
        else:  
            frappe.throw(  
                _("Row #{0}: A reorder entry already exists for warehouse {1} with reorder type {2}.").format(  
                    d.idx, d.warehouse, d.material_request_type  
                ),  
                frappe.DuplicateReorderRows,  
            )  
  
        # SKIP: Original reorder qty validation that blocks 0 values  
        # Original: if d.warehouse_reorder_level and not d.warehouse_reorder_qty:  
        # Original:     frappe.throw(_("Row #{0}: Please set reorder quantity").format(d.idx))  
  
        # Validate warehouse group relationships  
        if d.warehouse_group and d.warehouse:  
            if _warehouse_before_save.get(d.name) == d.warehouse:  
                continue  
  
            from erpnext.stock.utils import get_child_warehouses  
            child_warehouses = get_child_warehouses(d.warehouse_group)  
            if d.warehouse not in child_warehouses:  
                frappe.throw(  
                    _("Row #{0}: The warehouse {1} is not a child warehouse of a group warehouse {2}").format(  
                        d.idx, frappe.bold(d.warehouse), frappe.bold(d.warehouse_group)  
                    ),  
                    title=_("Incorrect Check in (group) Warehouse for Reorder"),  
                )