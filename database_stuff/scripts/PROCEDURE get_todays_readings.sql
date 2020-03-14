DROP PROCEDURE IF EXISTS get_todays_readings;
CREATE DEFINER=`adminuser`@`localhost` PROCEDURE `get_todays_readings`(IN startDate DATETIME, IN endDate DATETIME)
BEGIN

	-- Assume the start date is midnight
	IF startDate IS NULL THEN
      SET startDate = timestamp(current_date);
   END IF;

	IF endDate IS NULL THEN
		SET endDate = NOW();
	END IF;

    -- Create the temporary time table
    call create_time_table(startDate, endDate);

    -- Select and join readings with time table
	SELECT
		DATE_FORMAT(t3.`minute`, '%Y/%m/%d %h:%i %p') as `date`, IFNULL(t2.value,0) as `value`
	FROM
		coffee_scale.time_table AS t3
			LEFT JOIN
    (SELECT
        DATE_FORMAT(t1.`datetime`, '%Y-%m-%d %H:%i:00') AS `interval`,
            avg(t1.`value`) as `value`
		FROM
			coffee_scale.weight_reading AS t1
		WHERE
			t1.`datetime` >= startDate
		GROUP BY `interval`
		ORDER BY `interval` ASC) AS t2
    ON t3.minute = t2.interval
    ORDER BY t3.minute DESC;

END