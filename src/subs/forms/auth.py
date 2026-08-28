from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    passphrase = PasswordField("Passphrase", validators=[DataRequired(message="Passphrase is required.")])
    submit = SubmitField("Log in")
