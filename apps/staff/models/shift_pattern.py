from django.db import models


class ShiftPattern(models.Model):
    department = models.ForeignKey("Department", on_delete=models.CASCADE, related_name="shift_pattern")
    shift_type = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()
    min_staff = models.IntegerField()
    break_duration = models.DurationField()
