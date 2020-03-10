-- TODO: Due to rounding, this cuts off the upper values (ex. max value of 14157 rounds to bin sizes of 14 and stops at 14000)
CREATE DEFINER=`adminuser`@`localhost` PROCEDURE `assign_bins`()
BEGIN

    declare loop_index INTEGER;
    declare loop_end INTEGER;
    declare bin_range INTEGER;

    set loop_index = 0;
    set loop_end = 999;
    set bin_range = (SELECT (MAX(value) - MIN(value)) / 1000 as 'bin_range' FROM coffee_scale.weight_reading);

    -- Create a temporary table to hold the bin limits
    DROP TABLE IF EXISTS bin_ranges;

    create temporary table bin_ranges
    (
        min INTEGER,
        max INTEGER
    );

    -- Populate the temporary bin limits table
    bin_loop: LOOP
        -- Check if we should leave the "for" loop
        if loop_index > loop_end then
            leave bin_loop;
        end if;

        -- Insert a bin range into the temporary table
        INSERT INTO bin_ranges VALUES(bin_range*loop_index, (bin_range*(loop_index+1))-1);

        -- Increment the counter
        set loop_index = loop_index + 1;
    end loop;

END