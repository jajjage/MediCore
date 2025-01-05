DELETE FROM public.core_user WHERE is_superuser = False;
DELETE FROM public.hospital_profile WHERE subscription_plan = 'basic';
-- DELETE FROM public.tenants_domain WHERE domain = 'city-hospital.medicore.local';
DELETE FROM public.tenants_client WHERE schema_name = 'cityhospital_d25c5f8d';
