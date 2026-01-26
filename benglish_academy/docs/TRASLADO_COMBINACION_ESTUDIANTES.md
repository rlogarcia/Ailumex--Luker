# TRASLADO/COMBINACION DE ESTUDIANTES

Yo desarrolle el modulo Benglish Academy y documente este archivo para su operacion en produccion.


## A) Descripcion funcional final
Esta funcionalidad permite a Operacion mover estudiantes desde una sesion origen
hacia una sesion destino equivalente, para consolidar horarios duplicados sin
romper la agenda del estudiante. El objetivo es reducir clases duplicadas con la
misma asignatura y el mismo bloque horario, dejando el origen en cero para poder
eliminarlo.

Alcance:
- Aplica en Benglish Academy (backend) y se refleja de inmediato en Portal Student.
- Solo permite traslado si origen y destino son equivalentes (misma asignatura,
  misma fecha, mismo horario).
- El destino debe estar publicado y activo para recibir estudiantes.
- El traslado es auditable con registro de quien lo ejecuto, cuando, origen,
  destino, estudiantes afectados, motivo opcional y resultado.

Como funciona (vista operativa):
1) El operador abre una sesion origen y ejecuta el traslado.
2) Selecciona la sesion destino por codigo de sesion o por busqueda.
3) El sistema muestra un resumen del destino para confirmar que es la clase
   correcta (asignatura, fecha, hora, sede, docente, cupos y estado).
4) El operador elige si traslada un estudiante puntual o a todos.
5) El sistema valida equivalencia y estado del destino. Si falla, bloquea con
   mensaje claro.
6) Ejecuta el traslado: el estudiante sale del origen, entra al destino y la
   agenda del portal queda apuntando al nuevo link.
7) Se genera un registro de auditoria con el resultado.

Impacto esperado:
- El estudiante queda agendado en el destino y deja de estar en el origen.
- El portal muestra la sesion destino y el link correcto.
- La operacion puede dejar el origen en cero para eliminarlo sin afectar otras
  clases de la agenda semanal.

## B) Flujo paso a paso del operador

### Traslado individual
1) Abrir la sesion origen.
2) Click en "Trasladar Estudiantes".
3) Seleccionar la sesion destino (por codigo o busqueda).
4) Verificar resumen del destino.
5) Elegir "Un estudiante" y seleccionar el estudiante.
6) (Opcional) Ingresar motivo.
7) Confirmar el traslado.
8) Ver resultado en el log de traslados.

### Traslado masivo para consolidar
1) Abrir la sesion origen.
2) Click en "Trasladar Estudiantes".
3) Seleccionar sesion destino equivalente.
4) Confirmar que el destino esta publicado y activo.
5) Elegir "Todos los estudiantes".
6) (Opcional) Ingresar motivo.
7) Confirmar el traslado.
8) Ver resultado en el log: exitosos, omitidos o fallidos.

### Eliminacion del horario vacio y republicacion
1) Despublicar la sesion origen (para evitar nuevas inscripciones).
2) Ejecutar traslado masivo al destino equivalente.
3) Validar que el origen quedo en cero (sin inscripciones activas).
4) Eliminar la sesion origen vacia.
5) Republicar la agenda si aplica.
6) Confirmar en portal que los estudiantes ven el nuevo link y mantienen sus
   otras clases de la semana.

## C) Pantallas/acciones necesarias

### Pantalla de traslado (origen -> destino)
Debe mostrar:
- Sesion origen (codigo, asignatura, fecha, hora, sede, docente, inscritos).
- Campo de sesion destino (busqueda por codigo).
- Resumen del destino (asignatura, fecha/hora, sede, docente, cupos, estado,
  publicado/no publicado).
- Selector de alcance: un estudiante o todos.
- Campo de estudiante cuando el alcance es individual.
- Motivo opcional.
- Mensaje de validacion si no cumple equivalencia o estado.

### Vista previa del destino
Debe confirmar:
- Asignatura.
- Fecha y hora (mismo bloque).
- Sede (Bogota/Virtual).
- Docente.
- Cupos/ocupacion.
- Estado y publicacion.

### Confirmacion
Debe solicitar confirmacion explicita antes de ejecutar el traslado.

### Resultado
Debe mostrar:
- Resultado por estudiante: exitoso, omitido o fallido.
- Detalle del motivo de fallo si aplica.
- Acceso a la bitacora de traslados (log).

## D) Criterios de aceptacion (QA)
- [ ] Permite traslado cuando origen y destino tienen misma asignatura y horario.
- [ ] Bloquea traslado si la fecha u hora no coincide y muestra motivo claro.
- [ ] Bloquea traslado si la asignatura es diferente y muestra motivo claro.
- [ ] Bloquea traslado si el destino no esta publicado o activo.
- [ ] Al trasladar, el portal muestra la sesion destino y el link actualizado.
- [ ] Se genera log con usuario, fecha, origen, destino, estudiante(s), motivo y resultado.
- [ ] En consolidacion masiva, el origen queda en cero y puede eliminarse sin
      afectar otras clases de la agenda semanal.
