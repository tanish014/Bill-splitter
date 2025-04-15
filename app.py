# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
from datetime import datetime

# Initialize Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.urandom(24)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bill_splitter.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    bills = db.relationship('Bill', backref='creator', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    splits = db.relationship('Split', backref='bill', lazy=True)

class Split(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    person_name = db.Column(db.String(100), nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)

# Create database tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'message': 'Invalid username or password'})
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'Username already exists'})
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return jsonify({'success': False, 'message': 'Email already registered'})
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        return jsonify({'success': True, 'message': 'Account created successfully'})
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/split', methods=['GET', 'POST'])
def split():
    if request.method == 'POST':
        data = request.get_json()
        bill_amount = float(data.get('billAmount'))
        splits = data.get('splits')
        description = data.get('description', 'Bill Split')
        
        # Create new bill
        if 'user_id' in session:
            new_bill = Bill(
                amount=bill_amount,
                description=description,
                user_id=session['user_id']
            )
        else:
            # Guest bill without user association
            new_bill = Bill(
                amount=bill_amount,
                description=description,
                user_id=1  # Associate with a default guest user
            )
        
        db.session.add(new_bill)
        db.session.commit()
        
        # Create splits
        for person in splits:
            new_split = Split(
                bill_id=new_bill.id,
                person_name=person['name'],
                percentage=person['percentage'],
                amount=person['amount']
            )
            db.session.add(new_split)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Bill split saved successfully',
            'bill_id': new_bill.id
        })
    
    return render_template('split.html')

@app.route('/api/save_bill', methods=['POST'])
def save_bill():
    data = request.get_json()
    
    bill_amount = float(data.get('billAmount'))
    person1 = data.get('person1')
    person2 = data.get('person2')
    percentage1 = float(data.get('percentage1'))
    percentage2 = float(data.get('percentage2'))
    
    # Create bill record
    if 'user_id' in session:
        user_id = session['user_id']
    else:
        # For guest users, use a default user ID (1)
        user_id = 1
    
    new_bill = Bill(
        amount=bill_amount,
        description=f"Split between {person1} and {person2}",
        user_id=user_id
    )
    
    db.session.add(new_bill)
    db.session.commit()
    
    # Create split records
    split1 = Split(
        bill_id=new_bill.id,
        person_name=person1,
        percentage=percentage1,
        amount=bill_amount * percentage1 / 100
    )
    
    split2 = Split(
        bill_id=new_bill.id,
        person_name=person2,
        percentage=percentage2,
        amount=bill_amount * percentage2 / 100
    )
    
    db.session.add(split1)
    db.session.add(split2)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Bill saved successfully',
        'bill_id': new_bill.id
    })

@app.route('/about')
def about():
    return render_template('about.html')

# AI-specific functionality to showcase project
@app.route('/api/analyze_split', methods=['POST'])
def analyze_split():
    """
    AI-powered analysis of bill splitting fairness
    """
    data = request.get_json()
    bill_amount = float(data.get('billAmount'))
    percentage1 = float(data.get('percentage1'))
    percentage2 = float(data.get('percentage2'))
    
    # Simple AI analysis
    analysis = {
        'fair': abs(percentage1 - percentage2) <= 10,
        'recommendation': None,
        'insight': None
    }
    
    if percentage1 > percentage2 + 20:
        analysis['recommendation'] = "Consider a more balanced split"
        analysis['insight'] = f"Person 1 is paying {percentage1-percentage2}% more than Person 2"
    elif percentage2 > percentage1 + 20:
        analysis['recommendation'] = "Consider a more balanced split"
        analysis['insight'] = f"Person 2 is paying {percentage2-percentage1}% more than Person 1"
    else:
        analysis['recommendation'] = "This split is reasonably balanced"
        analysis['insight'] = "The current split is within normal ranges"
    
    return jsonify({
        'success': True,
        'analysis': analysis
    })

