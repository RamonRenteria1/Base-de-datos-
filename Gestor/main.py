from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import os

class GestorTareas:
    def __init__(self, uri: str = 'mongodb://localhost:27017/'):
        """Inicializar conexión a MongoDB"""
        try:
            self.cliente = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.cliente.admin.command('ping')
            self.db = self.cliente['gestor_tareas']
            self.tareas = self.db['tareas']
            self.usuarios = self.db['usuarios']
            
            # Crear índices necesarios
            self._crear_indices()
            print("✅ Conectado a MongoDB")
        except ConnectionFailure:
            print("❌ Error: No se pudo conectar a MongoDB")
            raise
    
    def _crear_indices(self):
        """Crear índices para mejorar rendimiento"""
        self.usuarios.create_index("email", unique=True)
        self.tareas.create_index([("usuario_id", 1), ("fecha_creacion", -1)])
        self.tareas.create_index("estado")
    
    def crear_usuario(self, nombre: str, email: str, password: str) -> Optional[str]:
        """Crear un nuevo usuario con contraseña"""
        try:
            resultado = self.usuarios.insert_one({
                "nombre": nombre,
                "email": email,
                "password": password, 
                "fecha_registro": datetime.now(),
                "activo": True
            })
            return str(resultado.inserted_id)
        except DuplicateKeyError:
            print(f"❌ Error: El email {email} ya está registrado")
            return None
    
    
    def obtener_usuario(self, email, password):
        usuario = self.db.usuarios.find_one({
            "email": email, 
            
            "password": password
            
        })

        if usuario:
            usuario['_id'] = str(usuario['_id']) 
            return usuario
            
        return None

    def crear_tarea(self, usuario_id, titulo, descripcion, fecha_entrega):
        nueva_tarea = {
            "usuario_id": ObjectId(usuario_id),
            "titulo": titulo,
            "descripcion": descripcion,
            "estado": "pendiente",
            "fecha_creacion": datetime.now(),
            "fecha_entrega": fecha_entrega  # Guardamos la fecha límite
        }
        
        resultado = self.db.tareas.insert_one(nueva_tarea)
        return str(resultado.inserted_id)
    def obtener_tareas_usuario(self, usuario_id):
        tareas = self.db.tareas.find({"usuario_id": ObjectId(usuario_id)})
        return list(tareas)
    
    def obtener_tarea(self, tarea_id):
        tarea = self.db.tareas.find_one({"_id": ObjectId(tarea_id)})
        if tarea:
            tarea['_id'] = str(tarea['_id']) 
            tarea['usuario_id'] = str(tarea['usuario_id'])
        return tarea

    def editar_tarea(self, tarea_id, titulo, descripcion):
        resultado = self.db.tareas.update_one(
            {"_id": ObjectId(tarea_id)},
            {"$set": {
                "titulo": titulo,
                "descripcion": descripcion
            }}
        )
        return resultado.modified_count > 0

    def actualizar_estado_tarea(self, tarea_id, nuevo_estado):
        actualizacion = {"estado": nuevo_estado}
        if nuevo_estado == 'completada':
            actualizacion["fecha_cierre"] = datetime.now()
            
        resultado = self.db.tareas.update_one(
            {"_id": ObjectId(tarea_id)},
            {"$set": actualizacion}
        )
        return resultado.modified_count > 0
        
    
    def agregar_etiqueta(self, tarea_id: str, etiqueta: str) -> bool:
        """Agregar etiqueta a una tarea"""
        resultado = self.tareas.update_one(
            {"_id": ObjectId(tarea_id)},
            {"$addToSet": {"etiquetas": etiqueta}}
        )
        return resultado.modified_count > 0
    
    def eliminar_tarea(self, tarea_id):
        
        resultado = self.db.tareas.delete_one({"_id": ObjectId(tarea_id)})
        return resultado.deleted_count > 0
    
    def estadisticas_usuario(self, usuario_id: str) -> Dict:
        """Obtener estadísticas de tareas de un usuario"""
        pipeline = [
            {"$match": {"usuario_id": ObjectId(usuario_id)}},
            {"$group": {
                "_id": "$estado",
                "cantidad": {"$sum": 1},
                "fecha_ultima": {"$max": "$fecha_creacion"}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        resultados = list(self.tareas.aggregate(pipeline))
        
        # Formatear resultados
        estadisticas = {
            "total": 0,
            "por_estado": {},
            "ultima_actividad": None
        }
        
        for r in resultados:
            estado = r['_id']
            cantidad = r['cantidad']
            estadisticas["por_estado"][estado] = cantidad
            estadisticas["total"] += cantidad
            
            if not estadisticas["ultima_actividad"] or r['fecha_ultima'] > estadisticas["ultima_actividad"]:
                estadisticas["ultima_actividad"] = r['fecha_ultima']
        
        return estadisticas
    
    def buscar_tareas(self, texto: str) -> List[Dict]:
        """Buscar tareas por texto en título o descripción"""
        # Requiere índice de texto en 'titulo' y 'descripcion'
        tareas = self.tareas.find({
            "$text": {"$search": texto}
        }).sort({"score": {"$meta": "textScore"}})
        
        resultado = []
        for t in tareas:
            t['_id'] = str(t['_id'])
            t['usuario_id'] = str(t['usuario_id'])
            resultado.append(t)
        return resultado
    
    def tareas_urgentes(self, horas: int = 24) -> List[Dict]:
        """Encontrar tareas que vencen en las próximas N horas"""
        ahora = datetime.now()
        limite = ahora + timedelta(hours=horas)
        
        tareas = self.tareas.find({
            "estado": {"$ne": "completada"},
            "fecha_limite": {"$gte": ahora, "$lte": limite}
        }).sort("fecha_limite", 1)
        
        resultado = []
        for t in tareas:
            t['_id'] = str(t['_id'])
            t['usuario_id'] = str(t['usuario_id'])
            resultado.append(t)
        return resultado
    
    def cerrar_conexion(self):
        """Cerrar conexión a MongoDB"""
        if self.cliente:
            self.cliente.close()
            print("🔌 Conexión cerrada")

