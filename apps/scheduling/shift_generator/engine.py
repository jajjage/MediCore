# shift_generator/engine.py

from scheduler import generate_schedule


def run_schedule_generation(department_id, year, month):
    """
    Run the schedule generation process for a given department and month.
    """
    generate_schedule(department_id, year, month)


if __name__ == "main":
    run_schedule_generation("67d03033-9408-4143-8d4a-cd2e3994e0fe", 2025, 3)
