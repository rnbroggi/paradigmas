#!/usr/bin/env python
import csv
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, session, abort
from flask_bootstrap import Bootstrap
# from flask_moment import Moment
from flask_script import Manager
from forms import LoginForm, SaludarForm, RegistrarForm, BuscarForm
from operator import itemgetter
from collections import OrderedDict
import itertools


app = Flask(__name__)
manager = Manager(app)
bootstrap = Bootstrap(app)
# moment = Moment(app)

app.config['SECRET_KEY'] = 'un string que funcione como llave'

# Chequeo que CSV este correcto segun lo requerido
# Devuelve cada linea del CSV como lista dentro de una lista
def procesar_csv(mi_archivo):
    lista_de_compras = []
    try:
        with open(mi_archivo) as archivo:
            archivo_csv = csv.reader(archivo)
            compra = next(archivo_csv)
            compra = next(archivo_csv)
            while compra:
                # Chequeo que el campo de CANTIDAD este escrito con numeros enteros
                try:
                    compra[3] = int(compra[3])
                except ValueError:
                    print(f'La cantidad de unidades del producto {compra[1]} debe ser representado con un numero entero')
                    abort(500)

                # Chequeo que el campo de PRECIO este escrito con numeros decimales
                try:
                    if '.' not in compra[4]:
                        print(f'El precio del producto {compra[1]} debe ser representado con un numero decimal (utilizando un ".")')
                        abort(500)
                    compra[4] = float(compra[4])
                except ValueError:
                    print(f'El precio del producto {compra[1]} debe ser representado con un numero decimal (utilizando un ".")')
                    abort(500)

                # Chequeo que la cantidad de campos del CSV sea el indicado
                if len(compra) != 5:
                    print("Compruebe la cantidad de campos por registro en su archivo CSV")
                    abort(500)

                # Chequeo que el campo CODIGO este compuesto por tres caracteres y tres digitos
                if len(compra[0]) == 6:
                    parte_alfabetica = compra[0][slice(0,3)].upper()
                    chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

                    for letra in parte_alfabetica:
                        if letra not in chars:
                            print(f"El codigo de la compra {compra[1]} debe estar compuesto por tres letras y luego tres digitos")
                            abort(500)

                    try:
                        parte_numerica = int(compra[0][slice(3,6)])

                        if parte_numerica < 100:
                            parte_numerica += 100

                        if len(str(parte_numerica)) != 3:
                            print(f"El codigo de la compra {compra[1]} debe estar compuesto por tres letras y luego tres digitos")
                            abort(500)

                    except:
                        print(f"El codigo de la compra {compra[1]} debe estar compuesto por tres letras y luego tres digitos")
                        abort(500)
                else:
                    print(f"El codigo de la compra {compra[1]} debe estar compuesto por tres letras y luego tres digitos")
                    abort(500)

                lista_de_compras.append(compra)
                compra = next(archivo_csv, None)

            return lista_de_compras
    except IOError:
        print("No se ha encontrado un archivo de datos")
        abort(500)

@app.route('/')
def index():
    return render_template('index.html', fecha_actual=datetime.utcnow())


@app.route('/saludar', methods=['GET', 'POST'])
def saludar():
    formulario = SaludarForm()
    if formulario.validate_on_submit():
        print(formulario.usuario.name)
        return redirect(url_for('saludar_persona', usuario=formulario.usuario.data))
    return render_template('saludar.html', form=formulario)


@app.route('/saludar/<usuario>')
def saludar_persona(usuario):
    return render_template('usuarios.html', nombre=usuario)


