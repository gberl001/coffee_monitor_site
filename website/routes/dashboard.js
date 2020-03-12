

module.exports = {
    getDashboard: (req, res) => {
        // let query = "SELECT DATE_FORMAT(`datetime`, '%Y/%m/%d %h:%i:%s') as `date`, value\n" +
        //     "FROM weight_reading as t\n" +
        //     "WHERE t.`datetime` >= CURRENT_DATE()\n" +
        //     "ORDER BY `datetime` DESC";

        // Stored procedure gets readings for the current day up to NOW()
        let query = "call get_todays_readings(null, null)";

        // execute query
        db.query(query, (err, result) => {
            if (err) {
                res.redirect('/');
            }
            // console.log(result[0]);
            // console.log(JSON.parse(JSON.stringify(result)));
            res.render('dashboard.ejs', {
                title: "Welcome to Coffee Monitor | View Readings"
                ,readings: result[0] // The result comes back as two dimensional??
            });
        });
    },
};