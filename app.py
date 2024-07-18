from flask import Flask, flash, render_template, request, redirect, url_for, session, make_response
from flask_sqlalchemy import SQLAlchemy 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from io import StringIO
import random
import csv



app = Flask(__name__)
app.config['SECRET_KEY'] = 'pivon'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banking_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

#User model
class User(db.Model):
  id = db.Column(db.Integer, primary_key = True)
  username = db.Column(db.String(150), nullable=False, unique = True)
  password = db.Column(db.String(150),nullable = False)
  balance = db.Column(db.Float, default=0.00)
  account_number = db.Column(db.String(6), nullable = False, unique = True)
  full_name = db.Column(db.String(150), nullable=False)
  id_number = db.Column(db.Integer, nullable=False, unique=True)
  email = db.Column(db.String(50), nullable=False, unique=True)
  address = db.Column(db.String(50), nullable=True)
  phone_number = db.Column(db.Integer, nullable=False, unique=True)
  transaction = db.relationship('Transaction', backref='account_holder', lazy=True)
  
#Transaction model
class Transaction(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  type = db.Column(db.String(50), nullable=False) 
  amount = db.Column(db.Float, nullable=False)
  timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
  description = db.Column(db.String(250), nullable=True) 
  
  
  
with app.app_context():
  db.create_all()



@app.route('/')  
def welcome():
  return render_template('Welcome.html')
  
#generate a random Account  Number
def generate_account_number():
  prefix = 'pI'
  suffix = ''.join(random.choices('0123456789', k=4)) 
  raw_account_number = prefix + suffix
  account_number = '-'.join([raw_account_number[i:i+2] for i in range(0, len(raw_account_number), 2)])
  
  return account_number 
  
  
#Registration route 
@app.route('/register', methods = ['GET', 'POST'])
def register ():
  if request.method == 'POST':
    username = request.form.get('username') 
    password = request.form.get('password') 
    confirm_password = request.form.get('confirm_password') 
    account_number = generate_account_number ()
    full_name = request.form.get('full_name') 
    id_number = request.form['id_number']
    email = request.form['email']
    address = request.form['address']
    phone_number = request.form['phone_number']
    
    #Check if user exists
    if User.query.filter_by(username=username).first():
      flash('Username already exists. Please choose a different username', 'error')
      return redirect(url_for('register'))
      
    #Check if password match
    if password != confirm_password:
      flash('Passwords do not match. Please try again.', 'error')
      return redirect(url_for('register'))
    
    account_number = generate_account_number ()
    while User.query.filter_by(account_number = account_number).first():
      account_number = generate_account_number()
    
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password, account_number=account_number, full_name=full_name, id_number=id_number, email=email, address=address, phone_number=phone_number)
    db.session.add(new_user)
    db.session.commit()
    flash('Account created successfully', 'success')
    session['username'] = username
    return redirect(url_for('home'))
  return render_template('register.html')
  
  
