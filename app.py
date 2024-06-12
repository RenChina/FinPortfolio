from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from extensions import db, migrate
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, IntegerField, DateField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Deposit, FamilyDeposit, ClosedDeposit
from decimal import Decimal


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

    class FamilyDepositForm(FlaskForm):
        email = StringField('Почта пользователя', validators=[DataRequired(), Email()])
        submit = SubmitField('Добавить')

    @app.route('/')
    def index():
        form = LoginForm()
        return render_template('index.html', form=form)

    @app.route('/', methods=['POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user is None:
                flash('Пользователь не найден.', 'danger')
            elif check_password_hash(user.password, form.password.data):
                session['user_id'] = user.id
                flash('Успешно зарегистрировались', 'success')
                return redirect(url_for('profile', user_id=user.id))
            else:
                flash('Неправильная почта или пароль.', 'danger')

        return render_template('index.html', form=form)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():
            # Проверяем, существует ли пользователь с таким email
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Пользователь с такой почтой уже зарегистрирован.', 'danger')
                return redirect(url_for('register'))

            # Хешируем пароль и создаем нового пользователя
            hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
            new_user = User(email=form.email.data, password=hashed_password)
            db.session.add(new_user)

            try:
                db.session.commit()
                flash('Регистрация успешна!', 'success')
            except:
                db.session.rollback()
                flash('Ошибка при регистрации, попробуйте снова.', 'danger')

        return render_template('register.html', form=form)

    @app.route('/profile/<int:user_id>', methods=['GET'])
    def profile(user_id):
        user = User.query.get_or_404(user_id)
        if not user:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('index'))

        deposits = Deposit.query.filter_by(user_id=user.id).all()
        closed_deposits = ClosedDeposit.query.filter_by(user_id=user.id).all()
        family_deposits = FamilyDeposit.query.filter_by(owner_id=user.id).all()

        tax_rate = 0.13  # Этот значение теперь будет преобразовано в Decimal в функции calculate_tax
        tax = calculate_tax(deposits, tax_rate)

        family_deposits_data = []
        for family_deposit in family_deposits:
            member = User.query.get(family_deposit.member_id)
            member_deposits = Deposit.query.filter_by(user_id=member.id).all()
            family_deposits_data.append({
                'id': family_deposit.id,
                'member': member,
                'deposits': member_deposits
            })

        if request.args.get('section') == 'closed_deposits':
            return render_template('partials/closed_deposits.html', closed_deposits=closed_deposits)

        return render_template('profile.html', user=user, deposits=deposits,
                               closed_deposits=closed_deposits, family_deposits_data=family_deposits_data,
                               tax_rate=tax_rate,
                               tax=tax)

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
            flash('Депозит добавлен!', 'success')
            return redirect(url_for('profile', user_id=session['user_id']))

        return render_template('deposit.html', form=form)

    @app.route('/close_deposit/<int:deposit_id>', methods=['POST'])
    def close_deposit(deposit_id):
        deposit = Deposit.query.get_or_404(deposit_id)
        if deposit.user_id != session.get('user_id'):
            flash('Нет доступа к вкладу', 'danger')
            return redirect(url_for('profile', user_id=session['user_id']))

        closed_deposit = ClosedDeposit(
            amount=deposit.amount,
            interest_rate=deposit.interest_rate,
            duration_months=deposit.duration_months,
            start_date=deposit.start_date,
            user_id=deposit.user_id
        )

        db.session.add(closed_deposit)
        db.session.delete(deposit)
        db.session.commit()

        flash('Депозит закрыт', 'success')
        return redirect(url_for('profile', user_id=session['user_id']))

    @app.route('/delete_closed_deposit/<int:deposit_id>', methods=['POST'])
    def delete_closed_deposit(deposit_id):
        closed_deposit = ClosedDeposit.query.get_or_404(deposit_id)
        if closed_deposit.user_id != session.get('user_id'):
            return {'error': 'Нет доступа к вкладу'}, 403

        db.session.delete(closed_deposit)
        db.session.commit()
        return {'success': True}, 200

    @app.route('/add_family_deposit', methods=['GET', 'POST'])
    def add_family_deposit():
        form = FamilyDepositForm()
        if form.validate_on_submit():
            member = User.query.filter_by(email=form.email.data).first()
            if member:
                new_family_deposit = FamilyDeposit(
                    owner_id=session['user_id'],
                    member_id=member.id
                )
                db.session.add(new_family_deposit)
                db.session.commit()
                flash('Семейный вклад добавлен!', 'success')
                return redirect(url_for('profile', user_id=session['user_id']))
            else:
                flash('Пользователь не найден', 'danger')
        return render_template('add_family_deposit.html', form=form)

    @app.route('/delete_family_deposit/<int:family_deposit_id>', methods=['POST'])
    def delete_family_deposit(family_deposit_id):
        family_deposit = FamilyDeposit.query.get_or_404(family_deposit_id)
        if family_deposit.owner_id != session.get('user_id'):
            return jsonify({'error': 'Нет доступа к этому семейному вкладу'}), 403
        db.session.delete(family_deposit)
        db.session.commit()
        return jsonify({'success': True}), 200

    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        flash('Вы вышли из профиля', 'success')
        return redirect(url_for('index'))

    def calculate_tax(deposits, tax_rate):
        total_tax = Decimal(0)
        tax_rate = Decimal(tax_rate)  # Преобразуем tax_rate в Decimal

        for deposit in deposits:
            proverka_na_nalog = deposit.amount * Decimal(0.15)
            total_value = deposit.amount * (((deposit.interest_rate / 100) / Decimal(12))) * deposit.duration_months
            if total_value > proverka_na_nalog:
                total_tax += (total_value - proverka_na_nalog) * tax_rate

        return total_tax

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)