-- Create bin range table
CALL assign_bins();

-- Join temp bin table with weight readings table to assign their bins
SELECT
       br.min, br.max, count(value)
FROM
     bin_ranges as br
         LEFT JOIN
     weight_reading as wr
     ON wr.value < br.max AND wr.value > br.min
GROUP BY br.min;