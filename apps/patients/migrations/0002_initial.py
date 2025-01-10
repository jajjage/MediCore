# Generated by Django 5.1.4 on 2025-01-08 18:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("patients", "0001_initial"),
        ("staff", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalpatient",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientaddress",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientallergies",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientappointment",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientappointment",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientappointment",
            name="modified_by",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientappointment",
            name="physician",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                limit_choices_to={"role__name": "Doctor"},
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientchronicconditions",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientdemographics",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientdiagnosis",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientemergencycontact",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientmedicalreport",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientoperation",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientoperation",
            name="modified_by",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientoperation",
            name="surgeon",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                limit_choices_to={"role__name__in": ["Doctor", "Head Doctor"]},
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientvisit",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staff.staffmember",
            ),
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(fields=["email"], name="patients_email_bf0efb_idx"),
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(
                fields=["date_of_birth"], name="patients_date_of_24544d_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(
                fields=["last_name", "first_name"], name="patients_last_na_ce6411_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.UniqueConstraint(fields=("email",), name="unique_email"),
        ),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.UniqueConstraint(fields=("pin",), name="unique_pin"),
        ),
        migrations.AddField(
            model_name="historicalpatientvisit",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientoperation",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientmedicalreport",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientemergencycontact",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientdiagnosis",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientdemographics",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientchronicconditions",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientappointment",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientallergies",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="historicalpatientaddress",
            name="patient",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientaddress",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="addresses",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientallergies",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="allergies",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientappointment",
            name="created_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_appointments",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="patientappointment",
            name="modified_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="modified_appointments",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="patientappointment",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="appointments",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientappointment",
            name="physician",
            field=models.ForeignKey(
                limit_choices_to={"role__name": "Doctor"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="appointments",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="patientchronicconditions",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="chronic_conditions",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientdemographics",
            name="patient",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="demographics",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientdiagnosis",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="diagnoses",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientemergencycontact",
            name="patient",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="emergency_contact",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientmedicalreport",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="medical_reports",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientoperation",
            name="modified_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="modified_operations",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="patientoperation",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="operations",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientoperation",
            name="surgeon",
            field=models.ForeignKey(
                limit_choices_to={"role__name__in": ["Doctor", "Head Doctor"]},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="operations",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="patientprescription",
            name="appointment",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prescription",
                to="patients.patientappointment",
            ),
        ),
        migrations.AddField(
            model_name="patientprescription",
            name="issued_by",
            field=models.ForeignKey(
                limit_choices_to={"role__name": "Doctor"},
                on_delete=django.db.models.deletion.CASCADE,
                related_name="issued_prescriptions",
                to="staff.staffmember",
            ),
        ),
        migrations.AddField(
            model_name="patientvisit",
            name="patient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="visits",
                to="patients.patient",
            ),
        ),
        migrations.AddIndex(
            model_name="patientaddress",
            index=models.Index(
                fields=["postal_code"], name="patient_add_postal__1b2093_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientaddress",
            index=models.Index(fields=["state"], name="patient_add_state_59b8a6_idx"),
        ),
        migrations.AddIndex(
            model_name="patientaddress",
            index=models.Index(fields=["city"], name="patient_add_city_e1fa70_idx"),
        ),
        migrations.AddConstraint(
            model_name="patientaddress",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_primary", True)),
                fields=("patient", "is_primary"),
                name="unique_primary_address_per_patient",
            ),
        ),
        migrations.AddIndex(
            model_name="patientallergies",
            index=models.Index(
                fields=["patient"], name="patient_all_patient_71e0e2_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientallergies",
            index=models.Index(fields=["name"], name="patient_all_name_8d7884_idx"),
        ),
        migrations.AddIndex(
            model_name="patientallergies",
            index=models.Index(
                fields=["severity"], name="patient_all_severit_e3fd33_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientappointment",
            index=models.Index(
                fields=["appointment_date", "appointment_time"],
                name="patient_app_appoint_3d31b7_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="patientappointment",
            index=models.Index(
                fields=["status", "appointment_date"],
                name="patient_app_status_76394a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="patientchronicconditions",
            index=models.Index(
                fields=["patient"], name="patient_chr_patient_86031e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientchronicconditions",
            index=models.Index(
                fields=["condition"], name="patient_chr_conditi_015f84_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientchronicconditions",
            index=models.Index(
                fields=["diagnosis_date"], name="patient_chr_diagnos_30027b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdemographics",
            index=models.Index(fields=["gender"], name="patient_dem_gender_951d6d_idx"),
        ),
        migrations.AddIndex(
            model_name="patientdemographics",
            index=models.Index(
                fields=["blood_type"], name="patient_dem_blood_t_364bea_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdemographics",
            index=models.Index(
                fields=["preferred_language"], name="patient_dem_preferr_b18c76_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdemographics",
            index=models.Index(
                fields=["marital_status"], name="patient_dem_marital_aee90b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdemographics",
            index=models.Index(
                fields=["created_at"], name="patient_dem_created_9c30ef_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdiagnosis",
            index=models.Index(
                fields=["patient"], name="patient_dia_patient_13836d_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdiagnosis",
            index=models.Index(
                fields=["diagnosis_date"], name="patient_dia_diagnos_9b0b29_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdiagnosis",
            index=models.Index(
                fields=["diagnosis_name"], name="patient_dia_diagnos_0f2135_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientdiagnosis",
            index=models.Index(
                fields=["icd_code"], name="patient_dia_icd_cod_2032aa_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientmedicalreport",
            index=models.Index(
                fields=["patient"], name="patient_med_patient_f90d8b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientmedicalreport",
            index=models.Index(fields=["title"], name="patient_med_title_420860_idx"),
        ),
        migrations.AddIndex(
            model_name="patientmedicalreport",
            index=models.Index(
                fields=["created_at"], name="patient_med_created_d7b0c6_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientmedicalreport",
            index=models.Index(
                fields=["updated_at"], name="patient_med_updated_47fee8_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientoperation",
            index=models.Index(
                fields=["operation_date", "operation_name"],
                name="patient_ope_operati_57967e_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="patientoperation",
            index=models.Index(
                fields=["operation_code"], name="patient_ope_operati_8a7383_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientprescription",
            index=models.Index(
                fields=["appointment"], name="patient_pre_appoint_45a731_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientprescription",
            index=models.Index(
                fields=["issued_by", "issued_date"],
                name="patient_pre_issued__70343c_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="patientprescription",
            index=models.Index(
                fields=["issued_date"], name="patient_pre_issued__a9e4dc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientvisit",
            index=models.Index(
                fields=["visit_date", "ward_or_clinic"],
                name="patient_vis_visit_d_fd66ac_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="patientvisit",
            index=models.Index(
                fields=["discharge_date", "patient"],
                name="patient_vis_dischar_c71203_idx",
            ),
        ),
    ]