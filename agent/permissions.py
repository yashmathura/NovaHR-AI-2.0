PERMISSION_MATRIX={
 "get_leave_balance": {"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "apply_leave":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "cancel_leave":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"},
 "get_attendance":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "mark_attendance":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "check_out":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"},
 "get_team_attendance":{"MANAGER","HR","ADMIN"}, "get_payroll":{"EMPLOYEE","HR","FINANCE","ADMIN"}, "get_payroll_report":{"FINANCE","HR","ADMIN"}, "generate_payroll":{"FINANCE","HR","ADMIN"},
 "get_tasks":{"EMPLOYEE","MANAGER","HR","ADMIN"}, "assign_task":{"MANAGER","HR","ADMIN"}, "update_task":{"EMPLOYEE","MANAGER","HR","ADMIN"},
 "get_policy":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "analyze_performance":{"EMPLOYEE","MANAGER","HR","ADMIN"}, "team_performance":{"MANAGER","HR","ADMIN"},
 "list_employees":{"MANAGER","HR","FINANCE","ADMIN"}, "get_employee":{"MANAGER","HR","FINANCE","ADMIN"}, "create_employee":{"HR","ADMIN"}, "update_employee":{"HR","ADMIN"}, "delete_employee":{"HR","ADMIN"},
 "list_pending_leaves":{"MANAGER","HR","ADMIN"}, "approve_leave":{"MANAGER","HR","ADMIN"}, "reject_leave":{"MANAGER","HR","ADMIN"}, "send_notification":{"MANAGER","HR","ADMIN"}, "get_notifications":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "mark_notifications_read":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "profile":{"EMPLOYEE","MANAGER","HR","FINANCE","ADMIN"}, "department_summary":{"MANAGER","HR","FINANCE","ADMIN"},
}

def check_permission(role,intent): return role in PERMISSION_MATRIX.get(intent,set())
