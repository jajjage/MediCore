 cursor.execute("""
                            CREATE OR REPLACE FUNCTION check_department_member_hospital()
                            RETURNS TRIGGER AS $$
                            DECLARE
                                user_hospital_id UUID;
                                dept_hospital_id UUID;
                            BEGIN
                            -- Get the hospital IDs
                            SELECT hospital_id INTO user_hospital_id
                            FROM staff_staffmember
                            WHERE id = NEW.user_id;

                            SELECT hospital_id INTO dept_hospital_id
                            FROM staff_department
                            WHERE id = NEW.department_id;

                            -- Check if they match
                            IF user_hospital_id != dept_hospital_id THEN
                                RAISE EXCEPTION 'User and department must belong to the same hospital';
                            END IF;

                            RETURN NEW;
                            END;
                            $$ LANGUAGE plpgsql;

                            CREATE TRIGGER enforce_same_hospital
                                BEFORE INSERT OR UPDATE ON staff_departmentmember
                                FOR EACH ROW
                                EXECUTE FUNCTION check_department_member_hospital();
                        """)
                    cursor.execute("""
                            DROP TRIGGER IF EXISTS enforce_same_hospital ON staff_departmentmember;
                            DROP FUNCTION IF EXISTS check_department_member_hospital();
                        """)