#Login route
@app.route('/login',methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    username = request.form.get('username') 
    password = request.form.get('password') 

    if not username or not password:
      flash('Enter both username and password please', 'error')
      return render_template('login.html')
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
      session['username'] = user.username
      flash('Logged in successfully', 'success')
      return redirect(url_for('home'))
    else:
      flash('Invalid username or password. Try again', 'error')
      return render_template('login.html')
  return render_template('login.html')
  
  
#Logout route
@app.route('/logout')
def logout():
  session.pop('username', None)
  flash('Thank you for using Pivon-Tech Bank. Have a nice time', 'success')
  return redirect(url_for('home'))
  
  
#Home Route
@app.route('/home')
def home():
  if 'username' not in session:
    return redirect(url_for('login'))
  username = session['username']
  user = User.query.filter_by(username=username).first()
  return render_template('home.html', user=user) 

#Deposit Route
@app.route('/deposit', methods=['GET', 'POST'])
def deposit():
  if 'username' not in session:
    return redirect(url_for('login'))
  if request.method == 'POST':
    amount = float(request.form['amount'])
    print (amount) 
    username = session['username']
    user = User.query.filter_by(username=username).first()
    user.balance += amount
    transaction = Transaction(user_id=user.id, type='Deposit', amount=amount)
    db.session.add(transaction)
    db.session.commit()
    flash('Deposit successful!', 'success')
    return redirect(url_for('home'))
  return render_template('deposit.html')


#Withdraw Route
@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
  if 'username' not in session:
    return redirect(url_for('login'))
  if request.method == 'POST':
    amount = float(request.form.get('amount')) 
    username = session['username']
    user = User.query.filter_by(username=username).first()
    if user.balance >= amount:
      user.balance -= amount
      transaction = Transaction(user_id=user.id, type='Withdrawal', amount=amount)
      db.session.add(transaction)
      db.session.commit()
      flash('Withdrawal successful!', 'success')
      return redirect(url_for('home'))
    else:
      flash('Insufficient funds in your account. Try again!', 'error')
      return render_template('withdraw.html')
  return render_template('withdraw.html')
  
#Transfer Route
@app.route('/transfer',methods=['GET', 'POST'])
def transfer():
  if 'username' not in session:
    return redirect(url_for('login'))
  if request.method == 'POST':
    username = session ['username']
    user = User.query.filter_by(username=username).first()
    recipient_account_number = request.form['account_number']
    amount = float(request.form['amount'])
    
    if user.balance < amount :
      flash('Insufficient funds in your account', 'error')
      return render_template('transfer.html')
    
    recipient = User.query.filter_by(account_number=recipient_account_number).first()
    if not recipient:
      flash('Invalid Account Number!', 'error')
      return render_template('transfer.html')
      
    user.balance-=amount
    recipient.balance+=amount
      
    transfer_out = Transaction(user_id=user.id, type='Sent', amount=amount)
    transfer_in = Transaction(user_id=recipient.id, type='Received', amount=amount)
      
    db.session.add(transfer_out)
    db.session.add(transfer_in)
    db.session.commit() 
     
    flash('Sent successfully', 'success') 
    return redirect(url_for('home'))
  return render_template('transfer.html')


#Transaction History Route
@app.route('/transaction_history')
def transaction_history():
  if 'username' not in session:
    return redirect(url_for('login'))
  username = session['username'] 
  user = User.query.filter_by(username=username).first()
  transaction = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
  return render_template('transaction_history.html',transaction=transaction,user=user)
  
#Terms and conditions route
@app.route('/terms')
def terms():
  return render_template('terms.html')
  
  
#Investors route
@app.route('/investors')
def investors():
  return render_template('investors.html')
  
#Manage Account route
@app.route('/manage_account', methods=['GET', 'POST'])
def manage_account():
  if 'username' not in session:
    return redirect(url_for ('login'))
  if request.method == 'POST':
    action = request.form['action']
    if action == 'change_password':
      return redirect(url_for('change_password'))
    elif action == 'delete_account':
      return redirect(url_for('delete_account'))
    elif action == 'profile':
      return redirect(url_for('profile'))
  return render_template('manage_account.html')
  
#change password route
@app.route('/change_password', methods=['GET', 'POST']) 
def change_password():
  if 'username' not in session:
    return redirect(url_for('login'))
  
  if request.method == 'POST':
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if not check_password_hash(user.password, current_password): 
      flash('Incorrect current password', 'error')
      return render_template('change_password.html') 
    if new_password != confirm_password:
      flash('Passwords do not match!')
      return render_template('change_password.html') 
    
    user.password = generate_password_hash(new_password)
    db.session.commit()
    flash('Password changed successfully', 'success')
    return redirect(url_for('home'))
    
  return render_template('change_password.html')
      
#Delete Account route
@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
  if 'username' not in session:
    return redirect(url_for('login'))
  
  if request.method == 'POST':
    username = session['username']
    user = User.query.filter_by(username=username).first()
    
    db.session.delete(user)
    db.session.commit()
    flash('Account Deleted, BYE!', 'error')
    return redirect(url_for('login'))
    
  return render_template('delete_account.html')
 
#Download transactions 
@app.route('/transaction_history/download', methods=['GET'])
def download_transaction_history():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    user = User.query.filter_by(username=username).first()
    transactions = Transaction.query.filter_by(user_id=user.id).all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Type', 'Amount'])
    for transaction in transactions:
        cw.writerow([transaction.timestamp, transaction.type, transaction.amount])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=transaction_history.csv"
    output.headers["Content-type"] = "text/csv"
    return output
    
#Update Profile information route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
  if 'username' not in session:
    redirect(url_for('login'))
    
  if request.method == 'POST':
    full_name = request.form['full_name']
    id_number = request.form['id_number']
    email = request.form['email']
    address = request.form['address']
    phone_number = request.form['phone_number']
    
    
    db.session.commit()
    flash('Details updated successfully', 'success')
    return redirect(url_for('home'))
  
  return render_template('profile.html')

#Show profile information route
@app.route('/profile_info', methods=['GET', 'POST'])
def profile_info():
  if 'username' not in session:
    return redirect(url_for('login'))
  
  username = session['username']
  user = User.query.filter_by(username=username).first()
 
  if not user:
   return redirect(url_for('home'))
  
  return render_template('profile_info.html', user=user)


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8757, debug=True)
  
