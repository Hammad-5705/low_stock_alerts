# # low_stock_alerts/low_stock_alerts/tests/test_low_stock_alerts.py  
# import frappe  
# from frappe.tests import IntegrationTestCase  
# from frappe.utils import flt, nowdate  
# from unittest.mock import patch  
  
# # Use relative import at top level  
# from ..api import run_low_stock_alerts, send_low_stock_email  
  
# class TestLowStockAlerts(IntegrationTestCase):  
#     def setUp(self):  
#         # Create test company with unique abbreviation  
#         self.company = self.create_test_company()  
          
#         # Create test warehouse with unique name  
#         self.warehouse = frappe.get_doc({  
#             "doctype": "Warehouse",  
#             "warehouse_name": f"Test Low Stock WH {frappe.generate_hash(length=4)}",  
#             "company": self.company  
#         })  
#         self.warehouse.insert()  
  
#         # Create test item with required fields  
#         self.item = frappe.get_doc({  
#             "doctype": "Item",  
#             "item_code": f"_Test Low Stock Item {frappe.generate_hash(length=4)}",  
#             "item_name": "Test Low Stock Item",  
#             "is_stock_item": 1,  
#             "stock_uom": "Nos",  
#             "item_group": "Products"  
#         })  
#         self.item.insert()  
  
#         # Add reorder level (use minimal qty to avoid validation error)  
#         self.item.append("reorder_levels", {  
#             "warehouse": self.warehouse.name,  
#             "warehouse_reorder_level": 10,  
#             "warehouse_reorder_qty": 0.01,  
#             "material_request_type": "Purchase"  
#         })  
#         self.item.save()  
  
#         # Create Bin using ERPNext's API  
#         from erpnext.stock.utils import get_or_make_bin  
#         bin_name = get_or_make_bin(self.item.name, self.warehouse.name)  
          
#         # Update Bin quantities  
#         frappe.db.set_value("Bin", bin_name, {  
#             "projected_qty": 5,  
#             "actual_qty": 5  
#         })  
  
#     def create_test_company(self):  
#         """Create a test company with unique abbreviation"""  
#         hash_suffix = frappe.generate_hash(length=4)  
#         company_name = f"_Test Low Stock Company {hash_suffix}"  
#         abbr = f"_LSC{hash_suffix}"  
          
#         if frappe.db.exists("Company", company_name):  
#             return company_name  
              
#         company = frappe.get_doc({  
#             "doctype": "Company",  
#             "company_name": company_name,  
#             "country": "India",  
#             "default_currency": "INR",  
#             "create_chart_of_accounts_based_on": "Standard Template",  
#             "chart_of_accounts": "Standard"  
#         })  
#         company.insert()  
#         return company.name  
  
#     def tearDown(self):  
#         # Clean up in reverse order  
#         if hasattr(self, 'item'):  
#             frappe.delete_doc("Item", self.item.name)  
#         if hasattr(self, 'warehouse'):  
#             frappe.delete_doc("Warehouse", self.warehouse.name)  
#         if hasattr(self, 'company'):  
#             frappe.delete_doc("Company", self.company)  
#         frappe.db.rollback()  
  
#     @patch('frappe.sendmail')  
#     def test_run_low_stock_alerts_single_warehouse(self, mock_sendmail):  
#         """Test that only target warehouse triggers alert"""  
#         # Set up mock to capture emails  
#         outbox = []  
#         def capture_email(*args, **kwargs):  
#             outbox.append(kwargs)  
#         mock_sendmail.side_effect = capture_email  
          
#         # Override configuration for test  
#         original_target = getattr(run_low_stock_alerts.__globals__, 'target_warehouses', None)  
#         original_recipient = getattr(run_low_stock_alerts.__globals__, 'recipient_email', None)  
          
#         try:  
#             # Temporarily set test configuration  
#             run_low_stock_alerts.__globals__['target_warehouses'] = [self.warehouse.name]  
#             run_low_stock_alerts.__globals__['recipient_email'] = "test@example.com"  
              
#             run_low_stock_alerts()  
              
#             # Should have exactly one email  
#             self.assertEqual(len(outbox), 1)  
#             email = outbox[0]  
#             self.assertIn("Low Stock Alert", email["subject"])  
#             self.assertIn(self.item.name, email["message"])  
#             self.assertIn(self.warehouse.name, email["message"])  
#         finally:  
#             # Restore original configuration  
#             if original_target is not None:  
#                 run_low_stock_alerts.__globals__['target_warehouses'] = original_target  
#             if original_recipient is not None:  
#                 run_low_stock_alerts.__globals__['recipient_email'] = original_recipient  
  
