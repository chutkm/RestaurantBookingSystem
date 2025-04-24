# 🧾 Restaurant Booking System

A modern restaurant reservation system powered by **Quart**, with a **chatbot interface**, **admin dashboard**, **pre-order system**, and **MySQL** backend. Designed to streamline customer interactions and provide advanced features for restaurant managers.

## 🚀 Features

### 🧑‍🍳 For Customers
- **Chatbot-powered booking**: Easy-to-use, natural language interface for making reservations.
- **Select date, time, and number of guests**: Customizable booking options for a personalized experience.
- **Instant booking confirmations**: Receive immediate booking confirmation notifications.
- **Automated reminders**: Get reminders for upcoming reservations to ensure you never forget your visit.
- **Pre-order food**: Order food in advance from the restaurant’s menu before your visit.
- **View promotions and discounts**: Check for current restaurant offers, deals, and promotions directly in the app.

### 🛠 For Administrators
- **Admin dashboard**: Manage reservations, pre-orders, and customer data from a centralized panel.
- **Add/edit restaurants, menus, and tables**: Customize and update restaurant details in real-time.
- **View real-time statistics**: Track restaurant traffic, peak hours, and popular dishes to optimize operations.
- **Customer notification control**: Manage and customize alerts and reminders for customers.
- **Generate booking and sales reports**: Automatically generate reports based on bookings and sales performance.
- **Promotion management**: Create and manage promotions or discounts offered to customers.

## 🧰 Tech Stack

- **Backend**: [Quart](https://pgjones.gitlab.io/quart/) (asynchronous Flask-compatible web framework)
- **Database**: MySQL
- **Frontend**: HTML, CSS, Bootstrap
- **Others**: Jinja templates, Chart.js for analytics

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/chutkm/RestaurantBookingSystem.git
cd RestaurantBookingSystem
```

### 2. Install dependencies

Make sure you have Python 3.9+ and a MySQL server running.

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file with your database credentials:

```env
DB_HOST=localhost
DB_NAME=restaurant_db
DB_USER=root
DB_PASS=yourpassword
```

### 4. Initialize the database

Import the provided schema (`schema.sql`) into MySQL:

```bash
mysql -u root -p restaurant_db < schema.sql
```

### 5. Run the app

```bash
quart run --reload
```

The app will be available at: [http://localhost:5000](http://localhost:5000)

## 📂 Project Structure

```
RestaurantBookingSystem/
│
├── app/                # Quart app logic (routes, models, database)
├── static/             # CSS, JS, images
├── templates/          # Jinja2 HTML templates
├── schema.sql          # MySQL database schema
├── main.py             # Entry point
├── requirements.txt
└── README.md
```

## 📈 Future Plans

- Add user login / registration
- Reservation history and loyalty rewards
- SMS/email integrations for notifications
- Multi-language chatbot support
- Expanded promotional features for marketing campaigns

## 📄 License

MIT License
