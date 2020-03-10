const express = require('express');
const app = express();
const port = 3000;
const cors = require('cors');
const path = require('path');
const exphbs = require('express-handlebars');
const bodyParser = require('body-parser');
let mysql = require('mysql');
// Set the __basedir for future use
global.__basedir = __dirname;

const HTML_DIR = path.join(__dirname, '/');
app.use(express.static(HTML_DIR));

const {getReadings} = require('./routes/d3dashboard');

// MySQL stuff
let db = mysql.createConnection({
    host: "127.0.0.1",
    user: "adminuser",
    port: "3306",
    password: "adminPa$$word1!",
    database: "coffee_scale"
});

db.connect(function (err) {
    if (err) throw err;
    console.log("Connected!");
});
global.db = db;

// App stuff
app.set('views', __dirname + '/views'); // set express to look in this folder to render our view
app.set('view engine', 'ejs'); // configure template engine
app.use(bodyParser.urlencoded({extended: false}));
app.use(bodyParser.json()); // parse form data client
app.use(cors());

// Routings
app.get('/', getReadings);

app.get('/static', (request, response, next) => {
    response.sendFile(__dirname + '/views/static/static.html')
});


// Startup the server
app.listen(port, (err) => {
    if (err) {
        return console.log('something bad happened', err)
    }

    console.log(`server is listening on ${port}`)
});