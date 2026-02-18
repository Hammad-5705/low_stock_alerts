import frappe  
  
def validate(doc):  
    if doc.is_active and not doc.recipient_email:  
        frappe.throw("Recipient Email is required when Active")  
  
def on_update(doc):  
    if doc.is_active and not doc.warehouses:  
        frappe.throw("At least one warehouse must be added when Active")