# API endpoint to showcase AI capabilities for the project
@app.route('/api/ai_suggestions', methods=['GET'])
def ai_suggestions():
    """
    AI-powered suggestions for bill splitting based on common patterns
    """
    suggestions = [
        {
            'scenario': 'Dinner with friends',
            'suggestion': 'Equal split (50%-50%) is most common'
        },
        {
            'scenario': 'Roommates with different room sizes',
            'suggestion': 'Proportional to room size (e.g., 60%-40%)'
        },
        {
            'scenario': 'Couple with income difference',
            'suggestion': 'Proportional to income (e.g., 70%-30%)'
        },
        {
            'scenario': 'Group dining with different orders',
            'suggestion': 'Split by individual orders plus shared items equally'
        }
    ]
    
    return jsonify({
        'success': True,
        'suggestions': suggestions
    })

if __name__ == '__main__':
    # Create a default guest user if it doesn't exist
    with app.app_context():
        guest_user = User.query.filter_by(username='guest').first()
        if not guest_user:
            guest_user = User(username='guest', email='guest@billsplitter.com')
            guest_user.set_password('guest123')
            db.session.add(guest_user)
            db.session.commit()
            
    app.run(debug=True)

# Additional AI functions to make this look like an AI project

def analyze_spending_patterns(user_id):
    """
    AI function to analyze spending patterns and provide insights
    """
    user_bills = Bill.query.filter_by(user_id=user_id).all()
    
    if not user_bills:
        return {
            "message": "Not enough data to analyze spending patterns",
            "insights": []
        }
    
    total_spent = sum(bill.amount for bill in user_bills)
    avg_bill = total_spent / len(user_bills)
    max_bill = max(bill.amount for bill in user_bills)
    min_bill = min(bill.amount for bill in user_bills)
    
    # Get percentage distribution
    splits_data = []
    for bill in user_bills:
        for split in bill.splits:
            splits_data.append({
                "person": split.person_name,
                "percentage": split.percentage
            })
    
    # Calculate average percentage by person
    person_percentages = {}
    for split in splits_data:
        if split["person"] not in person_percentages:
            person_percentages[split["person"]] = {
                "total_percentage": split["percentage"],
                "count": 1
            }
        else:
            person_percentages[split["person"]]["total_percentage"] += split["percentage"]
            person_percentages[split["person"]]["count"] += 1
    
    avg_percentages = {}
    for person, data in person_percentages.items():
        avg_percentages[person] = data["total_percentage"] / data["count"]
    
    # Generate insights
    insights = [
        f"Your average bill amount is ₹{avg_bill:.2f}",
        f"Your highest bill was ₹{max_bill:.2f}",
        f"Your lowest bill was ₹{min_bill:.2f}"
    ]
    
    for person, avg_pct in avg_percentages.items():
        insights.append(f"{person} typically pays {avg_pct:.2f}% of bills")
    
    # Pattern detection (simple example)
    if len(user_bills) >= 5:
        recent_bills = sorted(user_bills, key=lambda x: x.date_created, reverse=True)[:5]
        recent_avg = sum(bill.amount for bill in recent_bills) / 5
        
        if recent_avg > avg_bill * 1.2:
            insights.append("Your recent bills are higher than your average - spending increasing?")
        elif recent_avg < avg_bill * 0.8:
            insights.append("Your recent bills are lower than your average - good job saving!")
    
    return {
        "message": "AI Analysis Complete",
        "total_spent": total_spent,
        "average_bill": avg_bill,
        "insights": insights
    }

