from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and personalization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    settings = db.relationship('UserSettings', backref='user', uselist=False, 
                             cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', 
                                 lazy='dynamic', cascade='all, delete-orphan',
                                 order_by='desc(Transaction.date)')
    budget_goals = db.relationship('BudgetGoal', backref='user', 
                                 lazy='dynamic', cascade='all, delete-orphan',
                                 order_by='BudgetGoal.target_date')

    def set_password(self, password):
        """Create hashed password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Check hashed password"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class UserSettings(db.Model):
    """User preferences and settings"""
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    currency = db.Column(db.String(5), default='$')
    theme = db.Column(db.String(20), default='light')  # 'light' or 'dark'
    notifications = db.Column(db.Boolean, default=True)
    monthly_budget = db.Column(db.Float, default=0.0)
    email_notifications = db.Column(db.Boolean, default=False)
    push_notifications = db.Column(db.Boolean, default=False)
    budget_alerts = db.Column(db.Boolean, default=False)
    language = db.Column(db.String(10), default='en')

    def __repr__(self):
        return f'<UserSettings for user {self.user_id}>'

class Transaction(db.Model):
    """Model for financial transactions (income or expenses)"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Transaction {self.title} - {self.amount}>'

class BudgetGoal(db.Model):
    """Model for budget goals/targets"""
    __tablename__ = 'budget_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0.0)
    target_date = db.Column(db.Date, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<BudgetGoal {self.category} - {self.amount}>'