@app.errorhandler(404)
def no_encontrado(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def error_interno(e):
    return render_template('500.html'), 500


@app.route('/ingresar', methods=['GET', 'POST'])
def ingresar():
    formulario = LoginForm()
    if formulario.validate_on_submit():
        with open('usuarios') as archivo:
            archivo_csv = csv.reader(archivo)
            registro = next(archivo_csv)
            while registro:
                if formulario.usuario.data == registro[0] and formulario.password.data == registro[1]:
                    flash('Bienvenido')
                    session['username'] = formulario.usuario.data
                    return render_template('ingresado.html')
                registro = next(archivo_csv, None)
            else:
                flash('Revisá nombre de usuario y contraseña')
                return redirect(url_for('ingresar'))
    return render_template('login.html', formulario=formulario)


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    formulario = RegistrarForm()
    if formulario.validate_on_submit():
        if formulario.password.data == formulario.password_check.data:
            with open('usuarios', 'a+') as archivo:
                archivo_csv = csv.writer(archivo)
                registro = [formulario.usuario.data, formulario.password.data]
                archivo_csv.writerow(registro)
            flash('Usuario creado correctamente')
            return redirect(url_for('ingresar'))
        else:
            flash('Las passwords no matchean')
    return render_template('registrar.html', form=formulario)


@app.route('/secret', methods=['GET'])
def secreto():
    if 'username' in session:
        return render_template('private.html', username=session['username'])
    else:
        return render_template('sin_permiso.html')


@app.route('/logout', methods=['GET'])
def logout():
    if 'username' in session:
        session.pop('username')
        return render_template('logged_out.html')
    else:
        return redirect(url_for('index'))


# Renderiza el listado de compras del CSV para presentarlo en la pagina
@app.route('/listado', methods=['GET'])
def listado():
    if 'username' not in session:
        flash('Debes estar logeado para realizar consultas')
        return redirect(url_for('ingresar'))
    else:
        lista_de_compras = procesar_csv('datos.csv')
        return render_template('listado.html', listado=lista_de_compras, username=session['username'])


# Genera una lista de los clientes para ser mostrada en la pagina y un buscador
@app.route('/listado-por-cliente',methods=['GET', 'POST'])
def listado_por_cliente():
    if 'username' not in session:
        flash('Debes estar logeado para realizar consultas')
        return redirect(url_for('ingresar'))
    else:
        clientes = []
        lista_de_compras = procesar_csv('datos.csv')

        # Itero los campos de CLIENTE y agrego a los clientes a una lista
        for compra in lista_de_compras:
            clientes.append(compra[2])
        clientes = sorted(list(set(clientes))) #Evito tener clientes repetidos en la lista

        # Campo de busqueda. Devuelve los resultados que coincidan con lo ingresado por el usuario
        formulario = BuscarForm()
        if formulario.validate_on_submit():
            clientes_buscados = []
            for busqueda in clientes:
                if formulario.nombre.data in busqueda.lower():
                    clientes_buscados.append(busqueda)
            clientes = clientes_buscados
            if len(clientes) == 0:
                flash('No se encontraron resultados')
        return render_template('listado_por_cliente.html', clientes=clientes, form=formulario)


# Genera la lista de productos comprado por el cliente en especifico
@app.route('/compras-del-cliente/<cliente>')
def compras_del_cliente(cliente):
    if 'username' not in session:
        flash('Debes estar logeado para realizar consultas')
        return redirect(url_for('ingresar'))
    else:
        productos_comprados = []
        lista_de_compras = procesar_csv('datos.csv')
        for compra in lista_de_compras:
            if compra[2] == cliente:
                productos_comprados.append(compra)

        return render_template('compras_del_cliente.html', productos=productos_comprados, cliente=cliente)


# Genera una lista de los productos para ser mostrada en la pagina y un buscador
@app.route('/listado-por-producto',methods=['GET', 'POST'])
def listado_por_producto():
    if 'username' not in session:
        flash('Debes estar logeado para realizar consultas')
        return redirect(url_for('ingresar'))
    else:
        productos = []
        lista_de_compras = procesar_csv('datos.csv')

        # Itero los campos de PRODCUTO y los agrego a los productos a una lista
        for compra in lista_de_compras:
            productos.append(compra[1])
        productos = sorted(list(set(productos)))

        # Campo de busqueda. Devuelve los resultados que coincidan con lo ingresado por el usuario
        formulario = BuscarForm()
        if formulario.validate_on_submit():
            productos_buscados = []
            for busqueda in productos:
                if formulario.nombre.data in busqueda.lower():
                    productos_buscados.append(busqueda)
            productos = productos_buscados
            if len(productos) == 0:
                flash('No se encontraron resultados')
        return render_template('listado_por_producto.html', productos=productos, form=formulario)


# Genera la lista de clientes que compraron el producto especifico
@app.route('/compras-del-producto/<producto>')
def compras_del_producto(producto):
    if 'username' not in session:
        flash('Debes estar logeado para realizar consultas')
        return redirect(url_for('ingresar'))
    else:
        compradores = []
        lista_de_compras = procesar_csv('datos.csv')
        for compra in lista_de_compras:
            if compra[1] == producto:
                compradores.append(compra)

        return render_template('compras_del_producto.html', compradores=compradores, producto=producto)


# Genera una tabla con los productos mas vendidos
@app.route('/productos-mas-vendidos',methods=['GET', 'POST'])
def prodctos_mas_vendidos():
    if 'username' not in session:
        flash('Debes estar logeado para realizar consultas')
        return redirect(url_for('ingresar'))
    else:
        productos_dict = {}
        lista_de_compras = procesar_csv('datos.csv')

        # Itero las compras segun los productos y sumo las cantidades vendidas
        # y las agrego a un diccionario
        for compra in lista_de_compras:
            if compra[1] in productos_dict:
                productos_dict[compra[1]] = productos_dict[compra[1]] + int(compra[3])
            else:
                productos_dict[compra[1]] = int(compra[3])

        # Ordeno el diccionario para que queden los mas vendidos primero
        productos_dict = OrderedDict(sorted(productos_dict.items(), key=itemgetter(1), reverse=True))

        # Selecciono los tres primeros productos del dicionario ordenado
        mas_comprados = itertools.islice(productos_dict.items(), 0, 3)

        return render_template('productos_mas_vendidos.html', productos=productos_dict, mas_comprados=mas_comprados)
        

# Genera una tabla con los clientes que mas plata gastaron
@app.route('/mejores-clientes',methods=['GET', 'POST'])
def mejores_clientes():
    if 'username' not in session:
        flash('Debes estar logeado para realizar consultas')
        return redirect(url_for('ingresar'))
    else:
        compradores_dict = {}
        lista_de_compras = procesar_csv('datos.csv')

        # Itero las compras segun los compradores y sumo los gastos multiplicados
        # por la cantidad de producto y las agrego a un diccionario
        for compra in lista_de_compras:
            if compra[2] in compradores_dict:
                compradores_dict[compra[2]] = compradores_dict[compra[2]] + float(compra[4])*int(compra[3])
            else:
                compradores_dict[compra[2]] = float(compra[4])*int(compra[3])

        # Ordeno el diccionario para que queden los mas gastadores primero
        compradores_dict = OrderedDict(sorted(compradores_dict.items(), key=itemgetter(1), reverse=True))

        # Selecciono los tres primeros clientes del dicionario ordenado
        mejores_compradores = itertools.islice(compradores_dict.items(), 0, 3)

        return render_template('mejores_clientes.html', compradores=compradores_dict, mejores_compradores=mejores_compradores)


if __name__ == "__main__":
    # app.run(host='0.0.0.0', debug=True)
    manager.run()
