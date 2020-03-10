CREATE DEFINER=`adminuser`@`localhost` PROCEDURE `create_time_table`(IN startDate DATETIME, IN endDate DATETIME)
BEGIN
	-- Assume the start date is midnight
	IF startDate IS NULL THEN
      SET startDate = timestamp(current_date);
   END IF;

	IF endDate IS NULL THEN
		SET endDate = NOW();
	END IF;

    -- Create a temporary table to hold the times
    DROP TABLE IF EXISTS time_table;

    create temporary table coffee_scale.time_table
    (
        minute DATETIME
    );

    -- Populate the temporary time table
	WHILE startDate <= endDate DO
		INSERT INTO time_table VALUES (startDate);
		SET startDate = date_add(startDate, INTERVAL 1 MINUTE);
	END WHILE;

END