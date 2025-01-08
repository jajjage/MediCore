-- DELETE FROM public.core_user WHERE is_superuser = False;
-- DELETE FROM public.hospital_profile WHERE subscription_plan = 'premium';
DELETE FROM public.tenants_domain WHERE domain = 'peak-health-institute.medicore.local';
DELETE FROM public.tenants_client WHERE schema_name = 'peakhealthinstitute_a2c00817'
