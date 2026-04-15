from flask import Flask, render_template, request, redirect, url_for, session, flash
from main import GestorTareas

app = Flask(__name__)
app.secret_key = 'proyecto_escolar_secreto' 
gestor = GestorTareas()

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        
        usuario_id = gestor.crear_usuario(nombre, email, password)
        
        if usuario_id:
            flash('¡Registro exitoso! Ya puedes iniciar sesión.')
            return redirect(url_for('login'))
        else:
            flash('Ese correo ya existe, intenta con otro.')
            
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        usuario = gestor.verificar_usuario(email, password)
        
        if usuario:
            session['usuario_id'] = usuario['_id']
            session['nombre'] = usuario['nombre']
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos.')
            
    return render_template('login.html')


@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        flash('Tu contraseña ha sido actualizada correctamente. Inicia sesión.')
        return redirect(url_for('login'))
        
    return render_template('recuperar.html')


@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    tareas = gestor.obtener_tareas_usuario(session['usuario_id'])
    
    pendientes = [t for t in tareas if t['estado'] != 'completada']
    completadas = [t for t in tareas if t['estado'] == 'completada']
    
    return render_template('dashboard.html', pendientes=pendientes, completadas=completadas)

@app.route('/agregar_tarea', methods=['POST'])
def agregar_tarea():
    if 'usuario_id' in session:
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        gestor.crear_tarea(session['usuario_id'], titulo, descripcion)
    return redirect(url_for('dashboard'))

@app.route('/completar/<tarea_id>')
def completar_tarea(tarea_id):
    if 'usuario_id' in session:
        gestor.actualizar_estado_tarea(tarea_id, 'completada')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)