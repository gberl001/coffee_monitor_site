const fs = require("fs");
const Json2csvParser = require("json2csv").Parser;
const d3 = require("d3");

module.exports = {
    getReadingsNew: (req, res) => {

        res.header("Access-Control-Allow-Origin", "*");


        // Stored procedure gets readings for the current day up to NOW()
        let seconds = (new Date().getTime() - modifiedDate('lib/readings_test.csv')) / 1000;
        let query = "";
        if (seconds > 60) {
            query = "call get_todays_readings(null, null)";
        } else {
            query = "SELECT 1";
        }

        // Create the CSV data for the chart
        db.query(query, (err, result) => {
            if (err) {
                res.redirect('/');
            }

            if (seconds > 60) {
                // Store the info in a CSV
                const jsonData = JSON.parse(JSON.stringify(result[0]));
                const json2csvParser = new Json2csvParser({header: true});
                const csvData = json2csvParser.parse(jsonData);

                fs.writeFile("lib/readings_test.csv", csvData, function (error) {
                    if (error) throw error;
                    console.log("CSV Creation Successful!")
                });
            }

            // Get the age
            query = "SELECT " +
                "LEFT(TIMEDIFF(NOW(),t1.datetime),5) as age " +
                "FROM coffee_scale.detected_event as t1 " +
                "LEFT JOIN coffee_scale.event as t2 " +
                "ON t1.event_id=t2.id " +
                "WHERE t2.name='Full Brew'" +
                "ORDER BY t1.datetime DESC LIMIT 1";
            db.query(query, (err, result) => {
                if (err) {
                    res.redirect('/');
                }
                var coffeeAge = result[0].age;

                // Get the cups remaining
                query = "SELECT ((SELECT AVG(t1.value) FROM (SELECT value FROM coffee_scale.weight_reading ORDER BY datetime DESC LIMIT 3) as t1) - " +
                    "(SELECT splatter_point FROM coffee_scale.carafe WHERE name='Home')) / full_cup_weight as cups_remaining " +
                    "FROM coffee_scale.scale WHERE name='PTC'";

                db.query(query, (err, result) => {
                    if (err) {
                        res.redirect('/');
                    }
                    var cupsRemaining = result[0].cups_remaining;

                    query = "SELECT (full_weight - splatter_point) / " +
                        "(SELECT full_cup_weight FROM coffee_scale.scale WHERE name = 'PTC') as total_cups " +
                        "FROM coffee_scale.carafe as t1 " +
                        "WHERE t1.name='Home'";
                    db.query(query, (err, result) => {
                        if (err) {
                            res.redirect('/');
                        }

                        var pct = cupsRemaining / result[0].total_cups * 100;
                        res.render('new_dashboard', {
                            pct_remaining: pct + "%",
                            age: coffeeAge,
                            cups_remaining: cupsRemaining < 0 ? 0 : cupsRemaining.toFixed(2),
                            title: "Welcome to Coffee Monitor"
                        });
                    });

                });
            });
        });
    },
};

function modifiedDate (file) {
    const { mtime } = fs.statSync(file);

    return mtime.getTime();
}