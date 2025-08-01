import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Models (unchanged)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    budget_goals = db.relationship('BudgetGoal', backref='user', lazy=True)
    savings_goals = db.relationship('SavingsGoal', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_auth_token(self, expires_in=3600):
        return jwt.encode(
            {'user_id': self.id, 'exp': datetime.utcnow() + timedelta(seconds=expires_in)},
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    currency = db.Column(db.String(5), default='$')
    theme = db.Column(db.String(20), default='light')
    notifications = db.Column(db.Boolean, default=True)
    monthly_budget = db.Column(db.Float, default=0.0)
    email_notifications = db.Column(db.Boolean, default=False)
    push_notifications = db.Column(db.Boolean, default=False)
    budget_alerts = db.Column(db.Boolean, default=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)

class BudgetGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    target_date = db.Column(db.Date)

class SavingsGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0)
    target_date = db.Column(db.Date)


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        elif 'auth_token' in session:
            token = session['auth_token']
        
        if not token:
            if request.path.startswith('/api/'):
                return jsonify({'message': 'Token is missing!'}), 401
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
            
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                raise ValueError("User not found")
        except Exception as e:
            if request.path.startswith('/api/'):
                return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401
            session.clear()
            flash('Session expired. Please login again.', 'error')
            return redirect(url_for('login'))
            
        return f(current_user, *args, **kwargs)
        
    return decorated

def calculate_financial_summary(user_id):
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    income = sum(t.amount for t in transactions if t.type == 'income')
    expenses = sum(t.amount for t in transactions if t.type == 'expense')
    balance = income - expenses
    return income, expenses, balance

def validate_transaction_form(form):
    try:
        title = form.get('title', '').strip()
        amount = float(form.get('amount', 0))
        category = form.get('category', '').strip()
        transaction_type = form.get('type', '').strip().lower()
        date_str = form.get('date', '')

        if not all([title, category, transaction_type, date_str]) or amount <= 0:
            return None, "All fields are required and amount must be positive"
            
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
        return {
            'title': title,
            'amount': amount,
            'category': category,
            'type': transaction_type,
            'date': date
        }, None
        
    except ValueError as e:
        return None, f"Invalid input format: {str(e)}"

def validate_budget_form(form):
    try:
        category = form.get('category', '').strip()
        amount = float(form.get('amount', 0))
        target_date_str = form.get('target_date', '')

        if not category or amount <= 0:
            return None, "Category and amount are required and amount must be positive"
            
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else None
            
        return {
            'category': category,
            'amount': amount,
            'target_date': target_date
        }, None
        
    except ValueError as e:
        return None, f"Invalid input format: {str(e)}"


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([username, email, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        new_user.settings = UserSettings()  
        
        db.session.add(new_user)
        try:
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'error')
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))
            
        token = user.generate_auth_token()
        session['user_id'] = user.id
        session['auth_token'] = token
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Main Application Routes
@app.route('/')
@app.route('/dashboard')
@token_required
def dashboard(current_user):
    income, expenses, balance = calculate_financial_summary(current_user.id)
    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc()).limit(5).all()
    savings_goals = SavingsGoal.query.filter_by(user_id=current_user.id).all()
    
    return render_template('dashboard.html',
                         income=income,
                         expenses=expenses,
                         balance=balance,
                         recent_transactions=recent_transactions,
                         savings_goals=savings_goals,
                          current_user=current_user)   