#     @patch('frappe.sendmail')  
#     def test_no_alert_when_above_reorder_level(self, mock_sendmail):  
#         """Test no alert when projected_qty > reorder_level"""  
#         # Set up mock to capture emails  
#         outbox = []  
#         def capture_email(*args, **kwargs):  
#             outbox.append(kwargs)  
#         mock_sendmail.side_effect = capture_email  
          
#         # Update stock to above reorder level  
#         bin_name = frappe.db.get_value("Bin", {"item_code": self.item.name, "warehouse": self.warehouse.name}, "name")  
#         frappe.db.set_value("Bin", bin_name, "projected_qty", 15)  
          
#         # Override configuration for test  
#         original_target = getattr(run_low_stock_alerts.__globals__, 'target_warehouses', None)  
#         original_recipient = getattr(run_low_stock_alerts.__globals__, 'recipient_email', None)  
          
#         try:  
#             run_low_stock_alerts.__globals__['target_warehouses'] = [self.warehouse.name]  
#             run_low_stock_alerts.__globals__['recipient_email'] = "test@example.com"  
              
#             run_low_stock_alerts()  
#             self.assertEqual(len(outbox), 0)  
#         finally:  
#             if original_target is not None:  
#                 run_low_stock_alerts.__globals__['target_warehouses'] = original_target  
#             if original_recipient is not None:  
#                 run_low_stock_alerts.__globals__['recipient_email'] = original_recipient  
  
#     @patch('frappe.sendmail')  
#     def test_send_low_stock_email_template(self, mock_sendmail):  
#         """Test email template rendering"""  
#         # Set up mock to capture emails  
#         outbox = []  
#         def capture_email(*args, **kwargs):  
#             outbox.append(kwargs)  
#         mock_sendmail.side_effect = capture_email  
          
#         items = [{  
#             "item_code": "TEST-001",  
#             "item_name": "Test Item",  
#             "warehouse": "Test WH",  
#             "projected_qty": 5,  
#             "reorder_level": 10  
#         }]  
#         send_low_stock_email(items, "test@example.com")  
          
#         self.assertEqual(len(outbox), 1)  
#         email = outbox[0]  
#         self.assertIn("Low Stock Alert", email["subject"])  
#         self.assertIn("TEST-001", email["message"])  
#         self.assertIn("Test Item", email["message"])  
#         self.assertIn("Test WH", email["message"])  
#         self.assertIn("5", email["message"])  
#         self.assertIn("10", email["message"])


import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch

import low_stock_alerts.api as api
from low_stock_alerts.api import (
    on_sle_update,
    check_and_alert_low_stock,
    get_monitored_warehouses_for_leaf,
    send_low_stock_email,
    run_low_stock_alerts_fallback,
)


