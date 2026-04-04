from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/panel')
@admin_required
def panel():
    from models import User, FieldAnalysis
    total_users = User.query.count()
    total_farmers = User.query.filter_by(role='farmer').count()
    total_admins = User.query.filter_by(role='admin').count()
    total_analyses = FieldAnalysis.query.count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_analyses = (FieldAnalysis.query
                       .order_by(FieldAnalysis.timestamp.desc())
                       .limit(5).all())
    return render_template('admin/panel.html',
                           total_users=total_users,
                           total_farmers=total_farmers,
                           total_admins=total_admins,
                           total_analyses=total_analyses,
                           recent_users=recent_users,
                           recent_analyses=recent_analyses)


@admin_bp.route('/users')
@admin_required
def users():
    from models import User
    search = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '')
    page = request.args.get('page', 1, type=int)

    query = User.query
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%'))
        )
    if role_filter in ('farmer', 'admin'):
        query = query.filter_by(role=role_filter)

    users_page = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/users.html',
                           users_page=users_page,
                           search=search,
                           role_filter=role_filter)


@admin_bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    from models import User
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'farmer')

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
        else:
            user = User(name=name, email=email, role=role)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'User {name} created successfully.', 'success')
            return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', user=None, action='Add')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    from models import User
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'farmer')
        new_password = request.form.get('password', '').strip()

        if not name or not email:
            flash('Name and email are required.', 'danger')
        elif email != user.email and User.query.filter_by(email=email).first():
            flash('Email already in use.', 'danger')
        else:
            user.name = name
            user.email = email
            user.role = role
            if new_password:
                user.set_password(new_password)
            db.session.commit()
            flash(f'User {name} updated.', 'success')
            return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', user=user, action='Edit')


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    from models import User
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    name = user.name
    db.session.delete(user)
    db.session.commit()
    flash(f'User {name} deleted.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/analyses')
@admin_required
def analyses():
    from models import FieldAnalysis, User
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()

    query = FieldAnalysis.query
    if search:
        query = query.join(User).filter(
            (User.name.ilike(f'%{search}%')) |
            (FieldAnalysis.soil_type.ilike(f'%{search}%')) |
            (FieldAnalysis.recommended_crop.ilike(f'%{search}%'))
        )
    analyses_page = query.order_by(FieldAnalysis.timestamp.desc()).paginate(page=page, per_page=20)
    return render_template('admin/analyses.html', analyses_page=analyses_page, search=search)
