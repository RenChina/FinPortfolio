from flask import Flask, render_template, redirect, url_for, flash, session, request
from extensions import db, migrate
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, DateField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Portfolio, Deposit
from datetime import date
from dateutil.relativedelta import relativedelta

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)

    class LoginForm(FlaskForm):
        email = StringField('Почта', validators=[DataRequired(), Email()])
        password = PasswordField('Пароль', validators=[DataRequired()])
        submit = SubmitField('Войти')

    class RegistrationForm(FlaskForm):
        email = StringField('Почта', validators=[DataRequired(), Email()])
        password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
        submit = SubmitField('Зарегистрироваться')

    class DepositForm(FlaskForm):
        amount = DecimalField('Количество', validators=[DataRequired()])
        interest_rate = DecimalField('Процентная ставка', validators=[DataRequired()])
        duration_months = IntegerField('Продолжительность(месяц)', validators=[DataRequired()])
        start_date = DateField('Начало ставки', format='%Y-%m-%d', validators=[DataRequired()])
        submit = SubmitField('Принять')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and check_password_hash(user.password, form.password.data):
                session['user_id'] = user.id
                flash('Успешно зарегались', 'success')
                return redirect(url_for('profile', user_id=user.id))
            else:
                flash('Не найдена почта или пароль.', 'danger')
        return render_template('login.html', form=form)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
            new_user = User(email=form.email.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация успешна!!', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/profile/<int:user_id>')
    def profile(user_id):
        user = User.query.get_or_404(user_id)
        portfolios = Portfolio.query.filter_by(user_id=user.id).all()
        deposits = Deposit.query.filter_by(user_id=user.id).all()
        tax_rate = 0.13  # Пример налоговой ставки
        tax = calculate_tax(deposits, tax_rate)
        return render_template('profile.html', user=user, portfolios=portfolios, deposits=deposits, tax_rate=tax_rate, tax=tax)

    @app.route('/deposit', methods=['GET', 'POST'])
    def deposit():
        form = DepositForm()
        if form.validate_on_submit():
            new_deposit = Deposit(
                amount=form.amount.data,
                interest_rate=form.interest_rate.data,
                duration_months=form.duration_months.data,
                start_date=form.start_date.data,
                user_id=session['user_id']
            )
            db.session.add(new_deposit)
            db.session.commit()
            flash('Депозит добавлен!!', 'success')
            return redirect(url_for('profile', user_id=session['user_id']))
        return render_template('deposit.html', form=form)

    @app.route('/close_deposit/<int:deposit_id>', methods=['POST'])
    def close_deposit(deposit_id):
        deposit = Deposit.query.get_or_404(deposit_id)
        if deposit.user_id != session.get('user_id'):
            flash('Не найдено вкладов', 'danger')
            return redirect(url_for('profile', user_id=session['user_id']))
        db.session.delete(deposit)
        db.session.commit()
        flash('Депозит закрыт', 'success')
        return redirect(url_for('profile', user_id=session['user_id']))

    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        flash('Вы покинули профиль', 'success')
        return redirect(url_for('index'))


    def calculate_tax(deposits, tax_rate):
        total_tax = 0
        for deposit in deposits:
            end_date = deposit.start_date + relativedelta(months=+deposit.duration_months)
            if end_date.year == date.today().year:
                interest = (deposit.amount * deposit.interest_rate * (deposit.duration_months * 30.44)) / 100
                total_tax += interest * tax_rate
        return total_tax

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
