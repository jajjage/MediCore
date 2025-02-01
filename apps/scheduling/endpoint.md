# Get all currently valid day shifts

GET /api/shift-templates/?is_currently_valid=true&shift_types=DAY

# Get templates requiring doctors with at least 2 staff members

GET /api/shift-templates/?role_requirements=DOCTOR&min_max_staff=2

# Get morning shifts starting after 8 AM

GET /api/shift-templates/?shift_types=MORNING&start_time_after=08:00:00

# Get templates for a specific department with recurring parameters

GET /api/shift-templates/?department=1&has_recurrence_parameters=true

GET /api/shift-templates/
GET /api/shift-templates/?department=1&type=DAY
GET /api/shift-templates/?search=morning
GET /api/shift-templates/?ordering=-valid_from
POST /api/shift-templates/{id}/toggle_active/
GET /api/shift-templates/by_department/?department_id=1
