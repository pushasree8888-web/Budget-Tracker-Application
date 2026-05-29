from flask import (
    Flask,
    render_template,
    request,
    url_for,
    flash,
    redirect,
    Response,
    session
)

from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, date as dt_date
from sqlalchemy import func
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

app = Flask(__name__)

# CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'my-secret-key'

db = SQLAlchemy(app)


# =========================
# MODELS
# =========================

class Expense(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    description = db.Column(
        db.String(120),
        nullable=False
    )

    Amount = db.Column(
        db.Float,
        nullable=False
    )

    Category = db.Column(
        db.String(120),
        nullable=False
    )

    Date = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )


# =========================
# CREATE DATABASE
# =========================

with app.app_context():
    db.create_all()


# =========================
# CATEGORIES
# =========================

CATEGORIES = [
    'Food',
    'Transport',
    'Rent',
    'Utilities',
    'Health',
    'EMI',
    'Gold/Silver'
]


# =========================
# HELPER FUNCTION
# =========================

def parse_date_or_none(s: str):

    if not s:
        return None

    try:
        return datetime.strptime(
            s,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        return None


# =========================
# HOME PAGE
# =========================

@app.route("/")
def index():

    # LOGIN PROTECTION
    if "user_id" not in session:

        flash(
            "Please login first",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # FILTER VALUES
    start_str = (
        request.args.get("start") or ""
    ).strip()

    end_str = (
        request.args.get("end") or ""
    ).strip()

    selected_category = (
        request.args.get("Category") or ""
    ).strip()

    search = (
        request.args.get("search") or ""
    ).strip()

    # CONVERT TO DATE
    start_date = parse_date_or_none(
        start_str
    )

    end_date = parse_date_or_none(
        end_str
    )

    # VALIDATION
    if (
        start_date and
        end_date and
        end_date < start_date
    ):

        flash(
            "End date cannot be before start date",
            "error"
        )

        start_date = None
        end_date = None

        start_str = ""
        end_str = ""

    # QUERY
    q = Expense.query.filter_by(
        user_id=session["user_id"]
    )

    if start_date:
        q = q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        q = q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        q = q.filter(
            Expense.Category == selected_category
        )
    if search:
        q = q.filter(
            Expense.description.ilike(f"%{search}%")
        )

    expenses = q.order_by(
        Expense.Date.desc(),
        Expense.id.desc()
    ).all()

    recent_expenses = expenses[:5]
    expense_count = len(expenses)

    # TOTAL
    total = round(
        sum(e.Amount for e in expenses),
        2
    )

    # MONTH TOTAL
    current_month = date.today().month
    current_year = date.today().year

    month_total = round(
        sum(
            e.Amount
            for e in expenses
            if e.Date.month == current_month
            and e.Date.year == current_year
        ),2
    )

    # PIE CHART
    cat_q = db.session.query(
        Expense.Category,
        func.sum(Expense.Amount)
    ).filter(
        Expense.user_id == session["user_id"]
    )

    if start_date:
        cat_q = cat_q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        cat_q = cat_q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        cat_q = cat_q.filter(
            Expense.Category == selected_category
        )

    cat_rows = cat_q.group_by(
        Expense.Category
    ).all()

    cat_labels = [
        c for c, _ in cat_rows
    ]

    cat_values = [
        round(float(s or 0), 2)
        for _, s in cat_rows
    ]

    # BAR CHART
    day_q = db.session.query(
        Expense.Date,
        func.sum(Expense.Amount)
    ).filter(
        Expense.user_id == session["user_id"]
    )

    if start_date:
        day_q = day_q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        day_q = day_q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        day_q = day_q.filter(
            Expense.Category == selected_category
        )

    day_rows = day_q.group_by(
        Expense.Date
    ).order_by(
        Expense.Date
    ).all()

    day_labels = [
        d.isoformat()
        for d, _ in day_rows
    ]

    day_values = [
        round(float(s or 0), 2)
        for _, s in day_rows
    ]

    return render_template(
        "index.html",

        expense_count=expense_count,

        recent_expenses=recent_expenses,

        categories=CATEGORIES,

        today=date.today().isoformat(),

        expenses=expenses,

        total=total,

        month_total=month_total,

        start_str=start_str,

        end_str=end_str,

        selected_category=selected_category,

        search=search,

        cat_labels=cat_labels,

        cat_values=cat_values,

        day_labels=day_labels,

        day_values=day_values
    )


# =========================
# ADD EXPENSE
# =========================

@app.route("/add", methods=['POST'])
def add():

    if "user_id" not in session:
        return redirect(url_for("login"))

    description = (
        request.form.get("description") or ""
    ).strip()

    Amount_str = (
        request.form.get("Amount") or ""
    ).strip()

    Category = (
        request.form.get("Category") or ""
    ).strip()

    date_str = (
        request.form.get("date") or ""
    ).strip()

    if (
        not description or
        not Amount_str or
        not Category
    ):

        flash(
            "Please fill all fields",
            "error"
        )

        return redirect(
            url_for("index")
        )

    try:

        Amount = float(
            Amount_str
        )

        if Amount <= 0:
            raise ValueError

    except ValueError:

        flash(
            "Amount must be positive",
            "error"
        )

        return redirect(
            url_for("index")
        )

    try:

        d = (
            datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

            if date_str
            else date.today()
        )

    except ValueError:

        d = date.today()

    e = Expense(
        description=description,
        Amount=Amount,
        Category=Category,
        Date=d,
        user_id=session["user_id"]
    )

    db.session.add(e)

    db.session.commit()

    flash(
        "Expense added successfully",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================
# DELETE
# =========================

@app.route(
    '/delete/<int:expense_id>',
    methods=['POST']
)
def delete(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    e = Expense.query.filter_by(
        id=expense_id,
        user_id=session["user_id"]).first_or_404()

    db.session.delete(e)

    db.session.commit()

    flash(
        "Expense deleted",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================
# EDIT GET
# =========================

@app.route(
    '/edit/<int:expense_id>',
    methods=['GET']
)
def edit(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    e = Expense.query.filter_by(
        id=expense_id,
        user_id=session["user_id"]).first_or_404()

    return render_template(
        "edit.html",
        expense=e,
        categories=CATEGORIES,
        tday=dt_date.today().isoformat()
    )


# =========================
# EDIT POST
# =========================

@app.route(
    '/edit/<int:expense_id>',
    methods=['POST']
)
def edit_post(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    e = Expense.query.filter_by(
        id=expense_id,
        user_id=session["user_id"]).first_or_404()

    description = (
        request.form.get("description") or ""
    ).strip()

    Amount_str = (
        request.form.get("Amount") or ""
    ).strip()

    Category = (
        request.form.get("Category") or ""
    ).strip()

    date_str = (
        request.form.get("Date") or ""
    ).strip()

    if (
        not description or
        not Amount_str or
        not Category
    ):

        flash(
            "Please fill all fields",
            "error"
        )

        return redirect(
            url_for(
                "edit",
                expense_id=expense_id
            )
        )

    try:

        Amount = float(
            Amount_str
        )

        if Amount <= 0:
            raise ValueError

    except ValueError:

        flash(
            "Amount must be positive",
            "error"
        )

        return redirect(
            url_for(
                "edit",
                expense_id=expense_id
            )
        )

    try:

        d = (
            datetime.strptime(
                date_str,
                "%Y-%m-%d"
            ).date()

            if date_str
            else dt_date.today()
        )

    except ValueError:

        d = dt_date.today()

    e.description = description
    e.Amount = Amount
    e.Category = Category
    e.Date = d

    db.session.commit()

    flash(
        "Expense updated",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================
# EXPORT CSV
# =========================

@app.route("/export.csv")
def export_csv():

    if "user_id" not in session:
        return redirect(url_for("login"))

    start_str = (
        request.args.get("start") or ""
    ).strip()

    end_str = (
        request.args.get("end") or ""
    ).strip()

    selected_category = (
        request.args.get("Category") or ""
    ).strip()

    start_date = parse_date_or_none(
        start_str
    )

    end_date = parse_date_or_none(
        end_str
    )

    q = Expense.query.filter_by(
        user_id=session["user_id"]
    )

    if start_date:
        q = q.filter(
            Expense.Date >= start_date
        )

    if end_date:
        q = q.filter(
            Expense.Date <= end_date
        )

    if selected_category:
        q = q.filter(
            Expense.Category == selected_category
        )

    expenses = q.order_by(
        Expense.Date,
        Expense.id
    ).all()

    lines = [
        "Date,Description,Category,Amount"
    ]

    for e in expenses:

        lines.append(
            f"{e.Date.isoformat()},"
            f"{e.description},"
            f"{e.Category},"
            f"{e.Amount:.2f}"
        )

    csv_data = "\n".join(lines)

    filename = "expenses.csv"

    return Response(
        csv_data,

        headers={
            "Content-Type": "text/csv",

            "Content-Disposition":
            f"attachment; filename={filename}"
        }
    )


# =========================
# LOGIN
# =========================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = (
            request.form.get("email") or ""
        ).strip()

        password = (
            request.form.get("password") or ""
        ).strip()

        if not email or not password:

            flash(
                "Please fill all fields",
                "error"
            )

            return redirect(
                url_for("login")
            )

        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            flash(
                "User not found",
                "error"
            )

            return redirect(
                url_for("login")
            )

        if not check_password_hash(
            user.password,
            password
        ):

            flash(
                "Incorrect password",
                "error"
            )

            return redirect(
                url_for("login")
            )

        # SAVE SESSION
        session["user_id"] = user.id
        session["username"] = user.username

        flash(
            "Login successful",
            "success"
        )

        return redirect(
            url_for("index")
        )

    return render_template(
        "login.html"
    )


# =========================
# SIGNUP
# =========================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        username = (
            request.form.get("username") or ""
        ).strip()

        email = (
            request.form.get("email") or ""
        ).strip()

        password = (
            request.form.get("password") or ""
        ).strip()

        confirm_password = (
            request.form.get("confirm_password") or ""
        ).strip()

        if (
            not username or
            not email or
            not password or
            not confirm_password
        ):

            flash(
                "Please fill all fields",
                "error"
            )

            return redirect(
                url_for("signup")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match",
                "error"
            )

            return redirect(
                url_for("signup")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "Email already registered",
                "error"
            )

            return redirect(
                url_for("signup")
            )

        hashed_password = generate_password_hash(
            password
        )

        new_user = User(
            username=username,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)

        db.session.commit()

        flash(
            "Account created successfully",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "signup.html"
    )


# =========================
# PROFILE
# =========================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    total_expenses = db.session.query(
        func.sum(Expense.Amount)
    ).filter_by(
        user_id=session["user_id"]
    ).scalar() or 0

    total_transactions = Expense.query.filter_by(
        user_id=session["user_id"]
    ).count()

    return render_template(
        "profile.html",
        user=user,
        total_expenses=total_expenses,
        total_transactions=total_transactions
    )

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Logged out successfully",
        "success"
    )

    return redirect(
        url_for("login")
    )


# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    app.run(
        debug=True,
        port=4848
    )