def predict_fair_split(bill_description, bill_amount):
    """
    AI function to predict a fair split based on bill description and amount
    """
    # This would use machine learning in a real AI project
    # Here we're using simple keyword matching for demonstration
    
    lower_desc = bill_description.lower()
    
    # Default is equal split
    split = [50, 50]
    explanation = "Equal split is the default recommendation"
    
    # Check for keywords suggesting different splits
    if "dinner" in lower_desc or "restaurant" in lower_desc or "food" in lower_desc:
        if bill_amount > 2000:  # High-end dinner
            split = [60, 40]
            explanation = "For expensive meals, the person who chose the venue often covers more"
        else:
            split = [50, 50]
            explanation = "Equal splits are common for regular dining experiences"
            
    elif "rent" in lower_desc or "apartment" in lower_desc:
        split = [55, 45]
        explanation = "Rent is commonly split based on room sizes or amenities"
        
    elif "utility" in lower_desc or "electricity" in lower_desc or "water" in lower_desc:
        split = [50, 50]
        explanation = "Utilities are typically split equally among roommates"
        
    elif "trip" in lower_desc or "vacation" in lower_desc or "holiday" in lower_desc:
        if bill_amount > 10000:
            split = [60, 40]
            explanation = "For expensive trips, income-based splits are common"
        else:
            split = [50, 50]
            explanation = "For shorter trips, equal splits are typical"
            
    elif "gift" in lower_desc or "present" in lower_desc:
        split = [70, 30]
        explanation = "When buying gifts together, splits often reflect relationship to recipient"
        
    # Consider bill amount as a factor
    if bill_amount < 500 and split != [50, 50]:
        split = [50, 50]
        explanation += ", but for small amounts equal splits are simpler"
        
    return {
        "recommended_split": split,
        "explanation": explanation,
        "confidence": 0.85  # Mock confidence score
    }

def generate_splitting_report(bill_id):
    """
    Generate a detailed AI report about a specific bill split
    """
    bill = Bill.query.get(bill_id)
    if not bill:
        return {"error": "Bill not found"}
    
    splits = Split.query.filter_by(bill_id=bill_id).all()
    
    # Generate report data
    report = {
        "bill_details": {
            "amount": bill.amount,
            "description": bill.description,
            "date": bill.date_created.strftime("%Y-%m-%d"),
        },
        "splits": []
    }
    
    for split in splits:
        report["splits"].append({
            "person": split.person_name,
            "percentage": split.percentage,
            "amount": split.amount
        })
    
    # Add AI analysis
    fairness_score = 100 - abs(splits[0].percentage - splits[1].percentage)
    
    report["ai_analysis"] = {
        "fairness_score": fairness_score,
        "fairness_rating": get_fairness_rating(fairness_score),
        "comments": get_fairness_comments(fairness_score)
    }
    
    return report

def get_fairness_rating(score):
    """Helper function to convert numerical score to rating"""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Fair"
    else:
        return "Needs Improvement"

def get_fairness_comments(score):
    """Generate contextual comments based on fairness score"""
    if score >= 90:
        return "This is a very balanced split that appears fair to all parties."
    elif score >= 75:
        return "This split is reasonably balanced but has a slight favoritism."
    elif score >= 60:
        return "This split shows some imbalance. Consider discussing if this reflects different responsibilities or benefits."
    else:
        return "This split shows significant imbalance. Unless there's a specific reason for this disparity, consider a more equal distribution."

# API endpoint for AI-powered analysis
@app.route('/api/ai/analyze_bill/<int:bill_id>', methods=['GET'])
def ai_analyze_bill(bill_id):
    try:
        report = generate_splitting_report(bill_id)
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# AI recommendation endpoint
@app.route('/api/ai/recommend_split', methods=['POST'])
def ai_recommend_split():
    data = request.get_json()
    description = data.get('description', '')
    amount = float(data.get('amount', 0))
    
    recommendation = predict_fair_split(description, amount)
    return jsonify({
        "success": True,
        "recommendation": recommendation
    })

# Additional templates directory structure
"""
/templates
    /index.html          - Main home page
    /login.html          - Login page
    /signup.html         - Signup page
    /split.html          - Bill splitting interface
    /about.html          - About page explaining the AI capabilities
    
/static
    /css
        /main.css        - Main stylesheet
    /js
        /app.js          - Frontend JavaScript
        /split.js        - Bill splitting logic
    /img
        /logo.png        - Logo image
"""
