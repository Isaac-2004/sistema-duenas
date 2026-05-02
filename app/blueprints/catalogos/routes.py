from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth import login_required
from app.db import query, execute

catalogos_bp = Blueprint('catalogos', __name__)


@catalogos_bp.before_request
@login_required
def require_login():
    pass


# ── Categorías ──────────────────────────────────────────────────────────────

@catalogos_bp.route('/categorias')
def categorias_lista():
    cats = query("SELECT * FROM categorias ORDER BY nombre")
    return render_template('catalogos/categorias_lista.html', categorias=cats)


@catalogos_bp.route('/categorias/nueva', methods=['GET', 'POST'])
def categorias_nueva():
    if request.method == 'POST':
        execute("INSERT INTO categorias (nombre,descripcion) VALUES (%s,%s)",
                (request.form['nombre'].strip(), request.form.get('descripcion', '').strip() or None))
        flash('Categoría creada.', 'success')
        return redirect(url_for('catalogos.categorias_lista'))
    return render_template('catalogos/categorias_form.html', categoria=None)


@catalogos_bp.route('/categorias/<int:id>/editar', methods=['GET', 'POST'])
def categorias_editar(id):
    cat = query("SELECT * FROM categorias WHERE id_categoria=%s", (id,), fetchone=True)
    if request.method == 'POST':
        execute("UPDATE categorias SET nombre=%s,descripcion=%s,estado=%s WHERE id_categoria=%s",
                (request.form['nombre'].strip(),
                 request.form.get('descripcion', '').strip() or None,
                 int(request.form.get('estado', 1)), id))
        flash('Categoría actualizada.', 'success')
        return redirect(url_for('catalogos.categorias_lista'))
    return render_template('catalogos/categorias_form.html', categoria=cat)


# ── Unidades de Medida ───────────────────────────────────────────────────────

@catalogos_bp.route('/unidades')
def unidades_lista():
    unidades = query("SELECT * FROM unidades_medida ORDER BY nombre")
    return render_template('catalogos/unidades_lista.html', unidades=unidades)


@catalogos_bp.route('/unidades/nueva', methods=['GET', 'POST'])
def unidades_nueva():
    if request.method == 'POST':
        execute("INSERT INTO unidades_medida (nombre,abreviatura) VALUES (%s,%s)",
                (request.form['nombre'].strip(), request.form['abreviatura'].strip()))
        flash('Unidad creada.', 'success')
        return redirect(url_for('catalogos.unidades_lista'))
    return render_template('catalogos/unidades_form.html', unidad=None)


@catalogos_bp.route('/unidades/<int:id>/editar', methods=['GET', 'POST'])
def unidades_editar(id):
    unidad = query("SELECT * FROM unidades_medida WHERE id_unidad=%s", (id,), fetchone=True)
    if request.method == 'POST':
        execute("UPDATE unidades_medida SET nombre=%s,abreviatura=%s WHERE id_unidad=%s",
                (request.form['nombre'].strip(), request.form['abreviatura'].strip(), id))
        flash('Unidad actualizada.', 'success')
        return redirect(url_for('catalogos.unidades_lista'))
    return render_template('catalogos/unidades_form.html', unidad=unidad)
