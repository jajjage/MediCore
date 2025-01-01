-- DELETE FROM public.core_user WHERE is_superuser = False;
-- DELETE FROM public.hospital_profile WHERE subscription_plan = 'premium';
DELETE FROM public.tenants_client WHERE on_trial = True;
