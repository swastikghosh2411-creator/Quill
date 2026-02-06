from flask import Flask, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Regexp, EqualTo

from werkzeug.security import generate_password_hash

app = Flask(__name__)
#Secret Key
app.config['SECRET_KEY'] = 'dev-secret-key'

#Adding the database
app.config['SQLALCHEMY_DATABASE_URI'] = (
    "mysql+pymysql://root:admin@localhost/quill"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#Initializing the database
db = SQLAlchemy(app)

# Creating database model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    date_added = db.Column(db.DateTime, default= datetime.utcnow )

    def __repr__(self):
        return f"<User {self.username}>"
    
#Form class
class UserForm(FlaskForm):
    username = StringField(validators= [DataRequired(), Length(min=5, max =20)])
    email = StringField("Enter email here",validators= [DataRequired(), Email (message = "Please enter valid email address!")])
    password = PasswordField("Enter password here",validators= [DataRequired(), 
    Length(min = 8, message = "Password must be atleast 8 characters long"), Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])\S{8,}$', message = 'Password must contain atleast one lowercase, uppercase, special character and number')])
    confirm_password = PasswordField("Re-enter password", validators = [DataRequired(), EqualTo('password', "password must match")])
    submit = SubmitField("Submit")


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/Aboutus')
def Aboutus():
    return render_template("Aboutus.html")
    
@app.route('/Contact')
def Contact():
    return render_template("Contact.html")

@app.route('/signup', methods =['GET','POST'])
def signup():
    username=None
    email = None
    form = UserForm()
    if form.validate_on_submit():
        
        username = form.username.data
        email = form.email.data
        password = generate_password_hash(form.password.data)

        user = User(username = username, email = email, password=password)
        db.session.add(user)
        db.session.commit()
        form.username.data = ''
        form.email.data = ''
        form.password.data= ''
        form.confirm_password.data = ''

        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))
    return render_template("signup.html", username = username, email = email, form = form)

if __name__ == "__main__":
    app.run(debug=True)