class TestLowStockAlerts(IntegrationTestCase):

    def setUp(self):
        frappe.cache().flushall()
        api.monitored_warehouses = []

        self.company = self.create_test_company()

        self.group_wh = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": f"Test Group WH {frappe.generate_hash(length=4)}",
            "company": self.company,
            "is_group": 1,
            "email_id": "group@example.com",
        }).insert()

        self.wh1 = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": f"Test Leaf WH1 {frappe.generate_hash(length=4)}",
            "company": self.company,
            "parent_warehouse": self.group_wh.name,
            "email_id": "wh1@example.com",
        }).insert()

        self.wh2 = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": f"Test Leaf WH2 {frappe.generate_hash(length=4)}",
            "company": self.company,
            "parent_warehouse": self.group_wh.name,
            "email_id": "wh2@example.com",
        }).insert()

        self.item = frappe.get_doc({
            "doctype": "Item",
            "item_code": f"_Test Low Stock Item {frappe.generate_hash(length=4)}",
            "item_name": "Test Low Stock Item",
            "is_stock_item": 1,
            "stock_uom": "Nos",
            "item_group": "Products",
        }).insert()

        self.item.append("reorder_levels", {
            "warehouse": self.wh1.name,
            "warehouse_reorder_level": 10,
            "warehouse_reorder_qty": 5,
        })
        self.item.append("reorder_levels", {
            "warehouse": self.wh2.name,
            "warehouse_reorder_level": 10,
            "warehouse_reorder_qty": 5,
        })
        self.item.save()

        from erpnext.stock.utils import get_or_make_bin
        self.bin1 = get_or_make_bin(self.item.name, self.wh1.name)
        self.bin2 = get_or_make_bin(self.item.name, self.wh2.name)

        frappe.db.set_value("Bin", self.bin1, {"projected_qty": 5})
        frappe.db.set_value("Bin", self.bin2, {"projected_qty": 8})

        api.monitored_warehouses = [self.group_wh.name]

    def tearDown(self):
        api.monitored_warehouses = []
        frappe.db.rollback()

    def create_test_company(self):
        import uuid
        uid = str(uuid.uuid4())[:8].upper()
        abbr = f"LS{uid}"

        company = frappe.get_doc({
            "doctype": "Company",
            "company_name": f"_Test Low Stock Company {uid}",
            "abbr": abbr,
            "country": "India",
            "default_currency": "INR",
            "create_chart_of_accounts_based_on": "Standard Template",
            "chart_of_accounts": "Standard"
        })
        company.insert(ignore_permissions=True)
        return company.name

    @patch("frappe.enqueue")
    def test_on_sle_update_enqueues_check(self, mock_enqueue):
        sle = frappe.new_doc("Stock Ledger Entry")
        sle.docstatus = 1
        sle.is_cancelled = 0
        sle.item_code = self.item.name
        sle.warehouse = self.wh1.name

        on_sle_update(sle, "on_update")

        mock_enqueue.assert_called_once()

    @patch("frappe.sendmail")
    def test_check_and_alert_low_stock_sends_email(self, mock_sendmail):
        check_and_alert_low_stock(self.item.name, self.wh1.name)
        mock_sendmail.assert_called_once()
        self.assertEqual(mock_sendmail.call_args.kwargs["recipients"], "group@example.com")

    @patch("frappe.sendmail")
    def test_check_and_alert_no_email_when_above_level(self, mock_sendmail):
        frappe.db.set_value("Bin", self.bin1, "projected_qty", 50)
        check_and_alert_low_stock(self.item.name, self.wh1.name)
        mock_sendmail.assert_not_called()

    @patch("frappe.sendmail")
    def test_throttling_prevents_duplicate_emails(self, mock_sendmail):
        check_and_alert_low_stock(self.item.name, self.wh1.name)
        check_and_alert_low_stock(self.item.name, self.wh1.name)
        mock_sendmail.assert_called_once()

    def test_get_monitored_warehouses_for_leaf(self):
        monitored = get_monitored_warehouses_for_leaf(self.wh1.name)
        self.assertEqual(monitored, [self.group_wh.name])

    @patch("frappe.sendmail")
    def test_send_low_stock_email_template(self, mock_sendmail):
        send_low_stock_email(
            [{"item_code": self.item.name, "item_name": "Test", "warehouse": self.wh1.name, "projected_qty": 5, "reorder_level": 10}],
            "test@example.com",
            self.group_wh.name,
        )
        mock_sendmail.assert_called_once()

    @patch("frappe.sendmail")
    def test_fallback_scans_all_warehouses(self, mock_sendmail):
        # Clear monitored warehouses to force fallback
        api.monitored_warehouses = []

        # Run the fallback function
        run_low_stock_alerts_fallback()

        # Dynamically calculate warehouses that should receive emails
        bins = frappe.get_all("Bin", fields=["item_code", "warehouse", "projected_qty"])
        
        # Only include warehouses that have projected_qty less than reorder_level
        low_stock_warehouses = set()
        for b in bins:
            item = frappe.get_doc("Item", b.item_code)
            for rl in item.reorder_levels:
                if rl.warehouse == b.warehouse and b.projected_qty < rl.warehouse_reorder_level:
                    wh = frappe.get_doc("Warehouse", b.warehouse)
                    if wh.email_id:
                        low_stock_warehouses.add(wh.name)

        # Assert emails were sent exactly to these warehouses
        self.assertEqual(mock_sendmail.call_count, len(low_stock_warehouses))

    @patch("frappe.sendmail")
    def test_group_aggregation(self, mock_sendmail):
        frappe.db.set_value("Bin", self.bin2, "projected_qty", 5)
        check_and_alert_low_stock(self.item.name, self.wh1.name)
        check_and_alert_low_stock(self.item.name, self.wh2.name)

        recipients = {c.kwargs["recipients"] for c in mock_sendmail.call_args_list}
        self.assertIn("group@example.com", recipients)