@app.route('/transactions/add', methods=['GET', 'POST'])
@token_required
def add_transaction(current_user):
    if request.method == 'POST':
        data, error = validate_transaction_form(request.form)
        if error:
            flash(error, "error")
            return redirect(url_for('add_transaction'))
            
        data['user_id'] = current_user.id
        new_transaction = Transaction(**data)
        db.session.add(new_transaction)
        try:
            db.session.commit()
            flash("Transaction added successfully!", "success")
            return redirect(url_for('transaction_history'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving transaction: {str(e)}", "error")
        
    return render_template('add_transaction.html')

@app.route('/transactions')
@token_required
def transaction_history(current_user):
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.date.desc()).all()
    return render_template('transaction_history.html', transactions=transactions)

@app.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
@token_required
def edit_transaction(current_user, id):
    transaction = Transaction.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        data, error = validate_transaction_form(request.form)
        if error:
            flash(error, "error")
            return redirect(url_for('edit_transaction', id=id))
            
        for key, value in data.items():
            setattr(transaction, key, value)
            
        try:
            db.session.commit()
            flash("Transaction updated successfully!", "success")
            return redirect(url_for('transaction_history'))
        except Exception as e:
            db.session.rollback()
            flash("Error updating transaction: " + str(e), "error")
    
    return render_template('edit_transaction.html', transaction=transaction)

@app.route('/transactions/delete/<int:id>', methods=['POST'])
@token_required
def delete_transaction(current_user, id):
    transaction = Transaction.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(transaction)
        db.session.commit()
        flash("Transaction deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting transaction: " + str(e), "error")
    return redirect(url_for('transaction_history'))


@app.route('/budget_planning', methods=['GET', 'POST'])
@token_required
def budget_planning(current_user):
    if request.method == 'POST':
        data, error = validate_budget_form(request.form)
        if error:
            flash(error, "error")
            return redirect(url_for('budget_planning'))
            
        data['user_id'] = current_user.id
        new_goal = BudgetGoal(**data)
        db.session.add(new_goal)
        try:
            db.session.commit()
            flash("Budget goal added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Error saving budget goal: " + str(e), "error")
        return redirect(url_for('budget_planning'))
    
    goals = BudgetGoal.query.filter_by(user_id=current_user.id).order_by(BudgetGoal.category).all()
    return render_template('budget_planning.html', goals=goals)

@app.route('/budget_planning/delete/<int:id>', methods=['POST'])
@token_required
def delete_goal(current_user, id):
    goal = BudgetGoal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(goal)
        db.session.commit()
        flash("Budget goal deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Error deleting budget goal: " + str(e), "error")
    return redirect(url_for('budget_planning'))

@app.route('/report')
@token_required
def report(current_user):
    transactions = Transaction.query.filter_by(user_id=current_user.id, type='expense').all()
    goals = BudgetGoal.query.filter_by(user_id=current_user.id).all()
    
    categories = set(t.category for t in transactions).union(g.category for g in goals)
    report_data = []
    
    for category in categories:
        spent = sum(t.amount for t in transactions if t.category == category)
        goal = next((g.amount for g in goals if g.category == category), None)
        
        if goal is None:
            status = 'No Goal Set'
            status_class = 'no-goal'
        elif spent > goal:
            status = 'Over Budget'
            status_class = 'over-budget'
        else:
            status = 'Within Budget'
            status_class = 'within-budget'
        
        report_data.append({
            'category': category,
            'spent': spent,
            'goal': goal if goal else 'N/A',
            'status': status,
            'status_class': status_class
        })
    
    return render_template('report.html', report_data=report_data)

# API Endpoints 
@app.route('/api/summary')
@token_required
def api_summary(current_user):
    income, expenses, balance = calculate_financial_summary(current_user.id)
    savings_goals = SavingsGoal.query.filter_by(user_id=current_user.id).all()
    total_savings = sum(g.current_amount for g in savings_goals)
    
    return jsonify({
        'income': income,
        'expenses': expenses,
        'balance': balance,
        'savings': total_savings
    })

@app.route('/api/savings-goals')
@token_required
def api_savings_goals(current_user):
    goals = SavingsGoal.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'name': g.name,
        'target_amount': g.target_amount,
        'current_amount': g.current_amount,
        'target_date': g.target_date.strftime('%Y-%m-%d') if g.target_date else None
    } for g in goals])

@app.route('/api/transactions')
@token_required
def api_transactions(current_user):
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).limit(5).all()
    return jsonify([{
        'title': t.title,
        'amount': t.amount,
        'category': t.category,
        'date': t.date.strftime('%Y-%b-%d'),
        'type': t.type
    } for t in transactions])
    
@app.route('/api/spending-data')
@token_required
def api_spending_data(current_user):
    current_month = datetime.now().month
    transactions = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        db.extract('month', Transaction.date) == current_month
    ).all()
    
    categories = {}
    for t in transactions:
        if t.category not in categories:
            categories[t.category] = 0
        categories[t.category] += t.amount
    
    return jsonify({
        'labels': list(categories.keys()),
        'data': list(categories.values())
    })

