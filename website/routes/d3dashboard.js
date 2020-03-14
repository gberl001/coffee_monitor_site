const fs = require("fs");
const Json2csvParser = require("json2csv").Parser;
const d3 = require("d3");

module.exports = {
    getReadings: (req, res) => {

        res.header("Access-Control-Allow-Origin", "*");

        // Stored procedure gets readings for the current day up to NOW()
        let query = "call get_todays_readings(null, null)";

        // execute query
        db.query(query, (err, result) => {
            if (err) {
                res.redirect('/');
            }

            // Store the info in a CSV
            const jsonData = JSON.parse(JSON.stringify(result[0]));
            const json2csvParser = new Json2csvParser({header: true});
            const csvData = json2csvParser.parse(jsonData);

            fs.writeFile("lib/readings_test.csv", csvData, function (error) {
                if (error) throw error;
                console.log("CSV Creation Successful!")
            });

            res.render('d3dashboard', {
                pct_remaining: "74%",
                age: "1:26",
                cups_remaining: 5.6,
                title: "Welcome to Coffee Monitor"
            });
        });
    },
};