# Profile Routes
@app.context_processor
def inject_user():
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return dict(current_user=current_user)
    return dict(current_user=None)

@app.route('/profile')
@token_required
def profile(current_user):
    return render_template('profile.html', current_user=current_user)

@app.route('/terms')
def terms_of_use():
    return render_template('terms.html')

@app.route('/privacy')
@token_required
def privacy_settings(current_user):
    return render_template('privacy.html', current_user=current_user)

@app.route('/update_privacy', methods=['POST'])
@token_required
def update_privacy(current_user):

    analytics = request.form.get('analytics') == 'on'
    personalization = request.form.get('personalization') == 'on'
    
    
    # current_user.settings.analytics = analytics
    # current_user.settings.personalization = personalization
    # db.session.commit()
    
    flash('Privacy settings updated successfully!', 'success')
    return redirect(url_for('privacy_settings'))

@app.route('/messages')
@token_required
def messages(current_user):
    return render_template('messages.html', current_user=current_user)

@app.route('/language/<lang>')
def change_language(lang):
    session['language'] = lang
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/settings', methods=['GET', 'POST'])
@token_required
def settings(current_user):
    if not current_user.settings:
        current_user.settings = UserSettings()
        db.session.commit()

    if request.method == 'POST':
        
        current_user.settings.currency = request.form.get('currency', '$')
        current_user.settings.theme = request.form.get('theme', 'light')
        current_user.settings.monthly_budget = float(request.form.get('monthly_budget', 0))
        current_user.settings.email_notifications = 'email_notifications' in request.form
        current_user.settings.push_notifications = 'push_notifications' in request.form
        current_user.settings.budget_alerts = 'budget_alerts' in request.form
        
        db.session.commit()
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', settings=current_user.settings, current_user=current_user)

@app.route('/api/settings', methods=['GET', 'PUT'])
@token_required
def api_user_settings(current_user):
    
    if not current_user.settings:
        current_user.settings = UserSettings()
        db.session.commit()

    if request.method == 'GET':
        return jsonify({
            'currency': current_user.settings.currency,
            'theme': current_user.settings.theme,
            'monthly_budget': current_user.settings.monthly_budget,
            'notifications': current_user.settings.notifications,
            'email_notifications': current_user.settings.email_notifications,
            'push_notifications': current_user.settings.push_notifications,
            'budget_alerts': current_user.settings.budget_alerts
        })

    elif request.method == 'PUT':
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            
            current_user.settings.currency = data.get('currency', current_user.settings.currency)
            current_user.settings.theme = data.get('theme', current_user.settings.theme)
            current_user.settings.monthly_budget = float(data.get('monthly_budget', current_user.settings.monthly_budget))
            current_user.settings.notifications = bool(data.get('notifications', current_user.settings.notifications))
            current_user.settings.email_notifications = bool(data.get('email_notifications', current_user.settings.email_notifications))
            current_user.settings.push_notifications = bool(data.get('push_notifications', current_user.settings.push_notifications))
            current_user.settings.budget_alerts = bool(data.get('budget_alerts', current_user.settings.budget_alerts))

            db.session.commit()
            
            return jsonify({
                'message': 'Settings updated successfully',
                'settings': {
                    'currency': current_user.settings.currency,
                    'theme': current_user.settings.theme,
                    'monthly_budget': current_user.settings.monthly_budget,
                    'notifications': current_user.settings.notifications,
                    'email_notifications': current_user.settings.email_notifications,
                    'push_notifications': current_user.settings.push_notifications,
                    'budget_alerts': current_user.settings.budget_alerts
                }
            }), 200

        except ValueError as e:
            return jsonify({'error': 'Invalid data format', 'details': str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update settings', 'details': str(e)}), 500


def init_db():
    with app.app_context():
        if not os.path.exists(app.instance_path):
            os.makedirs(app.instance_path)
        
        db.create_all()
        
       
        if not User.query.first():
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('admin123')
            admin.settings = UserSettings(
                currency='$',
                theme='light',
                monthly_budget=3000.00,
                notifications=True
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
